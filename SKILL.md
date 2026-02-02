---
name: ubuntu-desktop-control
description:
  Control Ubuntu desktop GUI via xdotool - mouse, keyboard, screenshots, window
  management. For wallet automation, browser extensions, and GUI tasks Playwright
  can't reach.
license: MIT
metadata:
  author: lommaj
  version: '1.0.0'
---

# Desktop Control Skill

Control the desktop GUI using xdotool and screenshots. Useful for:
- Web3 wallet automation (MetaMask popups, etc.)
- Clicking on browser extension UIs
- Any GUI automation that Playwright can't reach

## Prerequisites

Required packages (install with apt):
```bash
sudo apt-get install -y xdotool scrot imagemagick
```

## Tools

All tools use `DISPLAY=:10.0` by default. Override with `--display` flag.

### screenshot

Take a screenshot of the desktop.

```bash
python3 scripts/desktop.py screenshot [--output PATH]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--output` | string | No | File path to save PNG. If omitted, returns base64. |
| `--display` | string | No | X display (default: `:10.0`) |

**Returns:** `{ "path": string, "size": int }` or `{ "base64": string, "size": int }`

---

### click

Click at screen coordinates.

```bash
python3 scripts/desktop.py click X Y [--right] [--middle] [--double]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `X` | int | Yes | X coordinate |
| `Y` | int | Yes | Y coordinate |
| `--right` | flag | No | Right click instead of left |
| `--middle` | flag | No | Middle click instead of left |
| `--double` | flag | No | Double click |
| `--delay` | float | No | Seconds to wait before clicking |

**Returns:** `{ "clicked": { "x": int, "y": int, "button": string, "double": bool } }`

---

### type

Type text using keyboard.

```bash
python3 scripts/desktop.py type "TEXT" [--type-delay MS]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `TEXT` | string | Yes | Text to type |
| `--type-delay` | int | No | Milliseconds between keystrokes (default: 12) |

**Returns:** `{ "typed": string }`

---

### key

Press a key or key combination.

```bash
python3 scripts/desktop.py key "KEYS"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `KEYS` | string | Yes | Key(s) to press (xdotool format) |

**Common keys:**
- `Return`, `Tab`, `Escape`, `BackSpace`, `Delete`
- `Up`, `Down`, `Left`, `Right`
- `ctrl+a`, `ctrl+c`, `ctrl+v`, `ctrl+shift+t`
- `alt+Tab`, `super` (Windows key)

**Returns:** `{ "pressed": string }`

---

### move

Move mouse to coordinates without clicking.

```bash
python3 scripts/desktop.py move X Y
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `X` | int | Yes | X coordinate |
| `Y` | int | Yes | Y coordinate |

**Returns:** `{ "moved": { "x": int, "y": int } }`

---

### active

Get information about the currently active window.

```bash
python3 scripts/desktop.py active
```

**Returns:**
```json
{
  "window_id": "71303172",
  "name": "FluxPoint - Google Chrome",
  "geometry": { "x": 10, "y": 37, "width": 1288, "height": 1054 }
}
```

---

### find

Find windows by name (partial match).

```bash
python3 scripts/desktop.py find "NAME"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `NAME` | string | Yes | Window name to search for (partial match) |

**Returns:** `{ "windows": [{ "window_id": string, "name": string }, ...] }`

---

### focus

Focus (activate) a window by name.

```bash
python3 scripts/desktop.py focus "NAME"
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `NAME` | string | Yes | Window name to focus (partial match, uses first result) |

**Returns:** `{ "focused": string }` (window_id)

---

### position

Get current mouse cursor position.

```bash
python3 scripts/desktop.py position
```

**Returns:** `{ "position": { "x": int, "y": int } }`

---

### windows

List all windows on the desktop.

```bash
python3 scripts/desktop.py windows
```

**Returns:** `{ "windows": [{ "window_id": string, "name": string }, ...] }`

---

## Wallet Automation Workflow

1. **Screenshot** - See current state, identify button coordinates
2. **Find/Focus** - Locate and activate the wallet popup window
3. **Click** - Click buttons by coordinates from screenshot
4. **Type** - Enter amounts, passwords, addresses
5. **Key** - Press Enter to confirm, Tab to navigate
6. **Screenshot** - Verify the action completed

## Example: Approve MetaMask Transaction

```bash
# 1. Take screenshot to see the popup
python3 scripts/desktop.py screenshot --output /tmp/before.png

# 2. Focus MetaMask window
python3 scripts/desktop.py focus "MetaMask"

# 3. Click "Confirm" button (coordinates from screenshot)
python3 scripts/desktop.py click 250 450

# 4. Take screenshot to verify
python3 scripts/desktop.py screenshot --output /tmp/after.png
```

## Tips

- Always screenshot first to find coordinates
- MetaMask popups are separate windows - use `find` to locate them
- Use `--delay` flag to wait for animations/loading
- Coordinates are screen-absolute, not window-relative
