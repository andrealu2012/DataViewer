"""Stock-list configuration dialog for the desktop client."""

from typing import Callable, Dict

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from config_loader import normalize_stock_code, save_config
from icon_utils import load_icon


def make_symbol_icon(color: str, symbol: str) -> QIcon:
    """Create a crisp plus/minus icon without relying on external assets."""
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(4, 9, 14, 9)
    if symbol == "plus":
        painter.drawLine(9, 4, 9, 14)
    painter.end()
    return QIcon(pixmap)


class StockItemDelegate(QStyledItemDelegate):
    """Paint code/market normally and only the stock name in bold."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        text_option = QStyleOptionViewItem(option)
        self.initStyleOption(text_option, index)
        super().paint(painter, text_option, index)
        if not bool(index.data(Qt.ItemDataRole.UserRole + 2)):
            return

        code = str(index.data(Qt.ItemDataRole.UserRole) or "")
        number, _, exchange = code.partition(".")
        market = {"SH": "上海", "SZ": "深圳", "BJ": "北京"}.get(exchange, exchange or "未知")
        name = str(index.data(Qt.ItemDataRole.UserRole + 1) or "（名称加载中）")
        color = (
            option.palette.highlightedText().color()
            if option.state & QStyle.StateFlag.State_Selected
            else option.palette.text().color()
        )

        painter.save()
        painter.setPen(color)
        rect = option.rect.adjusted(8, 0, -4, 0)
        painter.setFont(option.font)
        painter.drawText(rect.adjusted(0, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, number)
        painter.drawText(rect.adjusted(84, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, market)
        bold_font = QFont(option.font)
        bold_font.setBold(True)
        painter.setFont(bold_font)
        painter.drawText(rect.adjusted(142, 0, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)
        painter.restore()


class ConfigDialog(QDialog):
    def __init__(
        self,
        config: Dict,
        apply_callback: Callable[[], None],
        stock_names: Dict[str, str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.config = config
        self.apply_callback = apply_callback
        self.stock_names = stock_names or {}
        self.setWindowTitle("配置自选股")
        self.setMinimumSize(390, 420)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("股票列表（代码　　市场　　名称）"))

        self.stock_list = QListWidget()
        self.stock_list.setItemDelegate(StockItemDelegate(self.stock_list))
        self.stock_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.stock_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.stock_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.stock_list.itemSelectionChanged.connect(self._update_delete_button)
        for code in config.get("stocks", []):
            self._add_stock_item(code)
        layout.addWidget(self.stock_list)

        entry_layout = QHBoxLayout()
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("输入股票代码，例如 600580 或 000001.SZ")
        self.stock_input.returnPressed.connect(self.add_stock)
        add_button = QPushButton()
        add_button.setIcon(make_symbol_icon("#2EAD55", "plus"))
        add_button.setFixedWidth(52)
        add_button.setToolTip("添加股票")
        add_button.setAccessibleName("添加股票")
        add_button.setStyleSheet(
            "QPushButton { border: 1px solid #2EAD55; border-radius: 4px; "
            "padding: 3px 8px; background: transparent; }"
            "QPushButton:hover { background: #E8F5E9; }"
            "QPushButton:pressed { background: #C8E6C9; }"
        )
        add_button.clicked.connect(self.add_stock)
        entry_layout.addWidget(self.stock_input, 1)
        entry_layout.addWidget(add_button)
        layout.addLayout(entry_layout)

        buttons = QHBoxLayout()
        buttons.addStretch()
        apply_button = QPushButton("应用配置")
        apply_button.setIcon(load_icon("icons/apply.svg"))
        apply_button.setIconSize(QSize(18, 18))
        apply_button.setMinimumSize(112, 36)
        apply_button.clicked.connect(self.apply_config)
        save_button = QPushButton("保存退出")
        save_button.setIcon(load_icon("icons/save.svg"))
        save_button.setIconSize(QSize(18, 18))
        save_button.setMinimumSize(112, 36)
        save_button.setDefault(True)
        save_button.clicked.connect(self.save_and_close)
        buttons.addWidget(apply_button)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)
        self.resize(390, max(520, self.sizeHint().height()))

    def add_stock(self):
        raw_code = self.stock_input.text().strip()
        code = normalize_stock_code(raw_code)
        if not self._is_valid_code(code):
            QMessageBox.warning(self, "代码无效", "请输入 6 位股票代码，例如 600580 或 000001.SZ。")
            return
        existing = {self._item_code(self.stock_list.item(i)) for i in range(self.stock_list.count())}
        if code in existing:
            QMessageBox.information(self, "股票已存在", f"{code} 已在股票列表中。")
            return
        self._add_stock_item(code)
        self.stock_input.clear()
        self.stock_input.setFocus()
        self.apply_config()

    def delete_stock(self, item: QListWidgetItem):
        row = self.stock_list.row(item)
        if row >= 0:
            self._remove_item_widget(item)
            self.stock_list.takeItem(row)

    def apply_config(self) -> bool:
        stocks = [self._item_code(self.stock_list.item(i)) for i in range(self.stock_list.count())]
        if not stocks:
            QMessageBox.warning(self, "股票列表为空", "请至少添加一只股票后再应用配置。")
            return False

        updated_config = dict(self.config)
        updated_config["stocks"] = stocks
        try:
            save_config(updated_config, "config.json")
            self.config = updated_config
            self.apply_callback()
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", f"无法写入 config.json：\n{exc}")
            return False
        return True

    def save_and_close(self):
        if self.apply_config():
            self.accept()

    def update_stock_names(self, stock_names: Dict[str, str]):
        """Refresh visible names after a quote request completes."""
        self.stock_names.update(stock_names)
        selected_item = self.stock_list.currentItem()
        for index in range(self.stock_list.count()):
            item = self.stock_list.item(index)
            code = self._item_code(item)
            item.setData(Qt.ItemDataRole.UserRole + 1, self.stock_names.get(code) or "（名称加载中）")
        self.stock_list.viewport().update()
        if selected_item is not None:
            self._remove_item_widget(selected_item)
            self._update_delete_button()

    def _add_stock_item(self, code: str):
        item = QListWidgetItem("")
        item.setData(Qt.ItemDataRole.UserRole, code)
        item.setData(Qt.ItemDataRole.UserRole + 1, self.stock_names.get(code) or "（名称加载中）")
        item.setData(Qt.ItemDataRole.UserRole + 2, True)
        self.stock_list.addItem(item)

    def _update_delete_button(self):
        selected = self.stock_list.selectedItems()
        selected_item = selected[0] if selected else None

        for index in range(self.stock_list.count()):
            item = self.stock_list.item(index)
            if item is not selected_item and self.stock_list.itemWidget(item) is not None:
                self._remove_item_widget(item)

        if selected_item is None or self.stock_list.itemWidget(selected_item) is not None:
            return

        row_widget = QWidget(self.stock_list)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 4, 0)
        row_layout.setSpacing(8)
        code = self._item_code(selected_item)
        number, _, exchange = code.partition(".")
        market = {"SH": "上海", "SZ": "深圳", "BJ": "北京"}.get(exchange, exchange or "未知")
        name = self.stock_names.get(code) or "（名称加载中）"
        code_label = QLabel(number)
        code_label.setFixedWidth(76)
        market_label = QLabel(market)
        market_label.setFixedWidth(50)
        name_label = QLabel(name)
        name_font = name_label.font()
        name_font.setBold(True)
        name_label.setFont(name_font)
        row_layout.addWidget(code_label)
        row_layout.addWidget(market_label)
        row_layout.addWidget(name_label, 1)
        delete_button = QPushButton()
        delete_button.setIcon(make_symbol_icon("#D32F2F", "minus"))
        delete_button.setFixedWidth(52)
        delete_button.setToolTip("删除股票")
        delete_button.setAccessibleName("删除股票")
        delete_button.setStyleSheet(
            "QPushButton { color: #D32F2F; border: 1px solid #D32F2F; "
            "border-radius: 4px; padding: 3px 8px; background: transparent; }"
            "QPushButton:hover { background: #FFEBEE; }"
            "QPushButton:pressed { background: #FFCDD2; }"
        )
        delete_button.clicked.connect(lambda _checked=False, item=selected_item: self.delete_stock(item))
        row_layout.addWidget(delete_button)
        selected_item.setData(Qt.ItemDataRole.UserRole + 2, False)
        self.stock_list.setItemWidget(selected_item, row_widget)

    def _remove_item_widget(self, item: QListWidgetItem):
        widget = self.stock_list.itemWidget(item)
        if widget is not None:
            self.stock_list.removeItemWidget(item)
            widget.deleteLater()
            item.setData(Qt.ItemDataRole.UserRole + 2, True)

    def _item_text(self, code: str) -> str:
        number, _, exchange = code.partition(".")
        market = {"SH": "上海", "SZ": "深圳", "BJ": "北京"}.get(exchange, exchange or "未知")
        name = self.stock_names.get(code)
        stock_name = name or "（名称加载中）"
        return f"{number}　　{market}　　{stock_name}"

    @staticmethod
    def _item_code(item: QListWidgetItem) -> str:
        return str(item.data(Qt.ItemDataRole.UserRole))

    @staticmethod
    def _is_valid_code(code: str) -> bool:
        parts = code.split(".")
        return len(parts) == 2 and len(parts[0]) == 6 and parts[0].isdigit() and parts[1] in {"SH", "SZ"}
