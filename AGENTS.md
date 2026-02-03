# Ubuntu Desktop Control - Agent Guide

> Desktop GUI automation skill for Ubuntu/X11 with semantic element targeting. Uses AT-SPI accessibility tree as primary method and OCR as fallback. Control mouse, keyboard, find elements by name/role, and wait for conditions.

## Overview

This skill enables "human-level" desktop control by finding UI elements semantically rather than by coordinates. The primary method uses the AT-SPI accessibility tree (which knows element roles, states, and actions), with OCR as a fallback for elements not exposed through accessibility APIs.

**Capabilities:**
- Find and click buttons, inputs, links by name
- Wait for elements or text to appear/disappear
- List all interactive elements in an application
- Fall back to OCR when AT-SPI can't find elements
- Traditional coordinate-based clicking still available

## Prerequisites

Before using this skill, run the installer:

```bash
bash install.sh
```

For headless Xvfb sessions, set up the accessibility environment:

```bash
export GTK_MODULES=gail:atk-bridge
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
/usr/lib/at-spi2-core/at-spi-bus-launcher &
```

For Chrome/Chromium, add `--force-renderer-accessibility` flag.

Check that everything is working:

```bash
python3 scripts/desktop.py status
```

## Command Reference

### Semantic Commands (Recommended)

| Command | Purpose | Example |
|---------|---------|---------|
| `find-element` | Find UI element by name/role | `--name "Confirm" --role button` |
| `find-text` | Find text on screen (OCR) | `find-text "I have an existing wallet"` |
| `click-element` | Click element by name/role | `--name "Next" --verify` |
| `wait-for` | Wait for element/text to appear | `--text "Success" --timeout 30` |
| `list-elements` | List interactive elements | `--app "Firefox" --role button` |
| `status` | Check AT-SPI/OCR availability | |

### Coordinate Commands (Fallback)

| Command | Purpose | Example |
|---------|---------|---------|
| `screenshot` | Capture desktop | `--output /tmp/screen.png` |
| `click` | Click at coordinates | `click 500 300 --double` |
| `type` | Type text | `type "hello@example.com"` |
| `key` | Press key combination | `key "ctrl+a"` |
| `move` | Move mouse | `move 500 300` |
| `active` | Get active window | |
| `find-window` | Find windows by name | `find-window "MetaMask"` |
| `focus` | Focus window | `focus "Chrome"` |
| `position` | Get mouse position | |
| `windows` | List all windows | |

## Recommended Workflows

### Strategy: Semantic First, Coordinates as Fallback

1. **Always start with `status`** to verify AT-SPI and OCR are available
2. **Try semantic commands first** (`click-element`, `wait-for`)
3. **Fall back to `find-text`** if AT-SPI doesn't expose the element
4. **Use coordinates only** when semantic methods fail

### Wallet Transaction Approval

```bash
# 1. Check status
python3 scripts/desktop.py status

# 2. Focus wallet window
python3 scripts/desktop.py focus "MetaMask"

# 3. Wait for Confirm button to appear
python3 scripts/desktop.py wait-for --name "Confirm" --role button --timeout 30

# 4. Click Confirm with verification
python3 scripts/desktop.py click-element --name "Confirm" --verify

# 5. Wait for success (OCR for status text)
python3 scripts/desktop.py wait-for --text "Transaction submitted" --timeout 60
```

### Wallet Import Flow

```bash
# 1. Find and click import option
python3 scripts/desktop.py click-element --name "I already have a wallet"

# 2. Wait for input field
python3 scripts/desktop.py wait-for --role entry --timeout 10

# 3. Type seed phrase
python3 scripts/desktop.py type "word1 word2 word3..."

# 4. Click continue
python3 scripts/desktop.py click-element --name "Import"

# 5. Wait for completion
python3 scripts/desktop.py wait-for --text "Wallet imported" --timeout 30
```

### Browser Extension Interaction

```bash
# 1. List all buttons to understand the UI
python3 scripts/desktop.py list-elements --app "Chrome" --role button

# 2. Click extension button by name
python3 scripts/desktop.py click-element --name "Connect wallet" --app "Chrome"

# 3. Wait for popup
python3 scripts/desktop.py wait-for --name "Approve" --timeout 10

# 4. Click approve
python3 scripts/desktop.py click-element --name "Approve"
```

### Handling Unknown UIs (Discovery Mode)

When you don't know the element names:

