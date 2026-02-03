#!/bin/bash
# Install dependencies for Ubuntu Desktop Control
# Run as: bash install.sh

set -e

echo "=== Ubuntu Desktop Control Installer ==="
echo ""

# Check if running on Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    echo "Warning: apt-get not found. This script is designed for Ubuntu/Debian."
    echo "You may need to manually install equivalent packages."
fi

# Install apt packages
echo "Installing system packages..."
sudo apt-get update
sudo apt-get install -y \
    xdotool \
    scrot \
    imagemagick \
    at-spi2-core \
    libatk-adaptor \
    python3-gi \
    python3-gi-cairo \
    gir1.2-atspi-2.0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    python3-pip \
    python3-venv

echo ""
echo "Installing Python packages..."

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install Python dependencies
pip3 install -r "$SCRIPT_DIR/requirements.txt"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "To verify the installation, run:"
echo "  python3 $SCRIPT_DIR/scripts/desktop.py status"
echo ""
echo "For headless Xvfb sessions, ensure these environment variables are set:"
echo "  export GTK_MODULES=gail:atk-bridge"
echo "  export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1"
echo ""
echo "And start the AT-SPI bus launcher:"
echo "  /usr/lib/at-spi2-core/at-spi-bus-launcher &"
echo ""
echo "For Chrome/Chromium, add the --force-renderer-accessibility flag."
