# Agent Orchestrator Slides - Editor Context

You are editing an HTML slide presentation about the Agent Orchestrator framework. This document contains everything you need to make consistent edits.

## File Structure

```
docs/slides/
├── slides.json         # SINGLE SOURCE OF TRUTH for navigation - EDIT THIS for slide changes
├── navigation.js       # Shared navigation script (do not edit)
├── content/            # Markdown content files (source of truth for content)
│   ├── 01-orchestration.md
│   └── ...
├── index.html          # Navigation hub - auto-generated from slides.json
├── template.html       # Design system reference - READ for styling patterns
├── 01-orchestration.html  # Main flow slides (01 through 21)
├── 02a-problem-*.html     # Deep dive slides (out of main flow)
└── 21-summary.html
```

## Content-First Workflow

**Why:** Markdown files are smaller than HTML (~1KB vs ~10KB), reducing context size for AI editing sessions.

**How it works:**
- `content/*.md` = source of truth for **what** to present (text, message, ideas)
- `*.html` = **how** it's visualized (layout, CSS, animations)

**Naming convention:** 1:1 mapping between markdown and HTML:
- `content/04-coordinator.md` → `04-coordinator.html`
- `content/02a-problem-multiagent.md` → `02a-problem-multiagent.html`

**Front matter schema:**
```yaml
---
id: coordinator       # Unique ID from slides.json
title: "Agent Coordinator"
subtitle: "The central brain"
accentColor: coordinator  # Optional: coordinator|runner|dashboard|session
parentId: problem     # Only for deep dives
---
```

**Editing workflow:**
1. Edit the markdown file in `content/`
2. Tell the AI: "I updated `content/04-coordinator.md`, please adjust the HTML"
3. AI reads markdown, updates `04-coordinator.html` accordingly

**Important:** The markdown may contain more detail than the HTML shows. It captures the message/ideas; the HTML is just one visual representation.

## Navigation System

Navigation is **decoupled** from individual slide files. All navigation is defined in `slides.json` and rendered dynamically by `navigation.js`.

### slides.json Structure
```json
{
  "mainFlow": [
    { "id": "orchestration", "file": "01-orchestration.html", "title": "Why Orchestration?", "icon": "🎭", "section": "intro" },
    { "id": "problem", "file": "02-problem.html", "title": "The Challenges", "icon": "❓", "section": "intro",
      "deepDives": [
        { "id": "multiagent", "file": "02a-problem-multiagent.html", "title": "Multi-Agent Coordination", "icon": "🔗" }
      ]
    }
  ],
  "sections": [
    { "id": "intro", "number": "1", "title": "Motivation & Problem", "colorClass": "section-intro" }
  ]
}
```

### How Navigation Works
- Each slide includes `<script src="navigation.js"></script>`
- `navigation.js` reads `slides.json`, detects current file, and renders prev/next/home buttons
- Deep dive links use `data-deep-dive="id"` attributes, filled in by JS
- `index.html` auto-generates all sections from `slides.json`

## Design System (from template.html)

### Colors - Always Use These Variables

```css
/* Backgrounds */
--color-bg: #0a0f1a;
--color-bg-card: #141b2d;

/* Component Colors - CRITICAL for consistency */
--color-coordinator: #3b82f6;  /* Blue - Agent Coordinator */
--color-runner: #10b981;       /* Green - Agent Runner */
--color-dashboard: #f59e0b;    /* Amber - Dashboard */
--color-session: #8b5cf6;      /* Purple - Sessions/Agents */
--color-executor: #ec4899;     /* Pink - Claude/Executor */
--color-capability: #22c55e;   /* Green - Capabilities */

/* Text */
--color-text: #f1f5f9;
--color-text-muted: #64748b;
--color-text-bright: #ffffff;

/* Borders */
--color-border: #1e293b;
--color-border-light: #334155;
```

### Component Rules

| Component | Color | Border Style |
|-----------|-------|--------------|
| Coordinator boxes | `#3b82f6` | `border: 2px solid` + glow shadow |
| Runner boxes | `#10b981` | `border: 2px solid` + glow shadow |
| Dashboard boxes | `#f59e0b` | `border: 2px solid` + glow shadow |
| Session/Agent | `#8b5cf6` | Rounded corners |
| Capabilities | `#22c55e` | Rounded corners |

### Typography

```css
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--font-mono: 'SF Mono', 'Fira Code', monospace;
```

- Slide titles: `clamp(2rem, 5vw, 3rem)`, bold, white
- Subtitles: `clamp(1rem, 2vw, 1.25rem)`, muted color
- Body: ~0.875rem

### Standard Slide Structure

Every slide follows this HTML structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SLIDE TITLE - Agent Orchestrator</title>
  <style>
    /* Include CSS variables and styles inline */
  </style>
</head>
<body>
  <div class="slide">
    <header class="slide-header">
      <h1>Slide Title</h1>
      <p class="subtitle">Brief description</p>
    </header>

    <main class="slide-content">
      <!-- Visual content here -->
    </main>

    <nav class="slide-nav">
      <!-- Navigation rendered by navigation.js -->
    </nav>
  </div>

  <script src="navigation.js"></script>
