"""
AT-SPI accessibility tree integration.

Uses pyatspi to traverse the accessibility tree and find UI elements
by name, role, and state.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Generator, Callable

# AT-SPI imports - these require python3-pyatspi package
try:
    import gi
    gi.require_version('Atspi', '2.0')
    from gi.repository import Atspi
    ATSPI_AVAILABLE = True
except (ImportError, ValueError):
    ATSPI_AVAILABLE = False
    Atspi = None


@dataclass
class ATSPIElement:
    """Represents an element from the AT-SPI accessibility tree."""
    name: str
    role: str
    role_name: str
    description: str
    x: int
    y: int
    width: int
    height: int
    states: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    app_name: str = ""
    path: str = ""  # Hierarchical path for debugging

    @property
    def center(self) -> tuple[int, int]:
        """Get center coordinates of the element."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def is_visible(self) -> bool:
        """Check if element is visible."""
        return "visible" in self.states and "showing" in self.states

    @property
    def is_enabled(self) -> bool:
        """Check if element is enabled (not grayed out)."""
        return "enabled" in self.states or "sensitive" in self.states

    @property
    def is_focusable(self) -> bool:
        """Check if element can receive focus."""
        return "focusable" in self.states

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "role_name": self.role_name,
            "description": self.description,
            "bounds": {
                "x": self.x,
                "y": self.y,
                "width": self.width,
                "height": self.height
            },
            "center": {"x": self.center[0], "y": self.center[1]},
            "states": self.states,
            "actions": self.actions,
            "app_name": self.app_name,
            "visible": self.is_visible,
            "enabled": self.is_enabled
        }


def is_available() -> bool:
    """Check if AT-SPI is available on this system."""
    return ATSPI_AVAILABLE


def _get_element_states(accessible) -> list[str]:
    """Extract state names from an accessible object."""
    if not ATSPI_AVAILABLE:
        return []

    states = []
    try:
        state_set = accessible.get_state_set()
        # Check common states
        state_names = [
            ("visible", Atspi.StateType.VISIBLE),
            ("showing", Atspi.StateType.SHOWING),
            ("enabled", Atspi.StateType.ENABLED),
            ("sensitive", Atspi.StateType.SENSITIVE),
            ("focusable", Atspi.StateType.FOCUSABLE),
            ("focused", Atspi.StateType.FOCUSED),
            ("checked", Atspi.StateType.CHECKED),
            ("pressed", Atspi.StateType.PRESSED),
            ("selected", Atspi.StateType.SELECTED),
            ("editable", Atspi.StateType.EDITABLE),
            ("expandable", Atspi.StateType.EXPANDABLE),
            ("expanded", Atspi.StateType.EXPANDED),
        ]
        for name, state_type in state_names:
            if state_set.contains(state_type):
                states.append(name)
    except Exception:
        pass
    return states


def _get_element_actions(accessible) -> list[str]:
    """Extract available actions from an accessible object."""
    if not ATSPI_AVAILABLE:
        return []

    actions = []
    try:
        action_iface = accessible.get_action_iface()
        if action_iface:
            n_actions = action_iface.get_n_actions()
            for i in range(n_actions):
                action_name = action_iface.get_action_name(i)
                if action_name:
                    actions.append(action_name)
    except Exception:
        pass
    return actions


def _get_element_bounds(accessible) -> tuple[int, int, int, int]:
    """Get element bounds (x, y, width, height) in desktop coordinates."""
    if not ATSPI_AVAILABLE:
        return (0, 0, 0, 0)

    try:
        component = accessible.get_component_iface()
        if component:
            rect = component.get_extents(Atspi.CoordType.SCREEN)
            return (rect.x, rect.y, rect.width, rect.height)
    except Exception:
        pass
    return (0, 0, 0, 0)


def _accessible_to_element(
    accessible,
    app_name: str = "",
    path: str = ""
) -> Optional[ATSPIElement]:
    """Convert an Atspi accessible object to ATSPIElement."""
    if not ATSPI_AVAILABLE or accessible is None:
        return None

    try:
        name = accessible.get_name() or ""
        role = accessible.get_role()
        role_name = accessible.get_role_name() or ""
        description = accessible.get_description() or ""

        x, y, w, h = _get_element_bounds(accessible)
        states = _get_element_states(accessible)
        actions = _get_element_actions(accessible)

        return ATSPIElement(
            name=name,
            role=str(role),
            role_name=role_name,
            description=description,
            x=x,
            y=y,
            width=w,
            height=h,
            states=states,
            actions=actions,
            app_name=app_name,
            path=path
        )
    except Exception:
        return None


def get_desktop():
    """Get the root desktop accessible object."""
    if not ATSPI_AVAILABLE:
        return None
    try:
        return Atspi.get_desktop(0)
    except Exception:
        return None


def get_applications() -> list[str]:
    """Get list of application names with accessibility support."""
    if not ATSPI_AVAILABLE:
        return []

    apps = []
    try:
        desktop = get_desktop()
        if desktop:
            for i in range(desktop.get_child_count()):
                app = desktop.get_child_at_index(i)
                if app:
                    name = app.get_name()
                    if name:
                        apps.append(name)
    except Exception:
        pass
    return apps


