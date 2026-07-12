"""RealDataView stock overlay widget."""

import sys
from typing import Dict, List, Optional

from PyQt6.QtCore import QPoint, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QMenu, QSystemTrayIcon, QVBoxLayout, QWidget
from pypinyin import Style, lazy_pinyin

from config_loader import is_trading_hours, load_config
from config_dialog import ConfigDialog
from event_handlers import StockOverlayEvents
from icon_utils import load_icon
from stock_client import StockDataClientWorker
from styles import LABEL_MIN_HEIGHT, parse_qcolor

SERVER_BASE_URL = "https://stock.xdof.top"
SERVER_TIMEOUT_SECONDS = 8


class StockOverlay(StockOverlayEvents, QWidget):
    """Frameless desktop overlay that renders quotes returned by the server."""

    hotkey_show_requested = pyqtSignal()
    hotkey_hide_requested = pyqtSignal()

    def __init__(self, stock_codes: List[str], update_interval: int = 3000, config: Optional[Dict] = None):
        super().__init__()
        self.stock_codes = stock_codes
        self.update_interval = update_interval
        self.config = config or {}
        self.server_base_url = SERVER_BASE_URL
        self.timeout_seconds = SERVER_TIMEOUT_SECONDS

        self.stock_data: Dict[str, Dict] = {}
        self.drag_position = QPoint()
        self.worker: Optional[StockDataClientWorker] = None
        self.retired_workers: List[StockDataClientWorker] = []
        self.is_updating = False
        self.is_first_update = True
        self.display_modes = self._load_display_modes()
        self.display_mode_index = 0
        self.max_name_width = 0
        self.max_price_width = 0
        self.max_change_width = 0
        self.server_warning_label = None
        self.config_dialog = None

        ui_cfg = self.config.get("ui", {})
        self.increase_color = ui_cfg.get("increase_color", "#FF4444")
        self.decrease_color = ui_cfg.get("decrease_color", "#44DD44")

        hotkey_config = self.config.get("hotkey", {})
        self.hotkey_enabled = hotkey_config.get("enabled", True)
        self.hotkey_key = str(hotkey_config.get("key", "f3")).lower()
        self.hotkey_modifier = str(hotkey_config.get("modifier", "ctrl")).lower()
        self.hotkey_pressed = False
        self.pressed_keys = set()
        self.listener = None
        self.hotkey_show_requested.connect(self.show_overlay)
        self.hotkey_hide_requested.connect(self.hide)

        self.init_ui()
        self.setup_timer()
        self.init_tray_icon()

    @staticmethod
    def chinese_to_pinyin_initials(chinese_text: str) -> str:
        if not chinese_text:
            return ""
        return "".join(p.upper() for p in lazy_pinyin(chinese_text, style=Style.FIRST_LETTER) if p)

    def _load_display_modes(self) -> List[Dict]:
        modes = self.config.get("display_modes")
        if not isinstance(modes, list) or not modes:
            return [
                {"name": "Price + Change", "name_display": "none", "show_price": True, "show_change": True},
                {"name": "Chinese + Price + Change", "name_display": "chinese", "show_price": True, "show_change": True},
                {"name": "Pinyin + Price + Change", "name_display": "pinyin", "show_price": True, "show_change": True},
                {"name": "Pinyin + Change", "name_display": "pinyin", "show_price": False, "show_change": True},
            ]

        normalized = []
        for mode in modes:
            if not isinstance(mode, dict):
                continue
            name_display = str(mode.get("name_display", "pinyin")).lower()
            if name_display not in ("pinyin", "chinese", "none"):
                name_display = "pinyin"
            normalized.append(
                {
                    "name": mode.get("name") or f"Mode {len(normalized) + 1}",
                    "name_display": name_display,
                    "show_price": bool(mode.get("show_price", True)),
                    "show_change": bool(mode.get("show_change", True)),
                }
            )
        return normalized or [{"name": "Pinyin + Price", "name_display": "pinyin", "show_price": True, "show_change": True}]

    def _current_mode(self) -> Dict:
        return self.display_modes[self.display_mode_index % len(self.display_modes)]

    def _mode_label(self) -> str:
        return self._current_mode().get("name") or f"Mode {self.display_mode_index + 1}"

    def _set_mode_by_legacy_key(self, key: str):
        for idx, mode in enumerate(self.display_modes):
            name_mode = mode.get("name_display")
            show_price = mode.get("show_price", True)
            show_change = mode.get("show_change", True)
            if key == "price_only" and name_mode == "none" and show_price:
                self.display_mode_index = idx
                break
            if key == "chinese" and name_mode == "chinese" and show_price:
                self.display_mode_index = idx
                break
            if key == "pinyin" and name_mode == "pinyin" and show_price:
                self.display_mode_index = idx
                break
            if key == "pinyin_change" and name_mode == "pinyin" and show_change and not show_price:
                self.display_mode_index = idx
                break
        self._refresh_display()
        QTimer.singleShot(0, self.adjust_size_to_content)

    def init_ui(self):
        window_flags = (
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        if sys.platform == "darwin":
            # Qt.Tool maps to an NSPanel that macOS hides when this application
            # becomes inactive. Keep the overlay as a normal top-level window.
            window_flags |= Qt.WindowType.Window
        else:
            window_flags |= Qt.WindowType.Tool
        self.setWindowFlags(window_flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        base_height = 20
        stock_height = 12
        self.resize(180, base_height + len(self.stock_codes) * stock_height)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - 12, screen.top() + 12)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(3)

        self.stock_labels = []
        for _code in self.stock_codes:
            label = self._build_stock_label()
            self.stock_labels.append(label)
            layout.addWidget(label)

        self.setLayout(layout)
        self.update_ui_colors(True if self.is_first_update or is_trading_hours(self.config) else False)
        self.update_stock_data()
        QTimer.singleShot(0, self.adjust_size_to_content)
        self.start_hotkey_listener()

    def _build_stock_label(self) -> QLabel:
        label = QLabel("Loading...")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setStyleSheet(
            """
            QLabel {
                color: rgba(180, 180, 180, 200);
                background-color: rgba(30, 30, 30, 160);
                border-radius: 3px;
                padding: 8px 8px;
                font-size: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
            }
            """
        )
        label.setMinimumHeight(LABEL_MIN_HEIGHT)
        label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return label

    def _rebuild_stock_labels(self, stock_codes: List[str]):
        layout = self.layout()
        if layout is None:
            return

        for label in self.stock_labels:
            layout.removeWidget(label)
            label.deleteLater()

        self.stock_labels = []
        self.stock_data.clear()
        self.stock_codes = stock_codes

        for _code in self.stock_codes:
            label = self._build_stock_label()
            self.stock_labels.append(label)
            layout.addWidget(label)

        QTimer.singleShot(0, self.adjust_size_to_content)

    def reload_config(self):
        try:
            if self.worker and self.worker.isRunning():
                self._retire_worker(self.worker)

            self.config = load_config("config.json")
            ui_cfg = self.config.get("ui", {})
            self.increase_color = ui_cfg.get("increase_color", "#FF4444")
            self.decrease_color = ui_cfg.get("decrease_color", "#44DD44")

            self.display_modes = self._load_display_modes()
            self.display_mode_index = 0
            self._rebuild_stock_labels(self.config.get("stocks", self.stock_codes))

            self.update_interval = int(self.config.get("update_interval_ms", self.update_interval))
            self.timer.setInterval(self.update_interval)

            hotkey_config = self.config.get("hotkey", {})
            self.hotkey_enabled = hotkey_config.get("enabled", True)
            self.hotkey_key = str(hotkey_config.get("key", "f3")).lower()
            self.hotkey_modifier = str(hotkey_config.get("modifier", "ctrl")).lower()
            self.stop_hotkey_listener()
            self.start_hotkey_listener()

            self.is_first_update = True
            self.update_ui_colors(is_trading_hours(self.config))
            self.update_stock_data()
        except Exception as exc:
            print(f"Failed to reload config: {exc}")
            self._show_error("Config error")

    def open_config_dialog(self):
        if self.config_dialog and self.config_dialog.isVisible():
            self.config_dialog.raise_()
            self.config_dialog.activateWindow()
            return

        stock_names = {
            code: str(data.get("name"))
            for code, data in self.stock_data.items()
            if data.get("name")
        }
        self.config_dialog = ConfigDialog(
            self.config,
            self.reload_config,
            stock_names=stock_names,
            parent=self,
        )
        self.config_dialog.setWindowOpacity(self.windowOpacity())
        self.config_dialog.finished.connect(lambda _result: setattr(self, "config_dialog", None))
        self.config_dialog.show()
        self.config_dialog.raise_()
        self.config_dialog.activateWindow()

    def set_synced_opacity(self, opacity: float):
        """Apply one opacity value to the overlay and its configuration window."""
        self.setWindowOpacity(opacity)
        if self.config_dialog and self.config_dialog.isVisible():
            self.config_dialog.setWindowOpacity(opacity)

    def init_tray_icon(self):
        icon = QIcon()
        tray_icon_path = self.config.get("ui", {}).get("tray_icon_path", "icons/tray.png")
        icon = load_icon(tray_icon_path)

        # macOS menu bar icons should be template images. Qt then uses the
        # alpha silhouette and lets macOS choose black/white for the current
        # menu bar appearance. Windows keeps the original full-color icon.
        if sys.platform == "darwin" and not icon.isNull():
            icon.setIsMask(True)

        if icon.isNull():
            pixmap = QPixmap(16, 16)
            pixmap.fill(parse_qcolor("rgba(160,150,150,255)"))
            icon = QIcon(pixmap)

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip("RealDataView")

        tray_menu = QMenu()
        show_action = QAction("显示/隐藏", self)
        show_action.triggered.connect(self.toggle_window)
        tray_menu.addAction(show_action)

        config_action = QAction("配置自选股", self)
        config_action.triggered.connect(self.open_config_dialog)
        tray_menu.addAction(config_action)
        tray_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_window()

    def toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_overlay()

    def show_overlay(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication

                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            except Exception as exc:
                print(f"Failed to activate macOS application: {exc}")

    def quit_application(self):
        if hasattr(self, "timer") and self.timer.isActive():
            self.timer.stop()
        workers = ([self.worker] if self.worker else []) + self.retired_workers
        for worker in workers:
            if worker.isRunning():
                worker.stop(wait_ms=int((self.timeout_seconds + 1) * 1000))
        self.stop_hotkey_listener()
        if hasattr(self, "tray_icon"):
            self.tray_icon.hide()
        QApplication.quit()

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stock_data)
        self.timer.start(self.update_interval)

    def update_stock_data(self):
        if self.is_updating:
            return
        if not self.is_first_update and not is_trading_hours(self.config):
            self.update_ui_colors(False)
            return

        self.is_first_update = False
        self.update_ui_colors(True)

        if self.worker and self.worker.isRunning():
            self._retire_worker(self.worker)

        self.is_updating = True
        self.worker = StockDataClientWorker(self.stock_codes, self.server_base_url, self.timeout_seconds)
        self.worker.data_ready.connect(self._on_data_ready)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(lambda: setattr(self, "is_updating", False))
        self.worker.start()

    def _retire_worker(self, worker: StockDataClientWorker):
        """Keep a cancelled QThread alive until its blocking request returns."""
        worker.stop(wait_ms=0)
        for signal in (worker.data_ready, worker.error_occurred, worker.finished):
            try:
                signal.disconnect()
            except TypeError:
                pass
        if worker not in self.retired_workers:
            self.retired_workers.append(worker)

        def cleanup():
            if worker in self.retired_workers:
                self.retired_workers.remove(worker)

        worker.finished.connect(cleanup)
        if self.worker is worker:
            self.worker = None
        self.is_updating = False

    def _on_data_ready(self, payload):
        try:
            quotes = payload.get("quotes", []) if isinstance(payload, dict) else payload
            by_code = {str(q.get("ts_code") or q.get("code")): q for q in quotes if isinstance(q, dict)}
            for idx, code in enumerate(self.stock_codes):
                quote = by_code.get(code)
                if quote is None:
                    short_code = code.replace(".SH", "").replace(".SZ", "")
                    quote = next((q for q in quotes if short_code in str(q.get("ts_code") or q.get("code"))), None)
                if quote:
                    self._update_label_from_quote(idx, quote, code)
                else:
                    self.stock_labels[idx].setText("No data")
            if self.config_dialog and self.config_dialog.isVisible():
                stock_names = {
                    code: str(data.get("name"))
                    for code, data in self.stock_data.items()
                    if data.get("name")
                }
                self.config_dialog.update_stock_names(stock_names)
            self._update_column_widths()
        except Exception as exc:
            print(f"Failed to handle server data: {exc}")
            self._show_error("Data error")
        finally:
            self.is_updating = False

    def _on_error(self, error_msg: str):
        print(f"Failed to update stock data: {error_msg}")
        self._show_error("Server error")
        self.is_updating = False

    def _show_error(self, msg: str):
        QTimer.singleShot(0, lambda: self._update_error_labels(msg))

    def _update_error_labels(self, msg: str):
        for label in self.stock_labels:
            if not label.text() or label.text() in ("Loading...", "Server error", "Data error", "No data"):
                label.setText(msg)

    def _update_label_from_quote(self, idx: int, quote: Dict, code: str):
        name = quote.get("name") or code.split(".")[0]
        price = self._to_float(quote.get("price"))
        prev_close = self._to_float(quote.get("pre_close"))
        change_percent = quote.get("change_percent")
        if change_percent is None:
            change_percent = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

        pinyin_initials = self.chinese_to_pinyin_initials(str(name)) or code.split(".")[0]
        self.stock_data[code] = {
            "name": name,
            "pinyin_initials": pinyin_initials,
            "price": price,
            "prev_close": prev_close,
            "change_percent": self._to_float(change_percent),
        }

    def _to_float(self, value) -> float:
        try:
            return float(value) if value not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0

    def _refresh_display(self):
        self._update_column_widths()

    def _format_change_percent(self, change_percent: float) -> str:
        return f"{change_percent:+.2f}%"

    def _display_width(self, value: str) -> int:
        return sum(2 if ord(ch) > 127 else 1 for ch in value)

    def _update_column_widths(self):
        if not self.stock_data:
            return

        mode = self._current_mode()
        name_mode = mode.get("name_display", "pinyin")
        show_price = mode.get("show_price", True)
        show_change = mode.get("show_change", True)

        self.max_name_width = 0
        self.max_price_width = 0
        self.max_change_width = 0
        for data in self.stock_data.values():
            if name_mode == "none":
                name_str = ""
            elif name_mode == "chinese":
                name_str = str(data.get("name", ""))
            else:
                name_str = str(data.get("pinyin_initials", ""))
            price_str = self._format_price(data.get("price", 0.0)) if show_price else ""
            change_str = self._format_change_percent(data.get("change_percent", 0.0)) if show_change else ""
            self.max_name_width = max(self.max_name_width, self._display_width(name_str))
            self.max_price_width = max(self.max_price_width, len(price_str))
            self.max_change_width = max(self.max_change_width, len(change_str))

        self._refresh_display_aligned()

    def _format_price(self, price: float) -> str:
        return f"{price:.3f}".rstrip("0").rstrip(".") if price else "0"

    def _refresh_display_aligned(self):
        ui_cfg = self.config.get("ui", {})
        text_color = ui_cfg.get("active_text_color", "#FFFFFF")
        mode = self._current_mode()
        name_mode = mode.get("name_display", "pinyin")
        show_price = mode.get("show_price", True)
        show_change = mode.get("show_change", True)

        for code, data in self.stock_data.items():
            if code not in self.stock_codes:
                continue
            idx = self.stock_codes.index(code)
            if name_mode == "none":
                name_str = ""
            elif name_mode == "chinese":
                name_str = str(data.get("name", ""))
            else:
                name_str = str(data.get("pinyin_initials", ""))

            price_str = self._format_price(data.get("price", 0.0)) if show_price else ""
            name_padding = max(self.max_name_width - self._display_width(name_str), 0)
            price_padding = max(self.max_price_width - len(price_str), 0)
            name_aligned = name_str + "&nbsp;" * name_padding
            price_aligned = "&nbsp;" * price_padding + price_str

            change_html = ""
            if show_change:
                change_percent = data.get("change_percent", 0.0)
                change_text = self._format_change_percent(change_percent)
                change_text = "&nbsp;" * max(self.max_change_width - len(change_text), 0) + change_text
                color = self.increase_color if change_percent >= 0 else self.decrease_color
                change_html = f'&nbsp;<span style="color: {color};">[{change_text}]</span>'

            if not show_price and name_mode == "none":
                display_text = change_html
            elif not show_price:
                display_text = f'<span style="color: {text_color};">{name_aligned}</span>{change_html}'
            elif name_mode == "none":
                display_text = f'<span style="color: {text_color};">{price_aligned}</span>{change_html}'
            else:
                display_text = f'<span style="color: {text_color};">{name_aligned}&nbsp;&nbsp;{price_aligned}</span>{change_html}'

            self.stock_labels[idx].setText(display_text)

        QTimer.singleShot(0, self.adjust_size_to_content)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ui_cfg = self.config.get("ui", {})
        painter.setBrush(QBrush(parse_qcolor(ui_cfg.get("window_bg_color", "rgba(20, 20, 20, 180)"))))
        painter.setPen(QPen(parse_qcolor(ui_cfg.get("border_color", "rgba(100, 100, 100, 100)")), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)

    def adjust_size_to_content(self):
        layout = self.layout()
        if layout is None:
            return

        margins = layout.contentsMargins()
        spacing = layout.spacing() if layout.spacing() is not None else 0
        max_text_width = max((label.sizeHint().width() for label in self.stock_labels), default=0)
        total_height = sum(max(label.sizeHint().height(), LABEL_MIN_HEIGHT) for label in self.stock_labels)
        width = max(50, margins.left() + max_text_width + margins.right())
        height = margins.top() + margins.bottom() + total_height + spacing * max(len(self.stock_labels) - 1, 0)
        self.setFixedSize(int(width), int(height))

    def update_ui_colors(self, active: bool):
        ui_cfg = self.config.get("ui", {})
        text_color = ui_cfg.get("active_text_color", "#FFFFFF") if active else ui_cfg.get("inactive_text_color", "#000000")
        label_bg = ui_cfg.get("label_bg_color", "rgba(30, 30, 30, 160)")
        font_family = ui_cfg.get("font_family", "Consolas, 'Courier New', monospace")
        font_size = ui_cfg.get("font_size", 10)
        sheet = (
            "QLabel {"
            f"color: {text_color}; background-color: {label_bg}; border-radius: 3px; "
            f"padding: 3px 6px; font-size: {font_size}px; font-family: {font_family};"
            "}"
        )
        for label in self.stock_labels:
            label.setStyleSheet(sheet)
