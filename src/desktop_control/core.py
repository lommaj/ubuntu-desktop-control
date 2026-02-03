"""
Core utilities shared across desktop control modules.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional

DEFAULT_DISPLAY = ":10.0"


@dataclass
class CommandResult:
    """Result of a shell command execution."""
    returncode: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.returncode == 0


def run_cmd(
    cmd: list[str],
    display: Optional[str] = None,
    timeout: Optional[float] = None
) -> CommandResult:
    """
    Run a command with optional DISPLAY override.

    Args:
        cmd: Command and arguments as list
        display: X display to use (e.g., ":10.0")
        timeout: Command timeout in seconds

    Returns:
        CommandResult with returncode, stdout, and stderr
    """
    env = os.environ.copy()
    if display:
        env["DISPLAY"] = display

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout
        )
        return CommandResult(
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip()
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s"
        )
    except Exception as e:
        return CommandResult(
            returncode=-1,
            stdout="",
            stderr=str(e)
        )


def get_display(display: Optional[str] = None) -> str:
    """Get the display to use, with fallback to default."""
    if display:
        return display
    return os.environ.get("DISPLAY", DEFAULT_DISPLAY)
