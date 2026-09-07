"""Theme singleton for Atlas OS Dashboard.

Provides a cohesive, futuristic edge-AI operating system design language.
Engineered for high contrast, touch ergonomics, and 60 FPS performance on Raspberry Pi 5.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal
from PySide6.QtGui import QColor


class ThemeSingleton(QObject):
    """QML-accessible theme singleton with modern AtlasOS design tokens."""

    themeChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._dark_mode = True

    # -----------------------------------------------------------------------
    # Background Colors (Layered Depth)
    # -----------------------------------------------------------------------
    @Property(QColor, constant=True)
    def bgPrimary(self) -> QColor:
        """Deepest background canvas."""
        return QColor("#0d1017")

    @Property(QColor, constant=True)
    def bgPanel(self) -> QColor:
        """Card and panel background."""
        return QColor("#161b24")

    @Property(QColor, constant=True)
    def bgElevated(self) -> QColor:
        """Hovered, selected, or elevated item background."""
        return QColor("#212836")

    @Property(QColor, constant=True)
    def bgSurface(self) -> QColor:
        """Interactive control surface (inputs, buttons)."""
        return QColor("#283142")

    @Property(QColor, constant=True)
    def bgSecondary(self) -> QColor:
        """Sidebar / sub-panel background."""
        return QColor("#12161f")

    @Property(QColor, constant=True)
    def bgTertiary(self) -> QColor:
        return QColor("#1e2430")

    # -----------------------------------------------------------------------
    # Primary & Secondary Accents
    # -----------------------------------------------------------------------
    @Property(QColor, constant=True)
    def accentCyan(self) -> QColor:
        """Atlas Core Neon Cyan."""
        return QColor("#00e5ff")

    @Property(QColor, constant=True)
    def accent(self) -> QColor:
        """Primary action accent (Vibrant Blue/Cyan)."""
        return QColor("#00a6ff")

    @Property(QColor, constant=True)
    def accentHover(self) -> QColor:
        return QColor("#33b8ff")

    @Property(QColor, constant=True)
    def accentPurple(self) -> QColor:
        """AI / Neural accent."""
        return QColor("#b388ff")

    @Property(QColor, constant=True)
    def accentAmber(self) -> QColor:
        """Energy / Hardware accent."""
        return QColor("#ffab00")

    @Property(QColor, constant=True)
    def accentPink(self) -> QColor:
        return QColor("#ff4081")

    @Property(QColor, constant=True)
    def accentGreen(self) -> QColor:
        return QColor("#00e676")

    @Property(QColor, constant=True)
    def accentOrange(self) -> QColor:
        return QColor("#ff9100")

    @Property(QColor, constant=True)
    def accentRed(self) -> QColor:
        return QColor("#ff5252")

    # -----------------------------------------------------------------------
    # Typography & Text Colors
    # -----------------------------------------------------------------------
    @Property(QColor, constant=True)
    def textPrimary(self) -> QColor:
        """Crisp high-contrast white text."""
        return QColor("#f0f4fc")

    @Property(QColor, constant=True)
    def textSecondary(self) -> QColor:
        """Readable secondary label text."""
        return QColor("#a0aec0")

    @Property(QColor, constant=True)
    def textMuted(self) -> QColor:
        """Subdued metadata / inactive text."""
        return QColor("#64748b")

    # -----------------------------------------------------------------------
    # Semantic Status Colors
    # -----------------------------------------------------------------------
    @Property(QColor, constant=True)
    def success(self) -> QColor:
        """Online / Healthy / Success."""
        return QColor("#00e676")

    @Property(QColor, constant=True)
    def warning(self) -> QColor:
        """Degraded / High load / Warning."""
        return QColor("#ffd600")

    @Property(QColor, constant=True)
    def danger(self) -> QColor:
        """Error / Offline / Fatal."""
        return QColor("#ff1744")

    @Property(QColor, constant=True)
    def info(self) -> QColor:
        """Information / Notice."""
        return QColor("#00b0ff")

    @Property(QColor, constant=True)
    def offline(self) -> QColor:
        """Offline / Disabled."""
        return QColor("#475569")

    # -----------------------------------------------------------------------
    # Borders & Outlines
    # -----------------------------------------------------------------------
    @Property(QColor, constant=True)
    def border(self) -> QColor:
        return QColor("#2a3447")

    @Property(QColor, constant=True)
    def borderSubtle(self) -> QColor:
        return QColor("#1e2736")

    @Property(QColor, constant=True)
    def borderFocus(self) -> QColor:
        return QColor("#00e5ff")

    # -----------------------------------------------------------------------
    # Spacing & Metrics
    # -----------------------------------------------------------------------
    @Property(int, constant=True)
    def radiusXs(self) -> int:
        return 4

    @Property(int, constant=True)
    def radiusSm(self) -> int:
        return 6

    @Property(int, constant=True)
    def radiusMd(self) -> int:
        return 10

    @Property(int, constant=True)
    def radiusLg(self) -> int:
        return 16

    @Property(int, constant=True)
    def radiusXl(self) -> int:
        return 24

    @Property(int, constant=True)
    def spacingXs(self) -> int:
        return 4

    @Property(int, constant=True)
    def spacingSm(self) -> int:
        return 8

    @Property(int, constant=True)
    def spacingMd(self) -> int:
        return 14

    @Property(int, constant=True)
    def spacingLg(self) -> int:
        return 20

    @Property(int, constant=True)
    def spacingXl(self) -> int:
        return 28

    # -----------------------------------------------------------------------
    # Fonts
    # -----------------------------------------------------------------------
    @Property(str, constant=True)
    def fontMono(self) -> str:
        return "\"JetBrains Mono\", \"Fira Code\", \"Cascadia Code\", monospace"

    @Property(str, constant=True)
    def fontSans(self) -> str:
        return "\"Inter\", \"Roboto\", \"Segoe UI\", sans-serif"

    # -----------------------------------------------------------------------
    # Animation Durations (ms)
    # -----------------------------------------------------------------------
    @Property(int, constant=True)
    def animFast(self) -> int:
        return 120

    @Property(int, constant=True)
    def animNormal(self) -> int:
        return 200

    @Property(int, constant=True)
    def animSlow(self) -> int:
        return 350