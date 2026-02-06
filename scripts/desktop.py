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
from desktop_control import cache as element_cache
from desktop_control import annotate


def cmd_screenshot(args) -> dict:
    """Take a screenshot."""
    return screenshot_module.screenshot(
        output=args.output,
        display=args.display
    )


def cmd_click(args) -> dict:
    """Click at coordinates (pixel or percentage)."""
    if args.right and args.middle:
        return {"error": "Choose at most one mouse button: --right or --middle"}

    has_x_percent = args.x_percent is not None
    has_y_percent = args.y_percent is not None
    if has_x_percent != has_y_percent:
        return {"error": "Both --x-percent and --y-percent must be provided together"}

    button = "right" if args.right else ("middle" if args.middle else "left")

    # Check if percentage coordinates are provided
    if has_x_percent and has_y_percent:
        return xdotool.click_percent(
            args.x_percent, args.y_percent,
            button=button,
            double=args.double,
            display=args.display
        )

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
    if not args.name and not args.role:
        return {"error": "click-element requires at least one selector: --name or --role"}

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
        if not ocr.is_available():
            return {"error": "Pre-click verification requires OCR, but OCR is unavailable"}

        verify_text = (args.name or element.name or "").strip()
        if not verify_text:
            return {
                "error": "Pre-click verification requires text. Provide --name or disable --verify.",
                "element": element.to_dict()
            }

        # Take screenshot and verify text is at expected location
        img = screenshot_module.screenshot_to_pil(args.display)
        if img:
            matches = ocr.find_text(img, verify_text)
            if not matches:
                return {
                    "error": "Pre-click verification failed: text not found",
                    "element": element.to_dict()
                }
        else:
            return {"error": "Pre-click verification failed: screenshot capture failed"}

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

    if args.text and (args.name or args.role or args.app):
        return {
            "error": "Use either --text or element selectors (--name/--role/--app), not both"
        }

    try:
        if args.gone:
            if args.text:
                waiter.wait_until_gone(
                    text=args.text,
                    exact=args.exact,
                    timeout=args.timeout
                )
            else:
                if not args.name and not args.role:
                    return {
                        "error": "wait-for --gone requires --text or at least one of --name/--role"
                    }

                waiter.wait_until_gone(
                    name=args.name,
                    role=args.role,
                    app=args.app,
                    timeout=args.timeout
                )

            # Wait for element to disappear
            return {"gone": True, "name": args.name or args.text, "role": args.role, "app": args.app}
        elif args.text:
            element = waiter.wait_for_text(
                args.text,
                exact=args.exact,
                timeout=args.timeout
            )
        else:
            if not args.name and not args.role:
                return {
                    "error": "wait-for requires --text or at least one of --name/--role"
                }

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


