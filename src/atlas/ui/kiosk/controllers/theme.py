"""Design tokens for the Atlas OS touch kiosk UI, exposed to QML as a singleton.

Kept in Python rather than a QML ``pragma Singleton`` for two reasons: it is
trivially unit-testable, and the same token set can later be shared with a
browser-based dashboard's theme without duplicating color values in QML/JS.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject


class ThemeSingleton(QObject):
    """Read-only color/spacing tokens for the kiosk UI.

    Registered with the QML engine as the ``Theme`` singleton (see
    ``atlas.ui.kiosk.main``), so QML reads these as e.g. ``Theme.bgPrimary``.
    """

    # -- Colors: dark, PCB/datasheet-inspired palette ------------------------

    @Property(str, constant=True)
    def bgPrimary(self) -> str:
        return "#0a0e14"

    @Property(str, constant=True)
    def bgPanel(self) -> str:
        return "#121a24"

    @Property(str, constant=True)
    def bgElevated(self) -> str:
        return "#1a2432"

    @Property(str, constant=True)
    def borderSubtle(self) -> str:
        return "#26313f"

    @Property(str, constant=True)
    def accentCyan(self) -> str:
        return "#22d3ee"

    @Property(str, constant=True)
    def accentAmber(self) -> str:
        return "#f5a623"

    @Property(str, constant=True)
    def textPrimary(self) -> str:
        return "#e7edf3"

    @Property(str, constant=True)
    def textMuted(self) -> str:
        return "#7d8b9c"

    @Property(str, constant=True)
    def danger(self) -> str:
        return "#ef4444"

    @Property(str, constant=True)
    def success(self) -> str:
        return "#34d399"

    # -- Layout tokens --------------------------------------------------------

    @Property(int, constant=True)
    def radiusSm(self) -> int:
        return 6

    @Property(int, constant=True)
    def radiusMd(self) -> int:
        return 14

    @Property(int, constant=True)
    def radiusLg(self) -> int:
        return 24

    @Property(int, constant=True)
    def spacing(self) -> int:
        return 14

    @Property(str, constant=True)
    def fontMono(self) -> str:
        return "monospace"
