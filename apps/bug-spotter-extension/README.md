# Bug Spotter

A cross-browser extension (Chrome & Firefox) for creating bug reports by visually selecting page elements and pushing structured reports to the Context Store API.

## Use Case

This extension is designed as an **error reporting tool** for developers and QA teams. When you encounter a bug or issue on a webpage:

1. Select the problematic element visually
2. The extension captures a **stable CSS selector** that other developers can use to locate the same element
3. Optionally include console logs, element HTML, and system metadata
4. Push a structured Markdown report to your Context Store

The key value is the **reproducible CSS selector** - another developer can use it to find exactly the same element you reported, making bug reproduction much easier.

## Features

- **Visual element selector**: Hover to highlight elements, click to select
- **Stable CSS selectors**: Prioritizes IDs, data-testid attributes, and semantic markup over brittle auto-generated classes
- **Console log capture**: Automatically captures console output (log, warn, error, info, debug, trace)
- **System metadata**: Browser, OS, screen resolution, viewport, language, timezone
- **Markdown reports**: Well-formatted bug reports ready for issue trackers
- **Cross-browser**: Works on Chrome 88+ and Firefox 109+

## Installation

### Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select the `context-store-browser-extension` folder
5. The extension icon appears in your toolbar

### Firefox

1. Open Firefox and navigate to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on...**
3. Select the `manifest.json` file from the extension folder
4. The extension icon appears in your toolbar

> **Note**: For permanent Firefox installation, the extension needs to be signed by Mozilla.

## Usage

### Step-by-Step

1. **Navigate** to the page with the issue
2. **Click** the Context Store extension icon
3. **Click "Select Element"** - the popup closes and you enter selection mode
4. **Hover** over elements - they highlight with an indigo border and label showing tag/class info
5. **Click** the problematic element to select it
6. **Press ESC** to cancel selection (optional)
7. **Click the extension icon again** to reopen the popup
8. **Review** the captured CSS selector
9. **Toggle options**:
   - "Element HTML content" - include the element's markup
   - "Console logs" - include captured console output
   - "System metadata" - include browser/OS info
10. **Add a description** explaining the issue
11. **Add tags** for organization (default: `bug-screenshot`, domain name)
12. **Click "Push to Context Store"**

### Visual Feedback During Selection

When in selection mode, you'll see:
- **Indigo border** around the hovered element
- **Label** showing `tag.class#id` (e.g., `button.submit-btn`)
- **Instructions** at the top: "Click an element to select it • Press ESC to cancel"

## CSS Selector Strategy

The extension generates **stable, reproducible selectors** that won't break when the page changes. Priority order:

| Priority | Selector Type | Example |
|----------|--------------|---------|
| 1 | ID (non-generated) | `#submit-button` |
| 2 | Test attributes | `[data-testid="login-form"]` |
| 3 | Semantic attributes | `[role="dialog"]`, `[aria-label="Close"]` |
| 4 | Unique class combination | `.btn.primary` |
| 5 | Path-based fallback | `#container > div.card > button` |

**Auto-generated patterns are detected and avoided:**
- React: `:r0:`, `css-1a2b3c`
- Angular: `ng-*`, `_ngcontent-*`
- Styled-components: `sc-*`
- Vue/Svelte: `data-v-*`, `svelte-*`
- Generic: hex strings, numeric suffixes

## Nested Element Strategy

When hovering, the extension highlights the **deepest element** under your cursor. This is the most intuitive approach - what you point at is what you get.

**Tips for selecting parent containers:**
- Hover over padding/margin areas of the parent (not over nested children)
- Select a child element, then manually broaden the selector if needed

## What Gets Captured

| Data | Always Included | Optional (Toggle) |
|------|-----------------|-------------------|
| CSS Selector | ✅ | - |
| Element tag name | ✅ | - |
| Selector validity | ✅ | - |
| Page URL | ✅ | - |
| Page title | ✅ | - |
| Capture timestamp | ✅ | - |
| Element HTML | - | ✅ |
| Console logs | - | ✅ (default on) |
| System metadata | - | ✅ (default on) |
| User description | - | ✅ (free text) |
| Custom tags | - | ✅ |

## Output Format

Reports are saved as Markdown files:

```markdown
# Bug Report: My Application

## Page Information
- **URL:** https://example.com/dashboard
- **Captured:** 2025-12-02T14:30:00.000Z

## Selected Element

### CSS Selector
```css
[data-testid="submit-button"]
```

- **Tag:** `<button>`
- **Selector Valid:** Yes

### Element HTML
```html
<button data-testid="submit-button" class="btn primary" disabled>
  Submit Form
</button>
```

## Description
The submit button remains disabled even after filling all required fields.
This happens intermittently, approximately 1 in 5 page loads.

## Console Output
```
[ERROR] 2025-12-02T14:29:58.000Z
  TypeError: Cannot read property 'validate' of undefined
    at FormValidator.check (validator.js:42)
```

## System Information
| Property | Value |
|----------|-------|
| Browser | Chrome 120.0 |
| OS | macOS 14.1 |
| Screen | 2560x1440 |
| Viewport | 1920x1080 |
| DPR | 2 |
| Language | en-US |
| Timezone | America/New_York |
```

