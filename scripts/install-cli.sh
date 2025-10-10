#!/bin/bash
# Install dvmtx CLI globally
# This script creates a symlink in /usr/local/bin

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DVMTX_SCRIPT="$SCRIPT_DIR/dvmtx"

echo "╔════════════════════════════════════════╗"
echo "║   Devmatrix CLI Installer             ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Check if dvmtx script exists
if [ ! -f "$DVMTX_SCRIPT" ]; then
    echo "✗ Error: dvmtx script not found at $DVMTX_SCRIPT"
    exit 1
fi

# Make script executable
chmod +x "$DVMTX_SCRIPT"
echo "✓ Script made executable"

# Option 1: System-wide installation (requires sudo)
if [ "$1" = "--system" ]; then
    echo ""
    echo "Installing system-wide (requires sudo)..."
    sudo ln -sf "$DVMTX_SCRIPT" /usr/local/bin/dvmtx
    echo "✓ Symlink created: /usr/local/bin/dvmtx"
    echo ""
    echo "✓ Installation complete!"
    echo "  You can now run 'dvmtx' from anywhere"

# Option 2: User installation (no sudo needed)
else
    # Add to user's local bin
    USER_BIN="$HOME/.local/bin"
    mkdir -p "$USER_BIN"

    ln -sf "$DVMTX_SCRIPT" "$USER_BIN/dvmtx"
    echo "✓ Symlink created: $USER_BIN/dvmtx"

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
        echo ""
        echo "⚠ Warning: $USER_BIN is not in your PATH"
        echo ""
        echo "Add this line to your ~/.bashrc or ~/.zshrc:"
        echo ""
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
        echo "Then run: source ~/.bashrc  (or ~/.zshrc)"
    else
        echo "✓ $USER_BIN is already in PATH"
    fi

    echo ""
    echo "✓ Installation complete!"
    echo "  You can now run 'dvmtx' from anywhere"
fi

echo ""
echo "Try it: dvmtx help"
echo ""
