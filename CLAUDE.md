# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ubuntu Desktop Control is a Claude Code skill for GUI automation on Ubuntu/X11. It provides semantic element targeting using AT-SPI accessibility tree as the primary method and Tesseract OCR as fallback, along with xdotool for mouse/keyboard control.

## Running Commands

All commands go through the CLI entry point:
```bash
python3 scripts/desktop.py <command> [options]
```

Default X display is `:10.0`. Override with `--display` flag.

### Key Commands
```bash
# Check if AT-SPI and OCR are available
python3 scripts/desktop.py status

# Semantic element commands (preferred)
python3 scripts/desktop.py find-element --name "Confirm" --role button
python3 scripts/desktop.py click-element --name "Next" --verify
python3 scripts/desktop.py wait-for --name "Success" --timeout 30
python3 scripts/desktop.py list-elements --app Firefox

# OCR-only text finding
python3 scripts/desktop.py find-text "Button Label"

# Annotated screenshot with numbered elements (LLM-optimized)
python3 scripts/desktop.py screenshot-annotated --output /tmp/screen
# Returns: screenshot_path, annotated_path, elements with IDs and x_percent/y_percent

# Click element by cached ID (after screenshot-annotated)
python3 scripts/desktop.py click-id 5

# Coordinate-based commands (fallback)
python3 scripts/desktop.py click 500 300
python3 scripts/desktop.py click --x-percent 0.5 --y-percent 0.5  # Center of screen
python3 scripts/desktop.py click-percent 0.5 0.5  # Alternative syntax
python3 scripts/desktop.py type "Hello"
python3 scripts/desktop.py key "ctrl+a"
python3 scripts/desktop.py screenshot --output /tmp/screen.png
python3 scripts/desktop.py drag 100 100 500 300  # Drag from (100,100) to (500,300)
```

## Architecture

```
scripts/desktop.py         # CLI entry point - argparse commands dispatching to modules
src/desktop_control/
├── core.py               # Shared utilities: run_cmd(), CommandResult, DEFAULT_DISPLAY
├── element.py            # Unified Element class with ElementSource enum (ATSPI/OCR)
├── finder.py             # ElementFinder: AT-SPI first, OCR fallback orchestration
├── waiter.py             # Waiter: poll for elements with exponential backoff
├── atspi.py              # AT-SPI accessibility tree interface (pyatspi/GObject)
├── ocr.py                # Tesseract OCR via pytesseract
├── screenshot.py         # scrot-based screenshots
├── xdotool.py            # Mouse/keyboard control via xdotool
├── annotate.py           # Screenshot annotation with numbered markers
└── cache.py              # Element cache for click-by-ID
```

### Element Finding Strategy
1. `ElementFinder.find()` tries AT-SPI first (rich metadata: role, states, actions)
2. Falls back to OCR if AT-SPI doesn't find element and `name` was provided
3. Elements from both sources normalized to `Element` class for uniform interface

### Key Classes
- `Element`: Unified UI element with `center`, `is_visible`, `is_clickable` properties; `from_atspi()`/`from_ocr()` factory methods
- `ElementFinder`: Orchestrates finding with configurable `use_atspi`/`use_ocr` flags and `ocr_min_confidence` threshold
- `Waiter`: Polling with `wait_for_element()`, `wait_for_text()`, `wait_until_gone()`
- `ElementCache`: 5-second TTL cache for elements from `screenshot-annotated`

### LLM-Optimized Workflow
1. Run `screenshot-annotated` to get downsampled (1280x720) image with numbered red circles on interactive elements
2. LLM can reference elements by ID number (e.g., "click element #5")
3. Use `click-id N` to click cached element, or `click-percent X Y` for resolution-agnostic coordinates
4. Cache expires after 5 seconds; re-run `screenshot-annotated` to refresh

## Dependencies

System packages (Ubuntu): `xdotool scrot imagemagick at-spi2-core libatk-adaptor python3-gi gir1.2-atspi-2.0 tesseract-ocr`

Python packages: `PyGObject pytesseract Pillow opencv-python-headless numpy`

Install all with: `bash install.sh`

## Headless Session Setup

For Xvfb environments, AT-SPI requires:
```bash
export GTK_MODULES=gail:atk-bridge
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
/usr/lib/at-spi2-core/at-spi-bus-launcher &
```

For Chrome/Chromium accessibility: add `--force-renderer-accessibility` flag.