def cmd_screenshot_annotated(args) -> dict:
    """Take annotated screenshot with numbered element markers."""
    from PIL import Image
    import os

    # Get screen size for cache
    screen_size = xdotool.get_screen_size(args.display)
    if screen_size == (0, 0):
        return {"error": "Failed to get screen dimensions"}

    # Take screenshot
    img = screenshot_module.screenshot_to_pil(args.display)
    if img is None:
        return {"error": "Failed to capture screenshot"}

    # Find interactive elements
    finder = ElementFinder(display=args.display)
    elements = finder.list_interactive(
        app=args.app,
        visible_only=not args.include_hidden
    )

    # Filter by role if specified
    if args.role:
        role_lower = args.role.lower()
        elements = [e for e in elements if role_lower in e.role_name.lower()]

    # Limit to max results
    elements = elements[:args.max_elements]

    if not elements:
        # Still save screenshot even if no elements
        output_base = args.output or f"/tmp/screen_{int(time.time())}"
        orig_path = f"{output_base}.png"
        img.save(orig_path)
        return {
            "screenshot_path": orig_path,
            "annotated_path": orig_path,
            "original_size": {"width": img.width, "height": img.height},
            "display_size": {"width": img.width, "height": img.height},
            "elements": [],
            "element_count": 0
        }

    # Annotate and downsample
    max_w = args.max_width or 1280
    max_h = args.max_height or 720
    _, annotated_img, scale = annotate.annotate_screenshot(
        img, elements, max_w, max_h
    )

    # Store elements in cache
    element_cache.store_elements(elements, screen_size)

    # Save images
    output_base = args.output or f"/tmp/screen_{int(time.time())}"
    orig_path = f"{output_base}.png"
    annotated_path = f"{output_base}_annotated.png"

    img.save(orig_path)
    annotated_img.save(annotated_path)

    # Build element list with IDs and percentage coordinates
    element_list = []
    for idx, elem in enumerate(elements, start=1):
        elem_dict = elem.to_dict()
        elem_dict["id"] = idx
        # Add percentage coordinates
        cx, cy = elem.center
        elem_dict["x_percent"] = round(cx / screen_size[0], 4) if screen_size[0] > 0 else 0
        elem_dict["y_percent"] = round(cy / screen_size[1], 4) if screen_size[1] > 0 else 0
        element_list.append(elem_dict)

    return {
        "screenshot_path": orig_path,
        "annotated_path": annotated_path,
        "original_size": {"width": img.width, "height": img.height},
        "display_size": {"width": annotated_img.width, "height": annotated_img.height},
        "scale": round(scale, 4),
        "elements": element_list,
        "element_count": len(elements),
        "cache_ttl": element_cache.ElementCache.TTL
    }


def cmd_click_id(args) -> dict:
    """Click cached element by ID."""
    # Check cache validity
    if not element_cache.is_cache_valid():
        return {
            "error": "Element cache expired or empty. Run screenshot-annotated first.",
            "cache_valid": False
        }

    # Ensure screen size is unchanged since cache creation.
    cache = element_cache.get_cache()
    expected_size = cache.screen_size
    current_size = xdotool.get_screen_size(args.display)
    if current_size == (0, 0):
        return {"error": "Failed to get current screen dimensions", "cache_valid": False}

    if not cache.check_screen_size(current_size):
        return {
            "error": "Screen size changed since cache creation. Run screenshot-annotated again.",
            "cache_valid": False,
            "expected_screen_size": {"width": expected_size[0], "height": expected_size[1]},
            "current_screen_size": {"width": current_size[0], "height": current_size[1]},
        }

    # Get element from cache
    element = element_cache.get_element(args.element_id)
    if element is None:
        cached = element_cache.get_all_elements()
        return {
            "error": f"Element ID {args.element_id} not found in cache",
            "available_ids": list(cached.keys()),
            "cache_valid": True
        }

    # Get center coordinates
    x, y = element.center

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
            "element_id": args.element_id,
            "element": element.to_dict(),
            "x": x,
            "y": y,
            "button": button,
            "double": args.double
        }
    }


def cmd_click_percent(args) -> dict:
    """Click at percentage-based coordinates."""
    if args.right and args.middle:
        return {"error": "Choose at most one mouse button: --right or --middle"}

    return xdotool.click_percent(
        args.x_percent,
        args.y_percent,
        button="right" if args.right else ("middle" if args.middle else "left"),
        double=args.double,
        display=args.display
    )


def cmd_screen_size(args) -> dict:
    """Get screen dimensions."""
    width, height = xdotool.get_screen_size(args.display)
    if width == 0 or height == 0:
        return {"error": "Failed to get screen dimensions"}
    return {"width": width, "height": height}