</body>
</html>
```

**Note:** Navigation is rendered dynamically. Do NOT add hardcoded prev/next links.

## How To: Common Tasks

### Edit Slide Content

1. Open the specific slide file (e.g., `07-dashboard.html`)
2. Find `<main class="slide-content">` - this contains the visual content
3. Keep the header and nav sections unchanged
4. Use existing CSS classes for consistency

### Add a New Slide

1. **Create the slide file** - Copy an existing slide with similar layout
2. **Edit `slides.json`** - Add entry to `mainFlow` array at the correct position:
   ```json
   { "id": "new-slide", "file": "NN-new-slide.html", "title": "New Slide Title", "icon": "🆕", "section": "components" }
   ```
3. **Update `totalSlides`** in `slides.json`
4. **Done!** - Navigation and index.html update automatically

### Remove a Slide

1. **Edit `slides.json`** - Remove the entry from `mainFlow` array
2. **Update `totalSlides`** in `slides.json`
3. **Delete the file**
4. **Done!** - No other files need updating

### Add a Deep Dive Slide (Out of Main Flow)

Deep dives are detail slides accessible via click but **not** in the arrow-key navigation.

**Naming:** `NNx-topic.html` where `NN` is parent slide number, `x` is letter (a, b, c...)

1. **Create the slide file** with standard structure (uses `navigation.js`)
2. **Edit `slides.json`** - Add to parent slide's `deepDives` array:
   ```json
   { "id": "topic", "file": "02d-topic.html", "title": "Topic Title", "icon": "🔍", "backLabel": "Back to Parent" }
   ```
3. **In parent slide** - Add clickable card with `data-deep-dive` attribute:
   ```html
   <a data-deep-dive="topic" class="card">Click for details</a>
   ```
4. **Done!** - `navigation.js` fills in the href and handles back navigation

### Rename a Slide File

1. **Rename the file** (e.g., `05-runner.html` → `05-agent-runner.html`)
2. **Edit `slides.json`** - Update the `file` property
3. **Done!** - All navigation updates automatically

### Reorder Slides

1. **Edit `slides.json`** - Move the entry to the new position in `mainFlow` array
2. **Done!** - Prev/next links and slide numbers update automatically

## Current Slide Order

| # | File | Section |
|---|------|---------|
| 1-2 | motivation-01-problem, motivation-02-vision | Vision & Goals |
| 3 | 03-solution | Solution Overview |
| 4-8 | 04-coordinator through 08-architecture | Core Components |
| 9-10 | 09-chat-overview, 10-chat-flow | First Chat |
| 11-14 | 17-blueprints through 20-capabilities-example | Blueprints & Capabilities |
| 15-22 | 15-orchestrator-capability through 17-resume | Multi-Agent Orchestration |
| 23 | 21-summary | Summary |

### Deep Dives (Out of Main Flow)

**Problem Deep Dives (under motivation-01-problem):**

| File | ID | Topic |
|------|-----|-------|
| 01-orchestration.html | agent-overload | Agent Overload |
| 02d-problem-infrastructure.html | infrastructure | Infrastructure Overhead |
| 02a-problem-multiagent.html | multiagent | Multi-Agent Coordination |
| 02b-problem-context.html | context-challenge | Context Sharing |
| 02e-problem-hybrid.html | hybrid-gap | AI-Program Gap |
| 02f-problem-accessibility.html | accessibility | Programmer Barrier |
| 02c-problem-provider.html | provider-lockin | Provider Lock-in |

**Vision Deep Dives (under motivation-02-vision):**

| File | ID | Topic |
|------|-----|-------|
| motivation-03-foundation.html | foundation | Reusable Foundation |
| motivation-04-refinement.html | refinement | Progressive Refinement |
| motivation-05-hybrid.html | hybrid | Hybrid Execution |
| motivation-06-interfaces.html | interfaces | Clean Interfaces |
| motivation-07-provider.html | provider | Provider Independence |
| motivation-08-collaboration.html | collaboration | Decentralized Collaboration |
| motivation-09-context.html | context | Context Engineering |
| motivation-10-accessibility.html | accessibility | Everyone Can Contribute |

## Visual Patterns Reference

For complex diagrams, look at these files as examples:
- **SVG architecture diagram:** `08-architecture.html`
- **Sequence diagram:** `10-chat-flow.html`
- **Timeline diagrams:** `12-mode-sync.html` through `15-mode-callback.html`
- **Comparison grid:** `16-modes-comparison.html`
- **Card layouts:** `03-solution.html`, `17-blueprints.html`

## Key CSS Patterns

**Glow effect for component boxes:**
```css
box-shadow: 0 0 30px rgba(59, 130, 246, 0.3); /* Use component color */
```

**Animated SVG arrows:**
```css
.arrow-animated {
  stroke-dasharray: 6 4;
  animation: flowArrow 1s linear infinite;
}
@keyframes flowArrow {
  to { stroke-dashoffset: -10; }
}
```

**Fade-in animation:**
```css
.element {
  opacity: 0;
  animation: fadeIn 0.4s ease forwards;
  animation-delay: 0.2s; /* Stagger for multiple elements */
}
@keyframes fadeIn {
  to { opacity: 1; }
}
```

---

**To get started:** Read `template.html` for the complete design system, then open the specific slide you want to edit.

## Serve Locally

A local HTTP server is required because navigation uses `fetch()` to load `slides.json`.

```bash
cd docs/slides && python -m http.server 8000
```

Then open http://localhost:8000/index.html
