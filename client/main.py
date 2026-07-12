"""RealDataView client entrypoint."""

import sys

from PyQt6.QtWidgets import QApplication

from config_loader import load_config
from disclaimer_dialog import ensure_disclaimer_accepted
from stock_overlay import StockOverlay


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setOrganizationName("RealDataView")
    app.setApplicationName("DataViewer")

    if not ensure_disclaimer_accepted():
        return 0

    config = load_config("config.json")
    stock_codes = config.get("stocks", [])
    if not stock_codes:
        print("No stocks configured. Edit client/config.json first.")
        return 1

    overlay = StockOverlay(
        stock_codes,
        update_interval=int(config.get("update_interval_ms", 3000)),
        config=config,
    )
    overlay.hide()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
