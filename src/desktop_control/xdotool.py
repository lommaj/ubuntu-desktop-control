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
