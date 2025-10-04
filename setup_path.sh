#!/bin/bash
# Web Research Agent - PATH Setup Script for Linux/Mac
# This script adds the Python Scripts directory to your PATH permanently

echo "================================="
echo "Web Research Agent - PATH Setup"
echo "================================="
echo ""

# Detect the shell
SHELL_NAME=$(basename "$SHELL")
SHELL_RC=""

case "$SHELL_NAME" in
    bash)
        SHELL_RC="$HOME/.bashrc"
        ;;
    zsh)
        SHELL_RC="$HOME/.zshrc"
        ;;
    fish)
        SHELL_RC="$HOME/.config/fish/config.fish"
        ;;
    *)
        echo "⚠ Unsupported shell: $SHELL_NAME"
        echo "Please add to PATH manually"
        ;;
esac

# Common Python Scripts locations
SCRIPTS_DIRS=(
    "$HOME/.local/bin"
    "$HOME/Library/Python/3.*/bin"
    "/usr/local/bin"
)

# Find the scripts directory
SCRIPTS_PATH=""
for dir in "${SCRIPTS_DIRS[@]}"; do
    # Expand wildcards
    for expanded in $dir; do
        if [ -d "$expanded" ] && [ -f "$expanded/webresearch" ] 2>/dev/null; then
            SCRIPTS_PATH="$expanded"
            break 2
        fi
    done
done

# If not found, use the most common location
if [ -z "$SCRIPTS_PATH" ]; then
    SCRIPTS_PATH="$HOME/.local/bin"
    echo "ℹ Using default location: $SCRIPTS_PATH"
fi

echo "Python Scripts directory: $SCRIPTS_PATH"
echo ""

# Check if already in PATH
if echo "$PATH" | grep -q "$SCRIPTS_PATH"; then
    echo "✓ Scripts directory is already in your PATH!"
    echo ""
    echo "Try running: webresearch"
    exit 0
fi

# Add to PATH
if [ -n "$SHELL_RC" ]; then
    echo "Adding to PATH in $SHELL_RC..."

    # Create backup
    cp "$SHELL_RC" "${SHELL_RC}.backup.$(date +%Y%m%d_%H%M%S)"

    # Add to shell config
    if [ "$SHELL_NAME" = "fish" ]; then
        echo "set -gx PATH $SCRIPTS_PATH \$PATH" >> "$SHELL_RC"
    else
        echo "export PATH=\"$SCRIPTS_PATH:\$PATH\"" >> "$SHELL_RC"
    fi

    echo "✓ Successfully added to PATH!"
    echo ""
    echo "IMPORTANT: Run this command to reload your shell:"
    echo "  source $SHELL_RC"
    echo ""
    echo "Or simply restart your terminal."
    echo ""
    echo "Then run: webresearch"
else
    echo "⚠ Could not determine shell configuration file"
    echo ""
    echo "Add this line to your shell's configuration file manually:"
    echo "  export PATH=\"$SCRIPTS_PATH:\$PATH\""
fi

echo ""
echo "================================="
echo "Setup Complete!"
echo "================================="
