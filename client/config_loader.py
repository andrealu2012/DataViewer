"""Client configuration helpers."""

import json
import os
import shutil
import sys
from datetime import datetime
from typing import Dict, List


def runtime_dir() -> str:
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            app_support = os.path.expanduser("~/Library/Application Support/DataViewer")
            os.makedirs(app_support, exist_ok=True)
            return app_support
        if sys.platform.startswith("linux"):
            config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
            app_config = os.path.join(config_home, "DataViewer")
            os.makedirs(app_config, exist_ok=True)
            return app_config
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def bundled_file(filename: str) -> str:
    """Return a read-only file bundled by PyInstaller, when available."""
    bundle_dir = getattr(sys, "_MEIPASS", None)
    if bundle_dir:
        return os.path.join(bundle_dir, filename)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)


def normalize_stock_code(code: str) -> str:
    code = str(code).strip().upper()
    if "." in code:
        return code
    if not code.isdigit():
        return code
    if len(code) == 6:
        if code.startswith(("60", "68", "51", "50", "58", "56")):
            return f"{code}.SH"
        if code.startswith(("00", "30", "20", "15", "16", "18")):
            return f"{code}.SZ"
    return code


def normalize_codes(codes: List[str]) -> List[str]:
    return [normalize_stock_code(code) for code in codes]


def default_config() -> Dict:
    return {
        "stocks": ["600143.SH", "000612.SZ"],
        "trading_hours": {
            "enabled": True,
            "morning_start": "09:30",
            "morning_end": "11:30",
            "afternoon_start": "13:00",
            "afternoon_end": "15:00",
        },
        "update_interval_ms": 3000,
        "display_modes": [
            {"name": "Price + Change", "name_display": "none", "show_price": True, "show_change": True},
            {"name": "Chinese + Price + Change", "name_display": "chinese", "show_price": True, "show_change": True},
            {"name": "Pinyin + Price + Change", "name_display": "pinyin", "show_price": True, "show_change": True},
            {"name": "Pinyin + Change", "name_display": "pinyin", "show_price": False, "show_change": True},
        ],
        "hotkey": {"enabled": True, "key": "f3", "modifier": "ctrl"},
        "ui": {
            "active_text_color": "#FFFFFF",
            "inactive_text_color": "#000000",
            "label_bg_color": "rgba(30, 30, 30, 160)",
            "window_bg_color": "rgba(20, 20, 20, 180)",
            "border_color": "rgba(100, 100, 100, 100)",
            "font_family": "'Consolas','Microsoft YaHei','Courier New','monospace'",
            "font_size": 12,
            "increase_color": "#FF4444",
            "decrease_color": "#44DD44",
        },
    }


def load_config(config_file: str = "config.json") -> Dict:
    config_path = os.path.join(runtime_dir(), config_file)
    cfg = default_config()

    if not os.path.exists(config_path):
        bundled_config = bundled_file(config_file)
        if os.path.isfile(bundled_config) and os.path.abspath(bundled_config) != os.path.abspath(config_path):
            shutil.copy2(bundled_config, config_path)
        else:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        if os.path.exists(config_path):
            return load_config(config_file)
        return cfg

    try:
        with open(config_path, "r", encoding="utf-8-sig") as f:
            loaded = json.load(f)
        cfg.update(loaded)
        if "ui" in loaded:
            base_ui = default_config()["ui"]
            base_ui.update(loaded["ui"])
            cfg["ui"] = base_ui
        if isinstance(cfg.get("stocks"), list):
            cfg["stocks"] = normalize_codes(cfg["stocks"])
        return cfg
    except Exception as exc:
        print(f"Failed to load config: {exc}. Using defaults.")
        return cfg


def save_config(config: Dict, config_file: str = "config.json") -> None:
    """Persist a client configuration without risking a partially written file."""
    config_path = os.path.join(runtime_dir(), config_file)
    temp_path = f"{config_path}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(temp_path, config_path)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def is_trading_hours(config: Dict) -> bool:
    trading = config.get("trading_hours", {})
    if not trading.get("enabled", True):
        return True

    now = datetime.now()
    if now.weekday() >= 5:
        return False

    try:
        current_time = now.time()
        morning_start = datetime.strptime(trading.get("morning_start", "09:30"), "%H:%M").time()
        morning_end = datetime.strptime(trading.get("morning_end", "11:30"), "%H:%M").time()
        afternoon_start = datetime.strptime(trading.get("afternoon_start", "13:00"), "%H:%M").time()
        afternoon_end = datetime.strptime(trading.get("afternoon_end", "15:00"), "%H:%M").time()
        return morning_start <= current_time <= morning_end or afternoon_start <= current_time <= afternoon_end
    except Exception as exc:
        print(f"Failed to check trading hours: {exc}. Treating as active.")
        return True
