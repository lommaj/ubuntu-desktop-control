#!/usr/bin/env python3
"""
Desktop control script with semantic element targeting.

Provides AT-SPI accessibility tree and OCR-based element finding
with xdotool for mouse/keyboard control.

For GUI automation (wallet popups, browser extensions, etc.)
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from desktop_control.core import DEFAULT_DISPLAY
from desktop_control import xdotool
from desktop_control import screenshot as screenshot_module
from desktop_control import atspi
from desktop_control import ocr
from desktop_control.finder import ElementFinder
from desktop_control.waiter import Waiter, WaitTimeout


def cmd_screenshot(args) -> dict:
    """Take a screenshot."""
    return screenshot_module.screenshot(
        output=args.output,
        display=args.display
    )


def cmd_click(args) -> dict:
    """Click at coordinates."""
    button = "right" if args.right else ("middle" if args.middle else "left")
    return xdotool.click(
        args.x, args.y,
        button=button,
        double=args.double,
        display=args.display
    )


def cmd_type(args) -> dict:
    """Type text."""
    return xdotool.type_text(
        args.text,
        delay=args.type_delay,
        display=args.display
    )


def cmd_key(args) -> dict:
    """Press key combination."""
    return xdotool.key(args.keys, display=args.display)


def cmd_move(args) -> dict:
    """Move mouse."""
    return xdotool.move(args.x, args.y, display=args.display)


def cmd_active(args) -> dict:
    """Get active window info."""
    return xdotool.get_active_window(display=args.display)


def cmd_find_window(args) -> dict:
    """Find windows by name."""
    return xdotool.find_window(args.name, display=args.display)


def cmd_focus(args) -> dict:
    """Focus window by name."""
    return xdotool.focus_window(args.name, display=args.display)


def cmd_position(args) -> dict:
    """Get mouse position."""
    return xdotool.get_mouse_position(display=args.display)


def cmd_windows(args) -> dict:
    """List all windows."""
    return xdotool.list_windows(display=args.display)


def cmd_find_element(args) -> dict:
    """Find UI element via AT-SPI with OCR fallback."""
    finder = ElementFinder(display=args.display)

    if args.all:
        elements = finder.find_all(
            name=args.name,
            role=args.role,
            app=args.app,
            clickable_only=args.clickable,
            max_results=args.max_results
        )
        return {
            "elements": [e.to_dict() for e in elements],
            "count": len(elements)
        }
    else:
        element = finder.find(
            name=args.name,
            role=args.role,
            app=args.app
        )
        if element:
            return {"element": element.to_dict()}
        return {"error": f"Element not found", "name": args.name, "role": args.role}


def cmd_find_text(args) -> dict:
    """Find text on screen via OCR."""
    finder = ElementFinder(display=args.display, use_atspi=False)

    if args.all:
        elements = finder.find_all_text(
            args.text,
            exact=args.exact,
            case_sensitive=args.case_sensitive,
            max_results=args.max_results
        )
        return {
            "matches": [e.to_dict() for e in elements],
            "count": len(elements)
        }
    else:
        element = finder.find_text(
            args.text,
            exact=args.exact,
            case_sensitive=args.case_sensitive
        )
        if element:
            return {"match": element.to_dict()}
        return {"error": f"Text not found: '{args.text}'"}


def cmd_click_element(args) -> dict:
    """Click element by name/role."""
    finder = ElementFinder(display=args.display)

    # Find the element
    element = finder.find(
        name=args.name,
        role=args.role,
        app=args.app
    )

    if not element:
        return {"error": f"Element not found", "name": args.name, "role": args.role}

    # Get center coordinates
    x, y = element.center

    # Optional pre-click verification
    if args.verify:
        # Take screenshot and verify text is at expected location
        img = screenshot_module.screenshot_to_pil(args.display)
        if img and ocr.is_available():
            matches = ocr.find_text(img, args.name or "")
            if not matches:
                return {
                    "error": "Pre-click verification failed: text not found",
                    "element": element.to_dict()
                }

    # Click at element center
    button = "right" if args.right else "left"
    result = xdotool.click(
        x, y,
        button=button,
        double=args.double,
        display=args.display
    )

    if "error" in result:
        return result

    return {
        "clicked": {
            "element": element.to_dict(),
            "x": x,
            "y": y,
            "button": button,
            "double": args.double
        }
    }


def cmd_wait_for(args) -> dict:
    """Wait for element or text to appear."""
    waiter = Waiter(display=args.display)

    try:
        if args.text:
            element = waiter.wait_for_text(
                args.text,
                exact=args.exact,
                timeout=args.timeout
            )
        elif args.gone:
            # Wait for element to disappear
            waiter.wait_until_gone(
                name=args.name,
                text=args.text,
                timeout=args.timeout
            )
            return {"gone": True, "name": args.name or args.text}
        else:
            element = waiter.wait_for_element(
                name=args.name,
                role=args.role,
                app=args.app,
                timeout=args.timeout
            )

        return {"found": element.to_dict()}

    except WaitTimeout as e:
        return {"error": str(e), "timeout": True}


def cmd_list_elements(args) -> dict:
    """List interactive elements."""
    finder = ElementFinder(display=args.display)

    elements = finder.list_interactive(
        app=args.app,
        visible_only=not args.include_hidden
    )

    # Filter by role if specified
    if args.role:
        role_lower = args.role.lower()
        elements = [e for e in elements if role_lower in e.role_name.lower()]

    return {
        "elements": [e.to_dict() for e in elements[:args.max_results]],
        "count": len(elements)
    }


def cmd_status(args) -> dict:
    """Check status of AT-SPI and OCR."""
    return {
        "atspi": {
            "available": atspi.is_available(),
            "applications": atspi.get_applications() if atspi.is_available() else []
        },
        "ocr": {
            "available": ocr.is_available()
        },
        "display": args.display
    }


def main():
    parser = argparse.ArgumentParser(
        description="Desktop control with semantic element targeting"
    )
    parser.add_argument(
        "--display",
        default=DEFAULT_DISPLAY,
        help="X display to use (default: :10.0)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0,
        help="Delay before action (seconds)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # ===== Original commands =====

    # Screenshot
    p_screenshot = subparsers.add_parser("screenshot", help="Take a screenshot")
    p_screenshot.add_argument("--output", "-o", help="Output file path")

    # Click
    p_click = subparsers.add_parser("click", help="Click at coordinates")
    p_click.add_argument("x", type=int, help="X coordinate")
    p_click.add_argument("y", type=int, help="Y coordinate")
    p_click.add_argument("--right", action="store_true", help="Right click")
    p_click.add_argument("--middle", action="store_true", help="Middle click")
    p_click.add_argument("--double", action="store_true", help="Double click")

    # Type
    p_type = subparsers.add_parser("type", help="Type text")
    p_type.add_argument("text", help="Text to type")
    p_type.add_argument("--type-delay", type=int, default=12, help="Keystroke delay (ms)")

    # Key
    p_key = subparsers.add_parser("key", help="Press key combination")
    p_key.add_argument("keys", help="Key(s) to press (e.g., 'Return', 'ctrl+a')")

    # Move
    p_move = subparsers.add_parser("move", help="Move mouse")
    p_move.add_argument("x", type=int, help="X coordinate")
    p_move.add_argument("y", type=int, help="Y coordinate")

    # Active window
    subparsers.add_parser("active", help="Get active window info")

    # Find window (renamed from 'find' to avoid conflict)
    p_find_window = subparsers.add_parser("find-window", help="Find windows by name")
    p_find_window.add_argument("name", help="Window name to search")

    # Focus window
    p_focus = subparsers.add_parser("focus", help="Focus window by name")
    p_focus.add_argument("name", help="Window name to focus")

    # Mouse position
    subparsers.add_parser("position", help="Get mouse position")

    # List windows
    subparsers.add_parser("windows", help="List all windows")

    # ===== New semantic commands =====

    # Find element (AT-SPI + OCR)
    p_find_elem = subparsers.add_parser(
        "find-element",
        help="Find UI element via AT-SPI with OCR fallback"
    )
    p_find_elem.add_argument("--name", "-n", help="Element name/text to find")
    p_find_elem.add_argument("--role", "-r", help="Element role (button, entry, etc.)")
    p_find_elem.add_argument("--app", "-a", help="Application name filter")
    p_find_elem.add_argument("--all", action="store_true", help="Find all matches")
    p_find_elem.add_argument("--clickable", action="store_true", help="Only clickable elements")
    p_find_elem.add_argument("--max-results", type=int, default=50, help="Max results")

    # Find text (OCR only)
    p_find_text = subparsers.add_parser(
        "find-text",
        help="Find text on screen via OCR"
    )
    p_find_text.add_argument("text", help="Text to find")
    p_find_text.add_argument("--exact", action="store_true", help="Exact match")
    p_find_text.add_argument("--case-sensitive", action="store_true", help="Case sensitive")
    p_find_text.add_argument("--all", action="store_true", help="Find all matches")
    p_find_text.add_argument("--max-results", type=int, default=50, help="Max results")

    # Click element
    p_click_elem = subparsers.add_parser(
        "click-element",
        help="Click element by name/role"
    )
    p_click_elem.add_argument("--name", "-n", help="Element name/text")
    p_click_elem.add_argument("--role", "-r", help="Element role")
    p_click_elem.add_argument("--app", "-a", help="Application name filter")
    p_click_elem.add_argument("--right", action="store_true", help="Right click")
    p_click_elem.add_argument("--double", action="store_true", help="Double click")
    p_click_elem.add_argument("--verify", action="store_true", help="Verify before click")

    # Wait for
    p_wait = subparsers.add_parser(
        "wait-for",
        help="Wait for element or text to appear"
    )
    p_wait.add_argument("--name", "-n", help="Element name (AT-SPI + OCR)")
    p_wait.add_argument("--role", "-r", help="Element role (AT-SPI only)")
    p_wait.add_argument("--app", "-a", help="Application name filter")
    p_wait.add_argument("--text", "-t", help="Text to find (OCR only)")
    p_wait.add_argument("--exact", action="store_true", help="Exact text match")
    p_wait.add_argument("--gone", action="store_true", help="Wait until element/text disappears")
    p_wait.add_argument("--timeout", type=float, default=30.0, help="Timeout in seconds")

    # List elements
    p_list = subparsers.add_parser(
        "list-elements",
        help="List interactive elements"
    )
    p_list.add_argument("--app", "-a", help="Application name filter")
    p_list.add_argument("--role", "-r", help="Filter by role")
    p_list.add_argument("--include-hidden", action="store_true", help="Include hidden elements")
    p_list.add_argument("--max-results", type=int, default=100, help="Max results")

    # Status check
    subparsers.add_parser("status", help="Check AT-SPI and OCR status")

    # Parse arguments
    args = parser.parse_args()

    # Apply delay if specified
    if args.delay > 0:
        time.sleep(args.delay)

    # Command dispatch
    commands = {
        "screenshot": cmd_screenshot,
        "click": cmd_click,
        "type": cmd_type,
        "key": cmd_key,
        "move": cmd_move,
        "active": cmd_active,
        "find-window": cmd_find_window,
        "focus": cmd_focus,
        "position": cmd_position,
        "windows": cmd_windows,
        "find-element": cmd_find_element,
        "find-text": cmd_find_text,
        "click-element": cmd_click_element,
        "wait-for": cmd_wait_for,
        "list-elements": cmd_list_elements,
        "status": cmd_status,
    }

    handler = commands.get(args.command)
    if handler:
        result = handler(args)
    else:
        result = {"error": f"Unknown command: {args.command}"}

    print(json.dumps(result, indent=2))
    sys.exit(0 if "error" not in result else 1)


if __name__ == "__main__":
    main()
