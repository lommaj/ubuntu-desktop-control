"""
Mouse and keyboard control via xdotool.
"""

from typing import Optional
from .core import run_cmd, get_display


def click(
    x: int,
    y: int,
    button: str = "left",
    double: bool = False,
    display: Optional[str] = None
) -> dict:
    """
    Click at screen coordinates.

    Args:
        x: X coordinate (pixels from left edge)
        y: Y coordinate (pixels from top edge)
        button: "left", "middle", or "right"
        double: Whether to double-click
        display: X display to use

    Returns:
        Dict with click info or error
    """
    disp = get_display(display)

    # Move to position first
    result = run_cmd(["xdotool", "mousemove", "--sync", str(x), str(y)], disp)
    if not result.success:
        return {"error": f"Mouse move failed: {result.stderr}"}

    # Map button name to xdotool button number
    button_map = {"left": "1", "middle": "2", "right": "3"}
    btn = button_map.get(button, "1")

    if double:
        cmd = ["xdotool", "click", "--repeat", "2", "--delay", "100", btn]
    else:
        cmd = ["xdotool", "click", btn]

    result = run_cmd(cmd, disp)
    if not result.success:
        return {"error": f"Click failed: {result.stderr}"}

    return {"clicked": {"x": x, "y": y, "button": button, "double": double}}


def type_text(
    text: str,
    delay: int = 12,
    display: Optional[str] = None
) -> dict:
    """
    Type text using keyboard simulation.

    Args:
        text: Text to type
        delay: Milliseconds between keystrokes
        display: X display to use

    Returns:
        Dict with typed text or error
    """
    disp = get_display(display)
    result = run_cmd(
        ["xdotool", "type", "--delay", str(delay), "--", text],
        disp
    )
    if not result.success:
        return {"error": f"Type failed: {result.stderr}"}
    return {"typed": text}


def key(keys: str, display: Optional[str] = None) -> dict:
    """
    Press a key or key combination.

    Args:
        keys: Key(s) to press (e.g., "Return", "ctrl+a")
        display: X display to use

    Returns:
        Dict with pressed keys or error
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "key", "--", keys], disp)
    if not result.success:
        return {"error": f"Key press failed: {result.stderr}"}
    return {"pressed": keys}


def move(x: int, y: int, display: Optional[str] = None) -> dict:
    """
    Move mouse to coordinates without clicking.

    Args:
        x: X coordinate
        y: Y coordinate
        display: X display to use

    Returns:
        Dict with new position or error
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "mousemove", "--sync", str(x), str(y)], disp)
    if not result.success:
        return {"error": f"Mouse move failed: {result.stderr}"}
    return {"moved": {"x": x, "y": y}}


def get_mouse_position(display: Optional[str] = None) -> dict:
    """
    Get current mouse cursor position.

    Returns:
        Dict with position {x, y} or error
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "getmouselocation", "--shell"], disp)
    if not result.success:
        return {"error": f"Get position failed: {result.stderr}"}

    pos = {}
    for line in result.stdout.split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            pos[k.lower()] = int(v) if v.isdigit() else v

    return {"position": {"x": pos.get("x", 0), "y": pos.get("y", 0)}}


def get_active_window(display: Optional[str] = None) -> dict:
    """
    Get active window information.

    Returns:
        Dict with window_id, name, and geometry
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "getactivewindow"], disp)
    if not result.success:
        return {"error": f"Get active window failed: {result.stderr}"}

    window_id = result.stdout

    # Get window name
    name_result = run_cmd(["xdotool", "getwindowname", window_id], disp)
    name = name_result.stdout if name_result.success else ""

    # Get window geometry
    geom_result = run_cmd(
        ["xdotool", "getwindowgeometry", "--shell", window_id],
        disp
    )

    geometry = {}
    if geom_result.success:
        for line in geom_result.stdout.split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                geometry[k.lower()] = int(v) if v.isdigit() else v

    return {
        "window_id": window_id,
        "name": name,
        "geometry": geometry
    }


def find_window(name: str, display: Optional[str] = None) -> dict:
    """
    Find windows by name (partial match).

    Args:
        name: Window name to search for

    Returns:
        Dict with list of matching windows
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "search", "--name", name], disp)
    if not result.success or not result.stdout:
        return {"error": f"No windows found matching '{name}'", "windows": []}

    windows = []
    for wid in result.stdout.split("\n"):
        if wid:
            name_result = run_cmd(["xdotool", "getwindowname", wid], disp)
            windows.append({
                "window_id": wid,
                "name": name_result.stdout if name_result.success else ""
            })

    return {"windows": windows}


def focus_window(name: str, display: Optional[str] = None) -> dict:
    """
    Focus a window by name.

    Args:
        name: Window name to focus (partial match, uses first result)

    Returns:
        Dict with focused window_id or error
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "search", "--name", name], disp)
    if not result.success or not result.stdout:
        return {"error": f"No window found matching '{name}'"}

    # Take first match
    wid = result.stdout.split("\n")[0]
    focus_result = run_cmd(["xdotool", "windowactivate", "--sync", wid], disp)
    if not focus_result.success:
        return {"error": f"Focus failed: {focus_result.stderr}"}

    return {"focused": wid}


