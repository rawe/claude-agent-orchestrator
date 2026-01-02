# Agent Orchestrator Slides - Editor Context

You are editing an HTML slide presentation about the Agent Orchestrator framework. This document contains everything you need to make consistent edits.

## File Structure

```
docs/slides/
├── index.html          # Navigation hub - UPDATE when adding/removing slides
├── template.html       # Design system reference - READ for styling patterns
├── 01-problem.html     # ... through ...
└── 20-summary.html     # Individual slides
```

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
      <a href="PREV.html" class="nav-prev">←</a>
      <a href="index.html" class="nav-home">⌂</a>
      <span class="slide-number">N / 20</span>
      <a href="NEXT.html" class="nav-next">→</a>
    </nav>
  </div>

  <script>
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') document.querySelector('.nav-prev:not(.disabled)')?.click();
      if (e.key === 'ArrowRight') document.querySelector('.nav-next:not(.disabled)')?.click();
      if (e.key === 'Home' || e.key === 'h') document.querySelector('.nav-home')?.click();
    });
  </script>
</body>
</html>
```

## How To: Common Tasks

### Edit Slide Content

1. Open the specific slide file (e.g., `05-dashboard.html`)
2. Find `<main class="slide-content">` - this contains the visual content
3. Keep the header and nav sections unchanged
4. Use existing CSS classes for consistency

### Add a New Slide

1. **Create the slide file** - Copy an existing slide with similar layout
2. **Update navigation chain:**
   - In the new slide: set correct prev/next links
   - In the previous slide: update `nav-next` to point to new slide
   - In the next slide: update `nav-prev` to point to new slide
3. **Update slide numbers** - Update `slide-number` span in all affected slides (e.g., "N / 21")
4. **Update index.html** - Add the new slide card in the appropriate section

### Remove a Slide

1. **Fix navigation chain first:**
   - In the slide before: update `nav-next` to skip the removed slide
   - In the slide after: update `nav-prev` to skip the removed slide
2. **Update slide numbers** in all subsequent slides
3. **Update index.html** - Remove the slide card
4. **Delete the file**

### Update index.html

The index has sections like:
```html
<section class="section section-components">
  <div class="slides-grid">
    <a href="03-coordinator.html" class="slide-card">
      <div class="slide-card-icon">🧠</div>
      <div class="slide-card-number">Slide 03</div>
      <div class="slide-card-title">Agent Coordinator</div>
    </a>
    <!-- more cards -->
  </div>
</section>
```

To add a slide: add a new `<a class="slide-card">` block.
To remove: delete the corresponding card.

## Current Slide Order

| # | File | Section |
|---|------|---------|
| 1-2 | 01-problem, 02-solution | Problem & Solution |
| 3-6 | 03-coordinator through 06-architecture | Core Components |
| 7-8 | 07-chat-overview, 08-chat-flow | First Chat |
| 9-10 | 09-orchestration, 10-parent-child | Orchestration |
| 11-15 | 11-mode-sync through 15-modes-comparison | Execution Modes |
| 16-19 | 16-blueprints through 19-capabilities-example | Config System |
| 20 | 20-summary | Summary |

## Visual Patterns Reference

For complex diagrams, look at these files as examples:
- **SVG architecture diagram:** `06-architecture.html`
- **Sequence diagram:** `08-chat-flow.html`
- **Timeline diagrams:** `11-mode-sync.html` through `14-mode-callback.html`
- **Comparison grid:** `15-modes-comparison.html`
- **Card layouts:** `02-solution.html`, `16-blueprints.html`

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
