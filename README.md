# Ubuntu Desktop Control

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Ubuntu](https://img.shields.io/badge/Platform-Ubuntu%2FX11-orange.svg)](https://ubuntu.com)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-purple.svg)](https://claude.ai/code)

Desktop GUI automation skill for Claude Code on Ubuntu/X11. Control mouse, keyboard, take screenshots, and manage windows using xdotool and scrot.

## Use Cases

- **Web3 Wallet Automation** - Interact with MetaMask popups and transaction confirmations
- **Browser Extension UIs** - Click buttons in extension windows that Playwright can't reach
- **Desktop Application Control** - Automate any GUI application on the desktop
- **Screenshot Verification** - Capture screen state before and after actions

## Installation

### Prerequisites

Install required system packages:

```bash
sudo apt-get install -y xdotool scrot imagemagick
```

### Install Skill

```bash
claude skill install lommaj/ubuntu-desktop-control
```

## Quick Start

```bash
# Take a screenshot
python3 scripts/desktop.py screenshot --output /tmp/screen.png

# Click at coordinates
python3 scripts/desktop.py click 500 300

# Type text
python3 scripts/desktop.py type "Hello World"

# Press a key combination
python3 scripts/desktop.py key "ctrl+a"

# Focus a window by name
python3 scripts/desktop.py focus "MetaMask"
```

## Features

| Command | Description |
|---------|-------------|
| `screenshot` | Capture desktop as PNG file or base64 |
| `click` | Click at X,Y coordinates (left/right/middle/double) |
| `type` | Type text with configurable keystroke delay |
| `key` | Press key combinations (ctrl+c, alt+Tab, etc.) |
| `move` | Move mouse cursor without clicking |
| `active` | Get active window info and geometry |
| `find` | Search for windows by name |
| `focus` | Activate a window by name |
| `position` | Get current mouse cursor position |
| `windows` | List all desktop windows |

## Requirements

- Ubuntu Linux (or any X11-compatible system)
- X display server (default: `:10.0`)
- Python 3.6+
- xdotool
- scrot

## Documentation

- [SKILL.md](SKILL.md) - Full skill documentation with all parameters
- [AGENTS.md](AGENTS.md) - Expanded guide for AI agents

## License

MIT License - see [LICENSE](LICENSE) for details.