def traverse_tree(
    root=None,
    max_depth: int = 15,
    filter_fn: Optional[Callable] = None,
    app_filter: Optional[str] = None
) -> Generator[ATSPIElement, None, None]:
    """
    Traverse the accessibility tree and yield elements.

    Args:
        root: Starting accessible (defaults to desktop)
        max_depth: Maximum depth to traverse
        filter_fn: Optional function to filter elements (receives ATSPIElement)
        app_filter: Optional app name to filter by

    Yields:
        ATSPIElement objects matching the criteria
    """
    if not ATSPI_AVAILABLE:
        return

    if root is None:
        root = get_desktop()
        if root is None:
            return

    def _traverse(accessible, depth: int, app_name: str, path: str):
        if depth > max_depth:
            return

        try:
            # Get application name at top level
            if depth == 1:
                app_name = accessible.get_name() or ""
                if app_filter and app_filter.lower() not in app_name.lower():
                    return

            # Convert to element
            elem = _accessible_to_element(accessible, app_name, path)
            if elem:
                # Apply filter if provided
                if filter_fn is None or filter_fn(elem):
                    yield elem

            # Traverse children
            child_count = accessible.get_child_count()
            for i in range(child_count):
                try:
                    child = accessible.get_child_at_index(i)
                    if child:
                        child_path = f"{path}/{i}"
                        yield from _traverse(child, depth + 1, app_name, child_path)
                except Exception:
                    continue

        except Exception:
            pass

    yield from _traverse(root, 0, "", "")


def find_elements(
    name: Optional[str] = None,
    role: Optional[str] = None,
    app: Optional[str] = None,
    visible_only: bool = True,
    clickable_only: bool = False,
    max_results: int = 50
) -> list[ATSPIElement]:
    """
    Find elements matching the given criteria.

    Args:
        name: Element name to match (partial, case-insensitive)
        role: Role name to match (e.g., "button", "text", "entry")
        app: Application name to filter by
        visible_only: Only return visible elements
        clickable_only: Only return elements with click action
        max_results: Maximum number of results to return

    Returns:
        List of matching ATSPIElement objects
    """
    def filter_fn(elem: ATSPIElement) -> bool:
        # Check visibility
        if visible_only and not elem.is_visible:
            return False

        # Check clickable
        if clickable_only and "click" not in elem.actions:
            return False

        # Check name match
        if name:
            name_lower = name.lower()
            if name_lower not in elem.name.lower():
                if name_lower not in elem.description.lower():
                    return False

        # Check role match
        if role:
            role_lower = role.lower()
            if role_lower not in elem.role_name.lower():
                return False

        return True

    results = []
    for elem in traverse_tree(app_filter=app, filter_fn=filter_fn):
        results.append(elem)
        if len(results) >= max_results:
            break

    return results


def find_element(
    name: Optional[str] = None,
    role: Optional[str] = None,
    app: Optional[str] = None,
    visible_only: bool = True
) -> Optional[ATSPIElement]:
    """
    Find a single element matching the criteria.

    Returns the first matching element or None.
    """
    results = find_elements(
        name=name,
        role=role,
        app=app,
        visible_only=visible_only,
        max_results=1
    )
    return results[0] if results else None


def list_interactive_elements(
    app: Optional[str] = None,
    visible_only: bool = True
) -> list[ATSPIElement]:
    """
    List all interactive elements (buttons, links, inputs, etc.)

    Args:
        app: Optional application name to filter by
        visible_only: Only return visible elements

    Returns:
        List of interactive ATSPIElement objects
    """
    interactive_roles = {
        "push button", "toggle button", "radio button",
        "check box", "combo box", "menu item", "list item",
        "link", "entry", "text", "slider", "spin button"
    }

    def filter_fn(elem: ATSPIElement) -> bool:
        if visible_only and not elem.is_visible:
            return False

        # Check if role is interactive
        role_lower = elem.role_name.lower()
        for interactive_role in interactive_roles:
            if interactive_role in role_lower:
                return True

        # Also check if it has actions
        if elem.actions:
            return True

        return False

    return list(traverse_tree(app_filter=app, filter_fn=filter_fn))


def do_action(element: ATSPIElement, action_name: str = "click") -> bool:
    """
    Perform an action on an element.

    Note: This is a placeholder. Actual implementation would need
    to keep a reference to the accessible object.

    For now, use xdotool click at element.center instead.
    """
    # AT-SPI actions require the original accessible reference
    # Since we're working with serialized elements, use xdotool instead
    return False


def setup_environment():
    """
    Set up environment variables for AT-SPI in headless sessions.

    Call this before launching applications that need accessibility.
    """
    # Required for GTK applications
    os.environ.setdefault("GTK_MODULES", "gail:atk-bridge")

    # Required for Qt applications
    os.environ.setdefault("QT_LINUX_ACCESSIBILITY_ALWAYS_ON", "1")

    # Accessibility bus should be running
    # In headless sessions, you may need to start it manually:
    # /usr/lib/at-spi2-core/at-spi-bus-launcher &
