"""
Element caching for click-by-ID functionality.

Provides a cache with TTL for storing elements found during
screenshot annotation, enabling subsequent click-id commands.
"""

import time
from typing import Optional
from .element import Element


class ElementCache:
    """
    Cache for storing elements with automatic expiration.

    Elements are stored with numeric IDs (1-based) and expire
    after TTL seconds or when screen size changes.
    """

    TTL = 5.0  # Cache time-to-live in seconds

    def __init__(self):
        self._elements: dict[int, Element] = {}
        self._timestamp: float = 0.0
        self._screen_size: tuple[int, int] = (0, 0)

    def store(
        self,
        elements: list[Element],
        screen_size: tuple[int, int]
    ) -> dict[int, Element]:
        """
        Store elements in the cache with 1-based IDs.

        Args:
            elements: List of Element objects to cache
            screen_size: Current screen dimensions (width, height)

        Returns:
            Dict mapping element IDs to Elements
        """
        self._elements = {i: elem for i, elem in enumerate(elements, start=1)}
        self._timestamp = time.time()
        self._screen_size = screen_size
        return self._elements

    def get(self, element_id: int) -> Optional[Element]:
        """
        Get a cached element by ID.

        Args:
            element_id: 1-based element ID

        Returns:
            Element if found and cache is valid, None otherwise
        """
        if not self.is_valid():
            return None
        return self._elements.get(element_id)

    def get_all(self) -> dict[int, Element]:
        """
        Get all cached elements.

        Returns:
            Dict mapping element IDs to Elements, empty if cache invalid
        """
        if not self.is_valid():
            return {}
        return self._elements.copy()

    def is_valid(self) -> bool:
        """
        Check if the cache is still valid.

        Cache is invalid if:
        - TTL has expired
        - Cache is empty

        Returns:
            True if cache is valid and usable
        """
        if not self._elements:
            return False

        age = time.time() - self._timestamp
        return age < self.TTL

    def invalidate(self) -> None:
        """Clear the cache."""
        self._elements = {}
        self._timestamp = 0.0
        self._screen_size = (0, 0)

    def check_screen_size(self, screen_size: tuple[int, int]) -> bool:
        """
        Check if screen size matches cached size.

        If sizes don't match, cache is invalidated.

        Args:
            screen_size: Current screen dimensions (width, height)

        Returns:
            True if sizes match, False if cache was invalidated
        """
        if self._screen_size != screen_size:
            self.invalidate()
            return False
        return True

    @property
    def count(self) -> int:
        """Number of cached elements."""
        return len(self._elements) if self.is_valid() else 0

    @property
    def age(self) -> float:
        """Age of cache in seconds."""
        if self._timestamp == 0:
            return float('inf')
        return time.time() - self._timestamp

    @property
    def screen_size(self) -> tuple[int, int]:
        """Cached screen size."""
        return self._screen_size


# Global cache instance
_cache: Optional[ElementCache] = None


def get_cache() -> ElementCache:
    """Get the global element cache."""
    global _cache
    if _cache is None:
        _cache = ElementCache()
    return _cache


def store_elements(
    elements: list[Element],
    screen_size: tuple[int, int]
) -> dict[int, Element]:
    """Store elements in the global cache."""
    return get_cache().store(elements, screen_size)


def get_element(element_id: int) -> Optional[Element]:
    """Get an element from the global cache by ID."""
    return get_cache().get(element_id)


def get_all_elements() -> dict[int, Element]:
    """Get all elements from the global cache."""
    return get_cache().get_all()


def is_cache_valid() -> bool:
    """Check if the global cache is valid."""
    return get_cache().is_valid()


def invalidate_cache() -> None:
    """Invalidate the global cache."""
    get_cache().invalidate()
