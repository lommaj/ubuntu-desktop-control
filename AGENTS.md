# Ubuntu Desktop Control - Agent Guide

> Desktop GUI automation skill for Ubuntu/X11 using xdotool and scrot. Control mouse, keyboard, take screenshots, and manage windows - ideal for wallet popups, browser extensions, and any GUI automation beyond browser scope.

## Overview

This skill provides desktop-level GUI automation capabilities for Ubuntu systems running X11. It bridges the gap between browser automation tools (like Playwright) and native desktop interactions, enabling control of:

- Wallet popups (MetaMask, etc.)
- Browser extension windows
- Native desktop applications
- Any GUI element visible on screen

## Prerequisites

Before using this skill, ensure the required packages are installed:

```bash
sudo apt-get install -y xdotool scrot imagemagick
```

## Tool Reference

All commands are executed via the Python script. The default X display is `:10.0`. Override with `--display` flag on any command.

### screenshot

Capture the current desktop state as a PNG image.

```bash
python3 scripts/desktop.py screenshot [--output PATH] [--display DISPLAY]
```

**Parameters:**
- `--output` (optional): File path to save PNG. If omitted, returns base64-encoded image.
- `--display` (optional): X display to capture (default: `:10.0`)

**Response:**
```json
// With --output specified:
{ "path": "/tmp/screenshot.png", "size": 245678 }

// Without --output:
{ "base64": "iVBORw0KGgo...", "size": 245678 }
```

**Use Cases:**
- Capture initial state before performing actions
- Identify coordinates for click targets
- Verify action completion
- Debug automation failures

---

### click

Perform a mouse click at specific screen coordinates.

```bash
python3 scripts/desktop.py click X Y [--right] [--middle] [--double] [--delay SECONDS]
```

**Parameters:**
- `X` (required): X coordinate in pixels from screen left edge
- `Y` (required): Y coordinate in pixels from screen top edge
- `--right` (optional): Perform right-click instead of left
- `--middle` (optional): Perform middle-click instead of left
- `--double` (optional): Perform double-click
- `--delay` (optional): Seconds to wait before clicking (for animations)

**Response:**
```json
{ "clicked": { "x": 500, "y": 300, "button": "left", "double": false } }
```

**Important Notes:**
- Coordinates are screen-absolute, not window-relative
- Always screenshot first to determine correct coordinates
- Use `--delay` when waiting for UI animations to complete

---

### type

Type text using keyboard simulation.

```bash
python3 scripts/desktop.py type "TEXT" [--type-delay MS]
```

**Parameters:**
- `TEXT` (required): Text string to type
- `--type-delay` (optional): Milliseconds between keystrokes (default: 12)

**Response:**
```json
{ "typed": "0x1234abcd..." }
```

**Use Cases:**
- Enter wallet addresses
- Input passwords (ensure security context)
- Fill form fields
- Type search queries

---

### key

Press a key or key combination.

```bash
python3 scripts/desktop.py key "KEYS"
```

**Parameters:**
- `KEYS` (required): Key(s) to press in xdotool format

**Common Key Names:**
| Category | Keys |
|----------|------|
| Navigation | `Return`, `Tab`, `Escape`, `BackSpace`, `Delete` |
| Arrows | `Up`, `Down`, `Left`, `Right` |
| Modifiers | `ctrl`, `alt`, `shift`, `super` |
| Combinations | `ctrl+a`, `ctrl+c`, `ctrl+v`, `ctrl+shift+t`, `alt+Tab` |

**Response:**
```json
{ "pressed": "ctrl+a" }
```

---

### move

Move the mouse cursor without clicking.

```bash
python3 scripts/desktop.py move X Y
```

**Parameters:**
- `X` (required): Target X coordinate
- `Y` (required): Target Y coordinate

**Response:**
```json
{ "moved": { "x": 500, "y": 300 } }
```

---

### active

Get information about the currently active (focused) window.

```bash
python3 scripts/desktop.py active
```