def cmd_cache_status(args) -> dict:
    """Get element cache status."""
    cache = element_cache.get_cache()
    elements = cache.get_all()

    element_list = []
    for eid, elem in elements.items():
        elem_dict = elem.to_dict()
        elem_dict["id"] = eid
        element_list.append(elem_dict)

    return {
        "valid": cache.is_valid(),
        "count": cache.count,
        "age_seconds": round(cache.age, 2) if cache.is_valid() else None,
        "ttl_seconds": element_cache.ElementCache.TTL,
        "screen_size": {"width": cache.screen_size[0], "height": cache.screen_size[1]},
        "elements": element_list if args.show_elements else None
    }


def cmd_drag(args) -> dict:
    """Drag from one position to another."""
    return xdotool.drag(
        args.start_x,
        args.start_y,
        args.end_x,
        args.end_y,
        button="right" if args.right else "left",
        display=args.display
    )


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
    p_click.add_argument("x", type=int, nargs="?", default=0, help="X coordinate (pixels)")
    p_click.add_argument("y", type=int, nargs="?", default=0, help="Y coordinate (pixels)")
    p_click.add_argument("--x-percent", type=float, help="X as fraction 0.0-1.0 (overrides x)")
    p_click.add_argument("--y-percent", type=float, help="Y as fraction 0.0-1.0 (overrides y)")
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

    # ===== New annotated screenshot commands =====

    # Screenshot annotated
    p_screenshot_annotated = subparsers.add_parser(
        "screenshot-annotated",
        help="Take annotated screenshot with numbered element markers"
    )
    p_screenshot_annotated.add_argument("--output", "-o", help="Output file path (without extension)")
    p_screenshot_annotated.add_argument("--app", "-a", help="Application name filter")
    p_screenshot_annotated.add_argument("--role", "-r", help="Filter by role")
    p_screenshot_annotated.add_argument("--include-hidden", action="store_true", help="Include hidden elements")
    p_screenshot_annotated.add_argument("--max-elements", type=int, default=50, help="Max elements to annotate")
    p_screenshot_annotated.add_argument("--max-width", type=int, default=1280, help="Max output width")
    p_screenshot_annotated.add_argument("--max-height", type=int, default=720, help="Max output height")

    # Click by ID
    p_click_id = subparsers.add_parser(
        "click-id",
        help="Click cached element by ID"
    )
    p_click_id.add_argument("element_id", type=int, help="Element ID from screenshot-annotated")
    p_click_id.add_argument("--right", action="store_true", help="Right click")
    p_click_id.add_argument("--double", action="store_true", help="Double click")

    # Click by percentage
    p_click_percent = subparsers.add_parser(
        "click-percent",
        help="Click at percentage-based coordinates"
    )
    p_click_percent.add_argument("x_percent", type=float, help="X as fraction 0.0-1.0")
    p_click_percent.add_argument("y_percent", type=float, help="Y as fraction 0.0-1.0")
    p_click_percent.add_argument("--right", action="store_true", help="Right click")
    p_click_percent.add_argument("--middle", action="store_true", help="Middle click")
    p_click_percent.add_argument("--double", action="store_true", help="Double click")

    # Screen size
    subparsers.add_parser("screen-size", help="Get screen dimensions")

    # Cache status
    p_cache = subparsers.add_parser("cache-status", help="Get element cache status")
    p_cache.add_argument("--show-elements", action="store_true", help="Include element details")

    # Drag
    p_drag = subparsers.add_parser("drag", help="Drag from one position to another")
    p_drag.add_argument("start_x", type=int, help="Start X coordinate")
    p_drag.add_argument("start_y", type=int, help="Start Y coordinate")
    p_drag.add_argument("end_x", type=int, help="End X coordinate")
    p_drag.add_argument("end_y", type=int, help="End Y coordinate")
    p_drag.add_argument("--right", action="store_true", help="Right drag")

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
        # New annotated screenshot commands
        "screenshot-annotated": cmd_screenshot_annotated,
        "click-id": cmd_click_id,
        "click-percent": cmd_click_percent,
        "screen-size": cmd_screen_size,
        "cache-status": cmd_cache_status,
        "drag": cmd_drag,
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