```bash
# 1. List all interactive elements
python3 scripts/desktop.py list-elements --app "AppName"

# 2. If AT-SPI returns nothing, screenshot and use OCR
python3 scripts/desktop.py screenshot --output /tmp/discovery.png
python3 scripts/desktop.py find-text "button text" --all

# 3. Once you find the text, click it
python3 scripts/desktop.py click-element --name "button text"
```

## How Element Finding Works

```
User: click-element --name "Confirm"
           │
           ▼
    ┌─────────────┐
    │ Try AT-SPI  │ ◄─ Fast, reliable, knows element roles
    └──────┬──────┘
           │
    Found? │
           │
    ┌──────┴──────┐
    │Yes          │No
    ▼             ▼
  Click      ┌─────────────┐
  element    │ Fallback:   │
             │ Screenshot  │
             │ + OCR       │
             └──────┬──────┘
                    │
             Found? │
                    │
             ┌──────┴──────┐
             │Yes          │No
             ▼             ▼
           Click        Error
           at OCR
           coords
```

## Element Information

### AT-SPI Elements

AT-SPI elements include rich metadata:

```json
{
  "name": "Confirm",
  "bounds": { "x": 400, "y": 300, "width": 100, "height": 30 },
  "center": { "x": 450, "y": 315 },
  "role": "push button",
  "source": "atspi",
  "states": ["visible", "showing", "enabled", "focusable"],
  "actions": ["click"],
  "app_name": "Firefox",
  "visible": true,
  "enabled": true,
  "clickable": true
}
```

### OCR Elements

OCR elements have position and confidence:

```json
{
  "name": "Confirm",
  "bounds": { "x": 402, "y": 298, "width": 96, "height": 24 },
  "center": { "x": 450, "y": 310 },
  "source": "ocr",
  "confidence": 95.2
}
```

## Common Element Roles

| Role | Description | Examples |
|------|-------------|----------|
| `push button` | Clickable button | "Submit", "Cancel" |
| `toggle button` | On/off button | Theme toggle |
| `entry` | Text input field | Email, password |
| `combo box` | Dropdown | Currency selector |
| `check box` | Checkbox | "Remember me" |
| `radio button` | Radio option | Payment method |
| `link` | Clickable link | "Terms of Service" |
| `menu item` | Menu option | "Settings" |
| `slider` | Range slider | Volume control |

## Troubleshooting

### AT-SPI Not Available

```bash
# Check if AT-SPI is running
python3 scripts/desktop.py status

# If not, start the bus launcher
/usr/lib/at-spi2-core/at-spi-bus-launcher &

# Set environment variables
export GTK_MODULES=gail:atk-bridge
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
```

### Element Not Found via AT-SPI

Some applications don't expose elements via AT-SPI. Use OCR:

```bash
# Try OCR-only search
python3 scripts/desktop.py find-text "Button Label"
```

### OCR Confidence Too Low

If OCR finds text with low confidence:

1. Take a screenshot and check the image quality
2. Lower the confidence threshold (code modification needed)
3. Try exact matching: `--exact`

### Chrome Extensions Not Accessible

Chrome extensions often don't expose accessibility info. For extension popups:

1. Screenshot first to identify coordinates
2. Use `find-text` for OCR-based finding
3. Fall back to coordinate clicking if needed

### Wait Timeout

If `wait-for` times out:

1. Increase timeout: `--timeout 60`
2. Check that the element name/text is correct
3. Verify the window is focused
4. Try `list-elements` to see what's available

## Best Practices

1. **Always check status first** - Verify AT-SPI and OCR are working before starting automation

2. **Prefer semantic over coordinates** - `click-element` adapts to UI changes, coordinates don't

3. **Use wait-for instead of sleep** - Polling is more reliable than fixed delays

4. **Specify role when ambiguous** - If "Confirm" appears as both text and button, use `--role button`

5. **Use --verify for critical actions** - Adds OCR verification before clicking to prevent misclicks

6. **List elements for discovery** - When automating a new UI, start by listing available elements

7. **Fall back gracefully** - If semantic methods fail, screenshot and use coordinates

## References

- [AT-SPI Documentation](https://www.freedesktop.org/wiki/Accessibility/AT-SPI2/)
- [pyatspi API](https://lazka.github.io/pgi-docs/Atspi-2.0/)
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- [xdotool Documentation](https://github.com/jordansissel/xdotool)