**Response:**
```json
{
  "window_id": "71303172",
  "name": "FluxPoint - Google Chrome",
  "geometry": { "x": 10, "y": 37, "width": 1288, "height": 1054 }
}
```

**Use Cases:**
- Verify correct window is focused before actions
- Get window dimensions for relative positioning
- Debug window focus issues

---

### find

Search for windows by name (partial match).

```bash
python3 scripts/desktop.py find "NAME"
```

**Parameters:**
- `NAME` (required): Window name substring to search for

**Response:**
```json
{
  "windows": [
    { "window_id": "71303172", "name": "MetaMask Notification" },
    { "window_id": "71303180", "name": "MetaMask" }
  ]
}
```

---

### focus

Activate (focus) a window by name.

```bash
python3 scripts/desktop.py focus "NAME"
```

**Parameters:**
- `NAME` (required): Window name to focus (uses first partial match)

**Response:**
```json
{ "focused": "71303172" }
```

---

### position

Get the current mouse cursor position.

```bash
python3 scripts/desktop.py position
```

**Response:**
```json
{ "position": { "x": 512, "y": 384 } }
```

---

### windows

List all windows on the desktop.

```bash
python3 scripts/desktop.py windows
```

**Response:**
```json
{
  "windows": [
    { "window_id": "71303172", "name": "Terminal" },
    { "window_id": "71303180", "name": "Google Chrome" },
    { "window_id": "71303188", "name": "MetaMask Notification" }
  ]
}
```

---

## Common Workflows

### Wallet Transaction Approval

```bash
# 1. Capture current state
python3 scripts/desktop.py screenshot --output /tmp/before.png

# 2. Find and focus the wallet popup
python3 scripts/desktop.py find "MetaMask"
python3 scripts/desktop.py focus "MetaMask"

# 3. Click the "Confirm" button (coordinates from screenshot analysis)
python3 scripts/desktop.py click 250 450

# 4. Wait and verify
sleep 1
python3 scripts/desktop.py screenshot --output /tmp/after.png
```

### Browser Extension Interaction

```bash
# 1. Screenshot to find extension popup
python3 scripts/desktop.py screenshot --output /tmp/extension.png

# 2. Click extension icon (example coordinates)
python3 scripts/desktop.py click 1200 50

# 3. Wait for popup to appear
sleep 0.5

# 4. Screenshot popup and locate button
python3 scripts/desktop.py screenshot --output /tmp/popup.png

# 5. Click desired button
python3 scripts/desktop.py click 1150 200
```

### Form Filling

```bash
# Focus input field (click on it)
python3 scripts/desktop.py click 400 300

# Select all existing text
python3 scripts/desktop.py key "ctrl+a"

# Type new value
python3 scripts/desktop.py type "0x742d35Cc6634C0532925a3b844Bc9e7595f..."

# Move to next field
python3 scripts/desktop.py key "Tab"

# Type next value
python3 scripts/desktop.py type "1.5"

# Submit
python3 scripts/desktop.py key "Return"
```

---

## Troubleshooting

### Common Issues

**"Cannot open display"**
- Ensure X server is running
- Check DISPLAY environment variable matches `--display` flag
- For remote sessions, ensure X forwarding is enabled

**"No windows found"**
- Window may not be open yet - add delay
- Check exact window name with `windows` command
- Try broader search term with `find`

**Click not registering**
- Verify coordinates with screenshot
- Window may need focus first
- Add `--delay` for animation completion

**Typing produces wrong characters**
- Check keyboard layout settings
- Increase `--type-delay` for slower systems

### Best Practices

1. **Always screenshot first** - Never guess coordinates
2. **Focus before clicking** - Ensure target window is active
3. **Use delays appropriately** - Allow time for UI transitions
4. **Verify with screenshots** - Confirm actions completed successfully
5. **Handle errors gracefully** - Check for error responses in JSON output

---

## References

- [xdotool Documentation](https://github.com/jordansissel/xdotool)
- [scrot Screenshot Utility](https://github.com/resurrecting-open-source-projects/scrot)