def list_windows(display: Optional[str] = None) -> dict:
    """
    List all windows on the desktop.

    Returns:
        Dict with list of all windows
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "search", "--name", ""], disp)
    if not result.success:
        return {"error": f"List windows failed: {result.stderr}"}

    windows = []
    for wid in result.stdout.split("\n"):
        if wid:
            name_result = run_cmd(["xdotool", "getwindowname", wid], disp)
            if name_result.stdout:  # Skip windows without names
                windows.append({
                    "window_id": wid,
                    "name": name_result.stdout
                })

    return {"windows": windows}


def get_screen_size(display: Optional[str] = None) -> tuple[int, int]:
    """
    Get the screen dimensions.

    Args:
        display: X display to use

    Returns:
        Tuple of (width, height) in pixels, or (0, 0) on error
    """
    disp = get_display(display)
    result = run_cmd(["xdotool", "getdisplaygeometry"], disp)
    if not result.success:
        return (0, 0)

    try:
        parts = result.stdout.split()
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return (0, 0)


def click_percent(
    x_percent: float,
    y_percent: float,
    button: str = "left",
    double: bool = False,
    display: Optional[str] = None
) -> dict:
    """
    Click at percentage-based screen coordinates.

    Resolution-agnostic clicking using normalized coordinates.

    Args:
        x_percent: X position as fraction (0.0 = left, 1.0 = right)
        y_percent: Y position as fraction (0.0 = top, 1.0 = bottom)
        button: "left", "middle", or "right"
        double: Whether to double-click
        display: X display to use

    Returns:
        Dict with click info including actual pixel coordinates, or error
    """
    # Validate percentage values
    if not (0.0 <= x_percent <= 1.0 and 0.0 <= y_percent <= 1.0):
        return {
            "error": "Percentage values must be between 0.0 and 1.0",
            "x_percent": x_percent,
            "y_percent": y_percent
        }

    # Get screen dimensions
    width, height = get_screen_size(display)
    if width == 0 or height == 0:
        return {"error": "Failed to get screen dimensions"}

    # Convert to pixel coordinates
    x = int(x_percent * width)
    y = int(y_percent * height)

    # Ensure within bounds
    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))

    # Perform the click
    result = click(x, y, button=button, double=double, display=display)

    if "error" in result:
        return result

    # Return with additional percentage info
    return {
        "clicked": {
            "x": x,
            "y": y,
            "x_percent": x_percent,
            "y_percent": y_percent,
            "screen_size": {"width": width, "height": height},
            "button": button,
            "double": double
        }
    }


def drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: float = 0.5,
    display: Optional[str] = None
) -> dict:
    """
    Drag from one position to another.

    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        button: "left", "middle", or "right"
        duration: Duration of drag in seconds (not directly supported, simulated)
        display: X display to use

    Returns:
        Dict with drag info or error
    """
    disp = get_display(display)

    # Map button name to xdotool button number
    button_map = {"left": "1", "middle": "2", "right": "3"}
    btn = button_map.get(button, "1")

    # Move to start position
    result = run_cmd(["xdotool", "mousemove", "--sync", str(start_x), str(start_y)], disp)
    if not result.success:
        return {"error": f"Move to start failed: {result.stderr}"}

    # Press mouse button
    result = run_cmd(["xdotool", "mousedown", btn], disp)
    if not result.success:
        return {"error": f"Mouse down failed: {result.stderr}"}

    # Move to end position
    result = run_cmd(["xdotool", "mousemove", "--sync", str(end_x), str(end_y)], disp)
    if not result.success:
        # Try to release button even if move failed
        run_cmd(["xdotool", "mouseup", btn], disp)
        return {"error": f"Move to end failed: {result.stderr}"}

    # Release mouse button
    result = run_cmd(["xdotool", "mouseup", btn], disp)
    if not result.success:
        return {"error": f"Mouse up failed: {result.stderr}"}

    return {
        "dragged": {
            "start": {"x": start_x, "y": start_y},
            "end": {"x": end_x, "y": end_y},
            "button": button
        }
    }
