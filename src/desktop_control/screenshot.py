"""
Screenshot capture functionality.
"""

import base64
import time
from pathlib import Path
from typing import Optional

from .core import run_cmd, get_display


def screenshot(
    output: Optional[str] = None,
    display: Optional[str] = None,
    region: Optional[tuple[int, int, int, int]] = None
) -> dict:
    """
    Take a screenshot and return base64 or save to file.

    Args:
        output: File path to save PNG (returns base64 if not set)
        display: X display to use
        region: Optional (x, y, width, height) to capture specific area

    Returns:
        Dict with path/size or base64/size, or error
    """
    disp = get_display(display)
    temp_path = output or f"/tmp/screenshot_{int(time.time())}.png"

    # Build scrot command
    cmd = ["scrot", "-o"]
    if region:
        x, y, w, h = region
        # scrot uses -a for area selection: x,y,w,h
        cmd.extend(["-a", f"{x},{y},{w},{h}"])
    cmd.append(temp_path)

    result = run_cmd(cmd, disp)
    if not result.success:
        return {"error": f"Screenshot failed: {result.stderr}"}

    path = Path(temp_path)
    if not path.exists():
        return {"error": "Screenshot file not created"}

    response = {
        "path": str(path),
        "size": path.stat().st_size,
    }

    if not output:
        # Return base64 if no output path specified
        with open(path, "rb") as f:
            response["base64"] = base64.b64encode(f.read()).decode()
        # Clean up temp file
        path.unlink()
        del response["path"]

    return response


def screenshot_to_pil(display: Optional[str] = None):
    """
    Take a screenshot and return as PIL Image.

    Args:
        display: X display to use

    Returns:
        PIL Image object or None on error
    """
    try:
        from PIL import Image
        import io

        result = screenshot(display=display)
        if "error" in result:
            return None

        if "base64" in result:
            img_data = base64.b64decode(result["base64"])
            return Image.open(io.BytesIO(img_data))

        return Image.open(result["path"])
    except ImportError:
        return None
    except Exception:
        return None
