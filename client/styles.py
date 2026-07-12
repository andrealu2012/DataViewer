"""Small UI constants shared by the overlay."""

from PyQt6.QtGui import QColor

LABEL_MIN_HEIGHT = 5


def parse_qcolor(value: str, default=(20, 20, 20, 200)) -> QColor:
    try:
        if not value:
            return QColor(*default)

        text = str(value).strip()
        if text.startswith("#"):
            return QColor(text)
        if text.startswith("rgba"):
            inside = text[text.find("(") + 1:text.rfind(")")]
            parts = [p.strip() for p in inside.split(",")]
            if len(parts) >= 4:
                r = int(float(parts[0]))
                g = int(float(parts[1]))
                b = int(float(parts[2]))
                alpha = float(parts[3])
                a = int(alpha * 255) if 0.0 <= alpha <= 1.0 else int(alpha)
                return QColor(r, g, b, a)
        return QColor(text)
    except Exception:
        return QColor(*default)