## Configuration

Click the **gear icon** in the popup footer to access settings:

| Setting | Default | Description |
|---------|---------|-------------|
| Server URL | `http://localhost:8766` | Context Store API endpoint |

## Requirements

- **Context Store server** running and accessible
- **CORS configured** on the server to accept extension requests

### CORS Setup

Add to your Context Store server's CORS configuration:

```bash
# Environment variable
CORS_ORIGINS=chrome-extension://<your-extension-id>,moz-extension://<your-extension-id>

# Or for development
CORS_ORIGINS=*
```

## Project Structure

```
bug-spotter-extension/
├── manifest.json          # Extension manifest (MV3)
├── background.js          # Service worker - API communication
├── content.js             # Content script - coordinates selection
├── selector.js            # Element picker with visual overlay
├── injected.js            # Console interceptor (page context)
├── popup/
│   ├── popup.html         # Popup UI
│   ├── popup.css          # Styles (light/dark mode support)
│   └── popup.js           # Popup logic and state management
├── icons/
│   ├── icon.svg           # Source SVG icon (edit this to change the icon)
│   ├── icon16.png         # Toolbar icon
│   ├── icon32.png         # Toolbar icon (retina)
│   ├── icon48.png         # Extension management page
│   └── icon128.png        # Chrome Web Store / details page
└── README.md
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Popup     │────▶│Content Script│────▶│ Selector.js │
│  (popup.js) │     │ (content.js) │     │(page context)│
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       │                   │                    ▼
       │                   │              ┌───────────┐
       │                   │              │  Visual   │
       │                   │              │  Overlay  │
       │                   │              └───────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌──────────────┐
│ Background  │     │ Injected.js  │
│  (API calls)│     │(console logs)│
└─────────────┘     └──────────────┘
       │
       ▼
┌─────────────────┐
│ Context Store   │
│     API         │
└─────────────────┘
```

## Troubleshooting

### "Disconnected" status
1. Ensure the Context Store server is running (`http://localhost:8766/health`)
2. Check the server URL in extension settings
3. Verify CORS is configured correctly on the server

### Element selection not starting
- Refresh the page after installing/updating the extension
- Make sure you're not on a restricted page (`chrome://`, `about:`, Chrome Web Store)
- Check the browser console for errors

### "Selector may not be unique" warning
- The generated selector matches multiple elements on the page
- Try selecting a more specific child element
- Or select a parent with a unique ID/data attribute

### Console logs showing 0
- Console capture starts when the page loads
- Logs from before extension injection aren't captured
- Refresh the page to start capturing from the beginning

## API Integration

### Push Document Endpoint

```http
POST /documents
Content-Type: multipart/form-data

file: <Markdown report content>
tags: bug-screenshot,example.com,login-page
metadata: {
  "source_url": "https://example.com/login",
  "source_domain": "example.com",
  "css_selector": "[data-testid=\"submit-button\"]",
  "element_tag": "button",
  "description": "Button not working",
  "browser": "Chrome",
  "browser_version": "120.0",
  "os": "macOS 14.1",
  "viewport": "1920x1080",
  "captured_at": "2025-12-02T14:30:00.000Z"
}
```

### Response

```json
{
  "id": "doc_a1b2c3d4e5f6",
  "filename": "2025-12-02-my-application-submit-button.md",
  "content_type": "text/markdown",
  "size_bytes": 1847,
  "created_at": "2025-12-02T14:30:01.000000",
  "tags": ["bug-screenshot", "example.com"],
  "metadata": { ... },
  "url": "http://localhost:8766/documents/doc_a1b2c3d4e5f6"
}
```

## Browser Compatibility

| Browser | Minimum Version | Status |
|---------|-----------------|--------|
| Chrome | 88+ | ✅ Fully supported |
| Firefox | 109+ | ✅ Fully supported |
| Edge | 88+ | ✅ Fully supported |
| Safari | - | ❌ Not tested |

## Icon Generation

The extension icons are generated from the source SVG file (`icons/icon.svg`). To regenerate the PNG icons after modifying the SVG:

### Prerequisites

Install `librsvg` via Homebrew (macOS):

```bash
brew install librsvg
```

### Generate Icons

From the `icons/` directory, run:

```bash
cd icons/
rsvg-convert -w 16 -h 16 icon.svg -o icon16.png
rsvg-convert -w 32 -h 32 icon.svg -o icon32.png
rsvg-convert -w 48 -h 48 icon.svg -o icon48.png
rsvg-convert -w 128 -h 128 icon.svg -o icon128.png
```

Or as a one-liner:

```bash
for size in 16 32 48 128; do rsvg-convert -w $size -h $size icon.svg -o icon${size}.png; done
```

### Icon Design

The icon features:
- **Indigo circular background** (#6366f1) matching the UI theme
- **Stylized bug** with body, head, eyes, antennae, and legs
- **Subtle crosshair overlay** representing "spotting" bugs

To modify the icon, edit `icons/icon.svg` and regenerate the PNGs.

## License

MIT License - See main project LICENSE file.
