"""Event handler mixin for the desktop stock overlay."""

import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox

if sys.platform != "darwin":
    from pynput import keyboard


class StockOverlayEvents:
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self.set_synced_opacity(0.3 if self.windowOpacity() == 1.0 else 1.0)
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        config_action = menu.addAction("配置自选股")
        about_action = menu.addAction("关于")
        exit_action = menu.addAction("退出")
        action = menu.exec(event.globalPos())

        if action == config_action:
            self.open_config_dialog()
        elif action == about_action:
            QMessageBox.about(
                self,
                "DataViewer",
                f"显示模式: {self._mode_label()}\n股票数量: {len(self.stock_codes)}",
            )
        elif action == exit_action:
            self.quit_application()

    def start_hotkey_listener(self):
        if not self.hotkey_enabled:
            return
        if sys.platform == "darwin":
            self._start_macos_hotkey_listener()
            return
        try:
            self.listener = keyboard.Listener(
                on_press=self._on_hotkey_press,
                on_release=self._on_hotkey_release,
            )
            self.listener.start()
            print(f"Hotkey enabled: {self.hotkey_modifier}+{self.hotkey_key}")
        except Exception as exc:
            print(f"Failed to start hotkey listener: {exc}")

    def stop_hotkey_listener(self):
        if sys.platform == "darwin":
            monitors = self.listener or []
            if monitors:
                from AppKit import NSEvent

                for monitor in monitors:
                    NSEvent.removeMonitor_(monitor)
            self.listener = None
            self.hotkey_pressed = False
            return
        if self.listener:
            self.listener.stop()
            self.listener = None

    def _start_macos_hotkey_listener(self):
        """Use AppKit on macOS; pynput crashes in TSM APIs on recent macOS."""
        try:
            from AppKit import NSEvent, NSEventMaskKeyDown, NSEventMaskKeyUp, NSEventTypeKeyDown

            def handle_event(event):
                key_name = self._macos_key_name(event)
                has_modifier = self._macos_has_modifier(event.modifierFlags())
                is_down = event.type() == NSEventTypeKeyDown
                if is_down and has_modifier and key_name == self.hotkey_key.lower():
                    if not self.hotkey_pressed:
                        self.hotkey_pressed = True
                        self.hotkey_show_requested.emit()
                elif not is_down and self.hotkey_pressed and not has_modifier:
                    self.hotkey_pressed = False
                    self.hotkey_hide_requested.emit()

            mask = NSEventMaskKeyDown | NSEventMaskKeyUp
            global_monitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, handle_event)
            local_monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
                mask, lambda event: (handle_event(event), event)[1]
            )
            self.listener = [monitor for monitor in (global_monitor, local_monitor) if monitor is not None]
            print(f"macOS hotkey enabled: {self.hotkey_modifier}+{self.hotkey_key}")
        except Exception as exc:
            self.listener = None
            print(f"Failed to start macOS hotkey listener: {exc}")

    @staticmethod
    def _macos_key_name(event) -> str:
        function_keys = {
            122: "f1", 120: "f2", 99: "f3", 118: "f4", 96: "f5", 97: "f6",
            98: "f7", 100: "f8", 101: "f9", 109: "f10", 103: "f11", 111: "f12",
        }
        if event.keyCode() in function_keys:
            return function_keys[event.keyCode()]
        return str(event.charactersIgnoringModifiers() or "").lower()

    def _macos_has_modifier(self, flags) -> bool:
        from AppKit import NSEventModifierFlagControl, NSEventModifierFlagOption, NSEventModifierFlagShift

        modifier_flags = {
            "ctrl": NSEventModifierFlagControl,
            "alt": NSEventModifierFlagOption,
            "shift": NSEventModifierFlagShift,
        }
        required = modifier_flags.get(self.hotkey_modifier)
        return bool(required and flags & required)

    def _on_hotkey_press(self, key):
        try:
            self.pressed_keys.add(key)
            key_name = self._key_name(key)
            has_modifier = self._has_modifier()
            if has_modifier and key_name == self.hotkey_key.lower() and not self.hotkey_pressed:
                self.hotkey_pressed = True
                QTimer.singleShot(0, self.show)
        except Exception as exc:
            print(f"Hotkey press failed: {exc}")

    def _on_hotkey_release(self, key):
        try:
            self.pressed_keys.discard(key)
            if self.hotkey_pressed and not self._has_modifier():
                self.hotkey_pressed = False
                QTimer.singleShot(0, self.hide)
        except Exception as exc:
            print(f"Hotkey release failed: {exc}")

    def _key_name(self, key) -> str:
        if hasattr(key, "char") and key.char:
            return key.char.lower()
        if hasattr(key, "name"):
            return key.name.lower()
        return ""

    def _has_modifier(self) -> bool:
        if self.hotkey_modifier == "ctrl":
            return any(k in self.pressed_keys for k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r))
        if self.hotkey_modifier == "alt":
            return any(k in self.pressed_keys for k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r))
        if self.hotkey_modifier == "shift":
            return any(k in self.pressed_keys for k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r))
        return False

    def wheelEvent(self, event):
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.AltModifier:
            direction = -1 if event.angleDelta().y() > 0 else 1
            self.display_mode_index = (self.display_mode_index + direction) % len(self.display_modes)
            self._refresh_display()
            QTimer.singleShot(0, self.adjust_size_to_content)
            event.accept()
            return

        if mods & Qt.KeyboardModifier.ControlModifier:
            step = 0.05
            opacity = self.windowOpacity()
            self.set_synced_opacity(
                min(1.0, opacity + step)
                if event.angleDelta().y() > 0
                else max(0.1, opacity - step)
            )
            event.accept()
            return

        event.ignore()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.quit_application()
        elif key == Qt.Key.Key_M:
            self._set_mode_by_legacy_key("price_only")
        elif key == Qt.Key.Key_N:
            self._set_mode_by_legacy_key("chinese")
        elif key == Qt.Key.Key_P:
            self._set_mode_by_legacy_key("pinyin")
        elif key == Qt.Key.Key_G:
            self._set_mode_by_legacy_key("pinyin_change")

    def closeEvent(self, event):
        self.quit_application()
        event.accept()
