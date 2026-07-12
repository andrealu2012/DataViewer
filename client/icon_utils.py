"""Helpers for loading user-replaceable client icons."""

import os
import sys

from PyQt6.QtGui import QIcon


def client_base_dir() -> str:
    """Return the directory containing config.json and the icons folder."""
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_icon(path: str) -> QIcon:
    """Load an absolute path or a path relative to the client directory."""
    if not path:
        return QIcon()
    if os.path.isabs(path):
        candidates = [path]
    else:
        candidates = [os.path.join(client_base_dir(), path)]
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            candidates.append(os.path.join(bundle_dir, path))
    icon_file = next((candidate for candidate in candidates if os.path.isfile(candidate)), None)
    return QIcon(icon_file) if icon_file else QIcon()
