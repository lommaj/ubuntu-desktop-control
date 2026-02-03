"""
Desktop Control - Semantic UI automation for Ubuntu/X11.

Provides AT-SPI accessibility tree and OCR-based element finding
with xdotool for mouse/keyboard control.
"""

from .element import Element
from .finder import ElementFinder
from .waiter import Waiter

__version__ = "2.0.0"
__all__ = ["Element", "ElementFinder", "Waiter"]
