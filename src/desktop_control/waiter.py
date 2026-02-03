"""
Wait-for-condition utilities with polling and exponential backoff.

Provides reliable waiting for UI elements to appear or disappear.
"""

import time
from typing import Optional, Callable

from .element import Element
from .finder import ElementFinder


class WaitTimeout(Exception):
    """Raised when a wait operation times out."""
    pass


class Waiter:
    """
    Wait for UI conditions with configurable polling.

    Uses exponential backoff to balance responsiveness with CPU usage.
    """

    def __init__(
        self,
        finder: Optional[ElementFinder] = None,
        display: Optional[str] = None,
        initial_interval: float = 0.5,
        max_interval: float = 2.0,
        backoff_factor: float = 1.5
    ):
        """
        Initialize the waiter.

        Args:
            finder: ElementFinder to use (creates one if not provided)
            display: X display for screenshots
            initial_interval: Starting poll interval in seconds
            max_interval: Maximum poll interval in seconds
            backoff_factor: Multiplier for interval after each poll
        """
        self.finder = finder or ElementFinder(display=display)
        self.initial_interval = initial_interval
        self.max_interval = max_interval
        self.backoff_factor = backoff_factor

    def wait_for_element(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        app: Optional[str] = None,
        timeout: float = 30.0
    ) -> Element:
        """
        Wait for an element to appear.

        Uses AT-SPI with OCR fallback through ElementFinder.

        Args:
            name: Element name/text to find
            role: Element role (AT-SPI only)
            app: Application name filter (AT-SPI only)
            timeout: Maximum time to wait in seconds

        Returns:
            Element when found

        Raises:
            WaitTimeout: If element doesn't appear within timeout
        """
        def condition():
            return self.finder.find(name=name, role=role, app=app)

        element = self._poll_until(condition, timeout)
        if element is None:
            msg = f"Element not found within {timeout}s"
            if name:
                msg += f" (name='{name}')"
            if role:
                msg += f" (role='{role}')"
            raise WaitTimeout(msg)

        return element

    def wait_for_text(
        self,
        text: str,
        exact: bool = False,
        timeout: float = 30.0
    ) -> Element:
        """
        Wait for text to appear on screen.

        Uses OCR to find the text.

        Args:
            text: Text to find
            exact: Require exact match
            timeout: Maximum time to wait in seconds

        Returns:
            Element when text is found

        Raises:
            WaitTimeout: If text doesn't appear within timeout
        """
        def condition():
            return self.finder.find_text(text, exact=exact)

        element = self._poll_until(condition, timeout)
        if element is None:
            raise WaitTimeout(f"Text '{text}' not found within {timeout}s")

        return element

    def wait_until_gone(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        text: Optional[str] = None,
        timeout: float = 30.0
    ) -> bool:
        """
        Wait for an element or text to disappear.

        Useful for waiting for popups to close or loading indicators
        to disappear.

        Args:
            name: Element name (AT-SPI with OCR fallback)
            role: Element role (AT-SPI only)
            text: Text to find (OCR only)
            timeout: Maximum time to wait in seconds

        Returns:
            True when element/text is gone

        Raises:
            WaitTimeout: If element/text doesn't disappear within timeout
        """
        def condition():
            if text:
                elem = self.finder.find_text(text)
            else:
                elem = self.finder.find(name=name, role=role)

            # Return True when element is NOT found (gone)
            return True if elem is None else None

        result = self._poll_until(condition, timeout)
        if result is None:
            target = text or name or "element"
            raise WaitTimeout(f"'{target}' still present after {timeout}s")

        return True

    def wait_for_any(
        self,
        elements: list[dict],
        timeout: float = 30.0
    ) -> tuple[int, Element]:
        """
        Wait for any of the specified elements to appear.

        Args:
            elements: List of element specs, each a dict with keys:
                      name, role, app (same as find() parameters)
            timeout: Maximum time to wait in seconds

        Returns:
            Tuple of (index of matched element spec, Element)

        Raises:
            WaitTimeout: If no element appears within timeout
        """
        def condition():
            for i, spec in enumerate(elements):
                elem = self.finder.find(
                    name=spec.get("name"),
                    role=spec.get("role"),
                    app=spec.get("app")
                )
                if elem:
                    return (i, elem)
            return None

        result = self._poll_until(condition, timeout)
        if result is None:
            raise WaitTimeout(f"None of {len(elements)} elements found within {timeout}s")

        return result

    def wait_for_stable(
        self,
        name: Optional[str] = None,
        role: Optional[str] = None,
        stability_time: float = 0.5,
        timeout: float = 30.0
    ) -> Element:
        """
        Wait for an element to appear and stay stable.

        An element is considered stable when its position doesn't
        change for stability_time seconds. Useful for waiting for
        animations to complete.

        Args:
            name: Element name
            role: Element role
            stability_time: How long position must be stable
            timeout: Maximum time to wait in seconds

        Returns:
            Element when stable

        Raises:
            WaitTimeout: If element doesn't stabilize within timeout
        """
        start_time = time.time()
        last_pos = None
        stable_since = None

        while time.time() - start_time < timeout:
            elem = self.finder.find(name=name, role=role)

            if elem:
                current_pos = (elem.x, elem.y)

                if last_pos == current_pos:
                    # Position unchanged
                    if stable_since is None:
                        stable_since = time.time()
                    elif time.time() - stable_since >= stability_time:
                        return elem
                else:
                    # Position changed, reset stability timer
                    last_pos = current_pos
                    stable_since = time.time()
            else:
                # Element not found, reset
                last_pos = None
                stable_since = None

            time.sleep(self.initial_interval)

        raise WaitTimeout(
            f"Element didn't stabilize within {timeout}s "
            f"(name='{name}', role='{role}')"
        )

    def wait_with_callback(
        self,
        condition_fn: Callable[[], Optional[any]],
        timeout: float = 30.0
    ) -> any:
        """
        Wait for a custom condition.

        Args:
            condition_fn: Function that returns a truthy value when
                         condition is met, None/False otherwise
            timeout: Maximum time to wait in seconds

        Returns:
            The truthy value returned by condition_fn

        Raises:
            WaitTimeout: If condition not met within timeout
        """
        result = self._poll_until(condition_fn, timeout)
        if result is None:
            raise WaitTimeout(f"Custom condition not met within {timeout}s")
        return result

    def _poll_until(
        self,
        condition: Callable[[], Optional[any]],
        timeout: float
    ) -> Optional[any]:
        """
        Poll a condition until it returns a truthy value or timeout.

        Uses exponential backoff for polling interval.

        Args:
            condition: Function to poll
            timeout: Maximum time to wait

        Returns:
            Result of condition when truthy, None on timeout
        """
        start_time = time.time()
        interval = self.initial_interval

        while True:
            result = condition()
            if result:
                return result

            elapsed = time.time() - start_time
            if elapsed >= timeout:
                return None

            # Sleep with exponential backoff
            remaining = timeout - elapsed
            sleep_time = min(interval, remaining, self.max_interval)
            time.sleep(sleep_time)

            # Increase interval for next iteration
            interval = min(interval * self.backoff_factor, self.max_interval)


# Convenience functions using default waiter
_default_waiter: Optional[Waiter] = None


def get_waiter(display: Optional[str] = None) -> Waiter:
    """Get or create the default waiter."""
    global _default_waiter
    if _default_waiter is None:
        _default_waiter = Waiter(display=display)
    return _default_waiter


def wait_for_element(
    name: Optional[str] = None,
    role: Optional[str] = None,
    timeout: float = 30.0,
    display: Optional[str] = None
) -> Element:
    """Wait for an element to appear (convenience function)."""
    return get_waiter(display).wait_for_element(
        name=name, role=role, timeout=timeout
    )


def wait_for_text(
    text: str,
    timeout: float = 30.0,
    display: Optional[str] = None
) -> Element:
    """Wait for text to appear (convenience function)."""
    return get_waiter(display).wait_for_text(text, timeout=timeout)


def wait_until_gone(
    name: Optional[str] = None,
    text: Optional[str] = None,
    timeout: float = 30.0,
    display: Optional[str] = None
) -> bool:
    """Wait for element/text to disappear (convenience function)."""
    return get_waiter(display).wait_until_gone(
        name=name, text=text, timeout=timeout
    )
