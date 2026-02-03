"""
Unified Element class representing UI elements from any source.

Provides a common interface for elements found via AT-SPI or OCR.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ElementSource(Enum):
    """Source of the element."""
    ATSPI = "atspi"
    OCR = "ocr"


@dataclass
class Element:
    """
    Unified UI element representation.

    Can be created from AT-SPI accessibility tree or OCR detection.
    """
    # Core properties
    name: str
    x: int
    y: int
    width: int
    height: int
    source: ElementSource

    # AT-SPI specific (optional)
    role: str = ""
    role_name: str = ""
    description: str = ""
    states: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    app_name: str = ""

    # OCR specific (optional)
    confidence: float = 100.0

    @property
    def center(self) -> tuple[int, int]:
        """Get center coordinates of the element."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def center_x(self) -> int:
        """Get center X coordinate."""
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        """Get center Y coordinate."""
        return self.y + self.height // 2

    @property
    def is_visible(self) -> bool:
        """Check if element is visible (AT-SPI only, OCR assumed visible)."""
        if self.source == ElementSource.OCR:
            return True
        return "visible" in self.states and "showing" in self.states

    @property
    def is_enabled(self) -> bool:
        """Check if element is enabled."""
        if self.source == ElementSource.OCR:
            return True
        return "enabled" in self.states or "sensitive" in self.states

    @property
    def is_clickable(self) -> bool:
        """Check if element has click action."""
        if self.source == ElementSource.OCR:
            return True  # OCR results are assumed clickable
        return "click" in self.actions or "press" in self.actions

    @property
    def is_button(self) -> bool:
        """Check if element is a button."""
        if self.source == ElementSource.OCR:
            return False  # Can't determine from OCR alone
        return "button" in self.role_name.lower()

    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within the element bounds."""
        return (
            self.x <= x <= self.x + self.width and
            self.y <= y <= self.y + self.height
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "name": self.name,
            "bounds": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height
            },
            "center": {"x": self.center_x, "y": self.center_y},
            "source": self.source.value,
        }

        if self.source == ElementSource.ATSPI:
            result.update({
                "role": self.role_name,
                "description": self.description,
                "states": self.states,
                "actions": self.actions,
                "app_name": self.app_name,
                "visible": self.is_visible,
                "enabled": self.is_enabled,
                "clickable": self.is_clickable
            })
        else:
            result["confidence"] = self.confidence

        return result

    @classmethod
    def from_atspi(cls, atspi_element) -> "Element":
        """Create Element from ATSPIElement."""
        return cls(
            name=atspi_element.name,
            x=atspi_element.x,
            y=atspi_element.y,
            width=atspi_element.width,
            height=atspi_element.height,
            source=ElementSource.ATSPI,
            role=atspi_element.role,
            role_name=atspi_element.role_name,
            description=atspi_element.description,
            states=atspi_element.states,
            actions=atspi_element.actions,
            app_name=atspi_element.app_name
        )

    @classmethod
    def from_ocr(cls, ocr_match) -> "Element":
        """Create Element from OCRMatch."""
        return cls(
            name=ocr_match.text,
            x=ocr_match.x,
            y=ocr_match.y,
            width=ocr_match.width,
            height=ocr_match.height,
            source=ElementSource.OCR,
            confidence=ocr_match.confidence
        )


def merge_elements(
    atspi_elements: list,
    ocr_elements: list,
    overlap_threshold: float = 0.5
) -> list[Element]:
    """
    Merge elements from AT-SPI and OCR, preferring AT-SPI.

    AT-SPI elements take precedence when they overlap with OCR elements,
    as they have richer metadata (role, states, actions).

    Args:
        atspi_elements: Elements from AT-SPI
        ocr_elements: Elements from OCR
        overlap_threshold: Minimum overlap ratio to consider elements the same

    Returns:
        Merged list of Elements
    """
    # Convert to unified Elements
    result = [Element.from_atspi(e) for e in atspi_elements]

    # Add OCR elements that don't overlap with AT-SPI elements
    for ocr_elem in ocr_elements:
        ocr_box = Element.from_ocr(ocr_elem)

        # Check if this OCR element overlaps with any AT-SPI element
        overlaps = False
        for atspi_elem in result:
            if _boxes_overlap(atspi_elem, ocr_box, overlap_threshold):
                overlaps = True
                break

        if not overlaps:
            result.append(ocr_box)

    return result


def _boxes_overlap(elem1: Element, elem2: Element, threshold: float) -> bool:
    """Check if two elements overlap beyond the threshold."""
    # Calculate intersection
    x1 = max(elem1.x, elem2.x)
    y1 = max(elem1.y, elem2.y)
    x2 = min(elem1.x + elem1.width, elem2.x + elem2.width)
    y2 = min(elem1.y + elem1.height, elem2.y + elem2.height)

    if x1 >= x2 or y1 >= y2:
        return False

    intersection = (x2 - x1) * (y2 - y1)

    # Calculate smaller box area
    area1 = elem1.width * elem1.height
    area2 = elem2.width * elem2.height
    smaller_area = min(area1, area2)

    if smaller_area == 0:
        return False

    overlap_ratio = intersection / smaller_area
    return overlap_ratio >= threshold
