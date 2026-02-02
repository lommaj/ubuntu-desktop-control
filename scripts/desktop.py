#!/usr/bin/env python3
"""
Desktop control script using xdotool and scrot.
For GUI automation (wallet popups, browser extensions, etc.)
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_DISPLAY = ":10.0"


def run_cmd(cmd: list[str], display: str = None) -> tuple[int, str, str]:
    """Run a command with optional DISPLAY override."""
    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def screenshot(output: str = None, display: str = DEFAULT_DISPLAY) -> dict:
    """Take a screenshot and return base64 or save to file."""
    temp_path = output or f"/tmp/screenshot_{int(time.time())}.png"
    
    code, stdout, stderr = run_cmd(["scrot", "-o", temp_path], display)
    if code != 0:
        return {"error": f"Screenshot failed: {stderr}"}
    
    path = Path(temp_path)
    if not path.exists():
        return {"error": "Screenshot file not created"}
    
    result = {
        "path": str(path),
        "size": path.stat().st_size,
    }
    
    if not output:
        # Return base64 if no output path specified
        with open(path, "rb") as f:
            result["base64"] = base64.b64encode(f.read()).decode()
        # Clean up temp file
        path.unlink()
        del result["path"]
    
    return result


def click(x: int, y: int, button: str = "left", double: bool = False, display: str = DEFAULT_DISPLAY) -> dict:
    """Click at coordinates."""
    # Move to position first
    code, _, stderr = run_cmd(["xdotool", "mousemove", "--sync", str(x), str(y)], display)
    if code != 0:
        return {"error": f"Mouse move failed: {stderr}"}
    
    # Determine click command
    button_map = {"left": "1", "middle": "2", "right": "3"}
    btn = button_map.get(button, "1")
    
    if double:
        cmd = ["xdotool", "click", "--repeat", "2", "--delay", "100", btn]
    else:
        cmd = ["xdotool", "click", btn]
    
    code, _, stderr = run_cmd(cmd, display)
    if code != 0:
        return {"error": f"Click failed: {stderr}"}
    
    return {"clicked": {"x": x, "y": y, "button": button, "double": double}}


def type_text(text: str, delay: int = 12, display: str = DEFAULT_DISPLAY) -> dict:
    """Type text with optional delay between keystrokes."""
    code, _, stderr = run_cmd(["xdotool", "type", "--delay", str(delay), "--", text], display)
    if code != 0:
        return {"error": f"Type failed: {stderr}"}
    return {"typed": text}


def key(keys: str, display: str = DEFAULT_DISPLAY) -> dict:
    """Press key combination (e.g., 'ctrl+a', 'Return', 'Tab')."""
    code, _, stderr = run_cmd(["xdotool", "key", "--", keys], display)
    if code != 0:
        return {"error": f"Key press failed: {stderr}"}
    return {"pressed": keys}


def move(x: int, y: int, display: str = DEFAULT_DISPLAY) -> dict:
    """Move mouse to coordinates."""
    code, _, stderr = run_cmd(["xdotool", "mousemove", "--sync", str(x), str(y)], display)
    if code != 0:
        return {"error": f"Mouse move failed: {stderr}"}
    return {"moved": {"x": x, "y": y}}


def get_active_window(display: str = DEFAULT_DISPLAY) -> dict:
    """Get active window info."""
    code, window_id, stderr = run_cmd(["xdotool", "getactivewindow"], display)
    if code != 0:
        return {"error": f"Get active window failed: {stderr}"}
    
    # Get window name
    code, name, _ = run_cmd(["xdotool", "getwindowname", window_id], display)
    
    # Get window geometry
    code, geom, _ = run_cmd(["xdotool", "getwindowgeometry", "--shell", window_id], display)
    
    geometry = {}
    for line in geom.split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            geometry[k.lower()] = int(v) if v.isdigit() else v
    
    return {
        "window_id": window_id,
        "name": name,
        "geometry": geometry
    }


def find_window(name: str, display: str = DEFAULT_DISPLAY) -> dict:
    """Find windows by name (partial match)."""
    code, window_ids, stderr = run_cmd(["xdotool", "search", "--name", name], display)
    if code != 0 or not window_ids:
        return {"error": f"No windows found matching '{name}'", "windows": []}
    
    windows = []
    for wid in window_ids.split("\n"):
        if wid:
            code, wname, _ = run_cmd(["xdotool", "getwindowname", wid], display)
            windows.append({"window_id": wid, "name": wname})
    
    return {"windows": windows}


def focus_window(name: str, display: str = DEFAULT_DISPLAY) -> dict:
    """Focus a window by name."""
    code, window_id, stderr = run_cmd(["xdotool", "search", "--name", name], display)
    if code != 0 or not window_id:
        return {"error": f"No window found matching '{name}'"}
    
    # Take first match
    wid = window_id.split("\n")[0]
    code, _, stderr = run_cmd(["xdotool", "windowactivate", "--sync", wid], display)
    if code != 0:
        return {"error": f"Focus failed: {stderr}"}
    
    return {"focused": wid}


def get_mouse_position(display: str = DEFAULT_DISPLAY) -> dict:
    """Get current mouse position."""
    code, output, stderr = run_cmd(["xdotool", "getmouselocation", "--shell"], display)
    if code != 0:
        return {"error": f"Get position failed: {stderr}"}
    
    pos = {}
    for line in output.split("\n"):
        if "=" in line:
            k, v = line.split("=", 1)
            pos[k.lower()] = int(v) if v.isdigit() else v
    
    return {"position": {"x": pos.get("x", 0), "y": pos.get("y", 0)}}


def list_windows(display: str = DEFAULT_DISPLAY) -> dict:
    """List all windows."""
    code, window_ids, stderr = run_cmd(["xdotool", "search", "--name", ""], display)
    if code != 0:
        return {"error": f"List windows failed: {stderr}"}
    
    windows = []
    for wid in window_ids.split("\n"):
        if wid:
            code, name, _ = run_cmd(["xdotool", "getwindowname", wid], display)
            if name:  # Skip windows without names
                windows.append({"window_id": wid, "name": name})
    
    return {"windows": windows}


def main():
    parser = argparse.ArgumentParser(description="Desktop control via xdotool")
    parser.add_argument("--display", default=DEFAULT_DISPLAY, help="X display to use")
    parser.add_argument("--delay", type=float, default=0, help="Delay before action (seconds)")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Screenshot
    p_screenshot = subparsers.add_parser("screenshot", help="Take a screenshot")
    p_screenshot.add_argument("--output", "-o", help="Output file path (returns base64 if not set)")
    
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
    p_type.add_argument("--type-delay", type=int, default=12, help="Delay between keystrokes (ms)")
    
    # Key
    p_key = subparsers.add_parser("key", help="Press key combination")
    p_key.add_argument("keys", help="Key(s) to press (e.g., 'Return', 'ctrl+a')")
    
    # Move
    p_move = subparsers.add_parser("move", help="Move mouse")
    p_move.add_argument("x", type=int, help="X coordinate")
    p_move.add_argument("y", type=int, help="Y coordinate")
    
    # Active window
    subparsers.add_parser("active", help="Get active window info")
    
    # Find window
    p_find = subparsers.add_parser("find", help="Find windows by name")
    p_find.add_argument("name", help="Window name to search for")
    
    # Focus window
    p_focus = subparsers.add_parser("focus", help="Focus window by name")
    p_focus.add_argument("name", help="Window name to focus")
    
    # Mouse position
    subparsers.add_parser("position", help="Get mouse position")
    
    # List windows
    subparsers.add_parser("windows", help="List all windows")
    
    args = parser.parse_args()
    
    # Apply delay if specified
    if args.delay > 0:
        time.sleep(args.delay)
    
    # Execute command
    if args.command == "screenshot":
        result = screenshot(args.output, args.display)
    elif args.command == "click":
        button = "right" if args.right else ("middle" if args.middle else "left")
        result = click(args.x, args.y, button, args.double, args.display)
    elif args.command == "type":
        result = type_text(args.text, args.type_delay, args.display)
    elif args.command == "key":
        result = key(args.keys, args.display)
    elif args.command == "move":
        result = move(args.x, args.y, args.display)
    elif args.command == "active":
        result = get_active_window(args.display)
    elif args.command == "find":
        result = find_window(args.name, args.display)
    elif args.command == "focus":
        result = focus_window(args.name, args.display)
    elif args.command == "position":
        result = get_mouse_position(args.display)
    elif args.command == "windows":
        result = list_windows(args.display)
    else:
        result = {"error": f"Unknown command: {args.command}"}
    
    print(json.dumps(result, indent=2))
    sys.exit(0 if "error" not in result else 1)


if __name__ == "__main__":
    main()
