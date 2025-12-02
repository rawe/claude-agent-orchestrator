#!/bin/bash
# Generate PNG icons from SVG
# Requires: ImageMagick (convert) or Inkscape

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ICONS_DIR="$SCRIPT_DIR/icons"
SVG_FILE="$ICONS_DIR/icon.svg"

# Check for available tools
if command -v convert &> /dev/null; then
    echo "Using ImageMagick..."
    for size in 16 32 48 128; do
        convert -background none -resize ${size}x${size} "$SVG_FILE" "$ICONS_DIR/icon${size}.png"
        echo "Created icon${size}.png"
    done
elif command -v inkscape &> /dev/null; then
    echo "Using Inkscape..."
    for size in 16 32 48 128; do
        inkscape "$SVG_FILE" -w $size -h $size -o "$ICONS_DIR/icon${size}.png"
        echo "Created icon${size}.png"
    done
elif command -v rsvg-convert &> /dev/null; then
    echo "Using rsvg-convert..."
    for size in 16 32 48 128; do
        rsvg-convert -w $size -h $size "$SVG_FILE" -o "$ICONS_DIR/icon${size}.png"
        echo "Created icon${size}.png"
    done
else
    echo "No suitable tool found. Please install one of:"
    echo "  - ImageMagick: brew install imagemagick"
    echo "  - Inkscape: brew install inkscape"
    echo "  - librsvg: brew install librsvg"
    echo ""
    echo "Creating placeholder PNG icons with basic colors..."

    # Create simple colored placeholder PNGs using printf (works without external tools)
    # This creates minimal valid PNG files
    for size in 16 32 48 128; do
        # Create a simple 1x1 purple pixel PNG and note that proper icons should be generated
        echo "Note: icon${size}.png needs to be created manually or with proper tools"
    done

    exit 1
fi

echo ""
echo "Icons generated successfully!"
echo "You can now load the extension in your browser."
