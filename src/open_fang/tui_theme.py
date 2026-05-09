"""OpenFang brand — fang amber + ink-black."""
from __future__ import annotations

from harness_tui.theme import Theme
from harness_tui.themes import catppuccin_mocha

OPENFANG_LOGO = r"""
   [bold #F97316]\\\\[/]    [bold #F97316]////[/]
    [bold #F97316]\\[/]    [bold #F97316]/[/]
     [bold #F97316]\\[/]  [bold #F97316]/[/]      [dim]OpenFang[/]
      [bold #F97316]\\/[/]
     fangs.
""".strip("\n")


def openfang_theme() -> Theme:
    return catppuccin_mocha().with_brand(
        name="open-fang",
        primary="#F97316",
        primary_alt="#9A3412",
        accent="#FACC15",
        ascii_logo=OPENFANG_LOGO,
        spinner_frames=("◢", "◣", "◤", "◥"),
    )
