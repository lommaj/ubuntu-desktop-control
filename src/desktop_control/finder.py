"""
Element finder with AT-SPI primary and OCR fallback.

Orchestrates element finding using the accessibility tree first,
falling back to OCR when AT-SPI doesn't find the element.
"""

from typing import Optional

from .element import Element, ElementSource
from . import atspi
from . import ocr
from .screenshot import screenshot_to_pil


class ElementFinder:
    """
    Unified element finder using AT-SPI and OCR.

    AT-SPI is tried first as it provides richer element information
    (role, states, actions). OCR is used as fallback when AT-SPI
    doesn't find the element.
    """

    def __init__(
        self,
        display: Optional[str] = None,
        use_atspi: bool = True,
        use_ocr: bool = True,
        ocr_min_confidence: float = 30.0
    ):
        """
        Initialize the element finder.

        Args:
            display: X display to use for screenshots
            use_atspi: Whether to use AT-SPI (primary method)
            use_ocr: Whether to use OCR (fallback method)
            ocr_min_confidence: Minimum OCR confidence threshold
        """
        self.display = display
        self.use_atspi = use_atspi and atspi.is_available()
        self.use_ocr = use_ocr and ocr.is_available()
        self.ocr_min_confidence = ocr_min_confidence

        # Cache for screenshot (cleared after each find operation)
        self._screenshot_cache = None

    def find(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        app: Optional[str] = None,
        visible_only: bool = True
    ) -> Optional[Element]:
        """
        Find a single element matching the criteria.

        Tries AT-SPI first, then falls back to OCR.

        Args:
            name: Element text/name to find
            role: Element role (AT-SPI only, e.g., "button")
            app: Application name filter (AT-SPI only)
            visible_only: Only find visible elements

        Returns:
            Element if found, None otherwise
        """
        self._screenshot_cache = None

        # Try AT-SPI first
        if self.use_atspi:
            atspi_elem = atspi.find_element(
                name=name,
                role=role,
                app=app,
                visible_only=visible_only
            )
            if atspi_elem:
                return Element.from_atspi(atspi_elem)

        # Fall back to OCR if name is provided
        if self.use_ocr and name:
            ocr_match = self._find_text_ocr(name)
            if ocr_match:
                return Element.from_ocr(ocr_match)

        return None

    def find_all(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        app: Optional[str] = None,
        visible_only: bool = True,
        clickable_only: bool = False,
        max_results: int = 50
    ) -> list[Element]:
        """
        Find all elements matching the criteria.

        Args:
            name: Element text/name to find (partial match)
            role: Element role (AT-SPI only)
            app: Application name filter (AT-SPI only)
            visible_only: Only find visible elements
            clickable_only: Only find clickable elements
            max_results: Maximum number of results

        Returns:
            List of matching Elements
        """
        self._screenshot_cache = None
        results = []

        # Get AT-SPI results
        if self.use_atspi:
            atspi_results = atspi.find_elements(
                name=name,
                role=role,
                app=app,
                visible_only=visible_only,
                clickable_only=clickable_only,
                max_results=max_results
            )
            results.extend(Element.from_atspi(e) for e in atspi_results)

        # Add OCR results if name search and not enough AT-SPI results
        if self.use_ocr and name and len(results) < max_results:
            remaining = max_results - len(results)
            ocr_matches = self._find_all_text_ocr(name, max_results=remaining)

            # Filter out OCR matches that overlap with AT-SPI results
            for match in ocr_matches:
                ocr_elem = Element.from_ocr(match)
                if not self._overlaps_any(ocr_elem, results):
                    results.append(ocr_elem)

        return results[:max_results]

    def find_text(
        self,
        text: str,
        exact: bool = False,
        case_sensitive: bool = False
    ) -> Optional[Element]:
        """
        Find text on screen using OCR.

        This method uses OCR directly, skipping AT-SPI.
        Use this when you specifically want to find visible text
        regardless of element type.

        Args:
            text: Text to find
            exact: Require exact match
            case_sensitive: Case-sensitive matching

        Returns:
            Element if found, None otherwise
        """
        if not self.use_ocr:
            return None

        self._screenshot_cache = None
        img = self._get_screenshot()
        if img is None:
            return None

        matches = ocr.find_text(
            img,
            text,
            exact=exact,
            case_sensitive=case_sensitive,
            min_confidence=self.ocr_min_confidence
        )

        if matches:
            return Element.from_ocr(matches[0])
        return None

    def find_all_text(
        self,
        text: str,
        exact: bool = False,
        case_sensitive: bool = False,
        max_results: int = 50
    ) -> list[Element]:
        """
        Find all occurrences of text on screen using OCR.

        Args:
            text: Text to find
            exact: Require exact match
            case_sensitive: Case-sensitive matching
            max_results: Maximum number of results

        Returns:
            List of Elements for each text occurrence
        """
        if not self.use_ocr:
            return []

        self._screenshot_cache = None
        img = self._get_screenshot()
        if img is None:
            return []

        matches = ocr.find_text(
            img,
            text,
            exact=exact,
            case_sensitive=case_sensitive,
            min_confidence=self.ocr_min_confidence
        )

        return [Element.from_ocr(m) for m in matches[:max_results]]

    def list_interactive(
        self,
        app: Optional[str] = None,
        visible_only: bool = True
    ) -> list[Element]:
        """
        List all interactive elements (buttons, links, inputs, etc.)

        Uses AT-SPI only as OCR can't determine interactivity.

        Args:
            app: Application name filter
            visible_only: Only list visible elements

        Returns:
            List of interactive Elements
        """
        if not self.use_atspi:
            return []

        atspi_results = atspi.list_interactive_elements(
            app=app,
            visible_only=visible_only
        )
        return [Element.from_atspi(e) for e in atspi_results]

    def _get_screenshot(self):
        """Get screenshot, using cache if available."""
        if self._screenshot_cache is not None:
            return self._screenshot_cache

        self._screenshot_cache = screenshot_to_pil(self.display)
        return self._screenshot_cache

    def _find_text_ocr(self, text: str):
        """Find text using OCR."""
        img = self._get_screenshot()
        if img is None:
            return None

        matches = ocr.find_text(
            img,
            text,
            exact=False,
            case_sensitive=False,
            min_confidence=self.ocr_min_confidence
        )

        return matches[0] if matches else None

    def _find_all_text_ocr(self, text: str, max_results: int = 50):
        """Find all text using OCR."""
        img = self._get_screenshot()
        if img is None:
            return []

        return ocr.find_text(
            img,
            text,
            exact=False,
            case_sensitive=False,
            min_confidence=self.ocr_min_confidence
        )[:max_results]

    def _overlaps_any(
        self,
        elem: Element,
        others: list[Element],
        threshold: float = 0.5
    ) -> bool:
        """Check if element overlaps with any in the list."""
        for other in others:
            if self._boxes_overlap(elem, other, threshold):
                return True
        return False

    def _boxes_overlap(
        self,
        elem1: Element,
        elem2: Element,
        threshold: float
    ) -> bool:
        """Check if two elements overlap beyond the threshold."""
        x1 = max(elem1.x, elem2.x)
        y1 = max(elem1.y, elem2.y)
        x2 = min(elem1.x + elem1.width, elem2.x + elem2.width)
        y2 = min(elem1.y + elem1.height, elem2.y + elem2.height)

        if x1 >= x2 or y1 >= y2:
            return False

        intersection = (x2 - x1) * (y2 - y1)
        area1 = elem1.width * elem1.height
        area2 = elem2.width * elem2.height
        smaller_area = min(area1, area2)

        if smaller_area == 0:
            return False

        return intersection / smaller_area >= threshold


# Convenience functions using default finder
_default_finder: Optional[ElementFinder] = None


def get_finder(display: Optional[str] = None) -> ElementFinder:
    """Get or create the default element finder."""
    global _default_finder
    if _default_finder is None:
        _default_finder = ElementFinder(display=display)
    return _default_finder


def find_element(
    name: Optional[str] = None,
    role: Optional[str] = None,
    app: Optional[str] = None,
    display: Optional[str] = None
) -> Optional[Element]:
    """Find a single element (convenience function)."""
    return get_finder(display).find(name=name, role=role, app=app)


def find_text(
    text: str,
    exact: bool = False,
    display: Optional[str] = None
) -> Optional[Element]:
    """Find text on screen via OCR (convenience function)."""
    return get_finder(display).find_text(text, exact=exact)
