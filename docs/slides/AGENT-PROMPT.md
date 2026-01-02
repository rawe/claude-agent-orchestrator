# Agent Orchestrator Slide Deck - Implementation Prompt

## Context

You are creating an interactive HTML slide deck for the Agent Orchestrator framework. The presentation introduces the system progressively, from basic concepts to advanced orchestration patterns.

**Reference Document:** Read `docs/presentation-plan.md` for the complete content outline. This document defines 8 sections with specific content for each slide.

## Objective

Create a professional, visually-driven HTML slide presentation where:
- Each slide is a standalone HTML file
- Navigation connects all slides
- Diagrams and visuals dominate over text
- Design is consistent across all slides

## Technical Requirements

### File Structure

```
docs/slides/
├── AGENT-PROMPT.md          # This file (instructions)
├── template.html            # Base template with CSS design system
├── index.html               # Navigation hub / table of contents
├── 01-problem.html          # Section 1: The Problem
├── 02-solution.html         # Section 1: The Solution
├── 03-coordinator.html      # Section 2: Agent Coordinator
├── 04-runner.html           # Section 2: Agent Runner
├── 05-dashboard.html        # Section 2: Dashboard
├── 06-architecture.html     # Section 2: Three components together
├── 07-chat-overview.html    # Section 3: Chat introduction
├── 08-chat-flow.html        # Section 3: Message flow diagram
├── 09-orchestration.html    # Section 4: Why orchestration
├── 10-parent-child.html     # Section 4: Parent-child agents
├── 11-mode-sync.html        # Section 5: Synchronous mode
├── 12-mode-polling.html     # Section 5: Async with polling
├── 13-mode-fire-forget.html # Section 5: Fire and forget
├── 14-mode-callback.html    # Section 5: Callback mode
├── 15-modes-comparison.html # Section 5: All modes side-by-side
├── 16-blueprints.html       # Section 6: Agent Blueprints
├── 17-capabilities-problem.html  # Section 7: The copy-paste problem
├── 18-capabilities-solution.html # Section 7: Capabilities concept
├── 19-capabilities-example.html  # Section 7: Neo4j example
├── 20-summary.html          # Section 8: Full picture
└── assets/
    └── (optional shared assets)
```

### Design System (define in template.html)

**Color Palette:**
```css
--color-bg: #0f172a;           /* Deep navy background */
--color-bg-card: #1e293b;      /* Slightly lighter for cards */
--color-primary: #3b82f6;      /* Blue - Coordinator */
--color-secondary: #10b981;    /* Green - Runner */
--color-accent: #f59e0b;       /* Amber - Dashboard */
--color-purple: #8b5cf6;       /* Purple - Sessions/Agents */
--color-text: #f8fafc;         /* White text */
--color-text-muted: #94a3b8;   /* Gray text */
--color-border: #334155;       /* Subtle borders */
```

**Component Consistency:**
- Coordinator: Always blue (#3b82f6), rounded rectangle
- Runner: Always green (#10b981), hexagon or rounded rectangle
- Dashboard: Always amber (#f59e0b), rounded rectangle
- Sessions: Always purple (#8b5cf6), circles
- Arrows: White or gray, with animation hints
- Boxes: Rounded corners (8-12px), subtle shadows

**Typography:**
- Use system fonts: `-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- Slide titles: Large (2.5-3rem), bold, white
- Subtitles: Medium (1.25rem), muted color
- Body text: Minimal, large enough to read (1.1rem)
- Code/technical: Monospace font

**Layout Principles:**
- Each slide: Full viewport (100vw x 100vh)
- Content centered both horizontally and vertically
- Maximum 3-4 visual elements per slide
- Text should be 30% or less of slide content
- Diagrams/visuals should dominate

### Navigation

Each slide must include:
- Previous/Next arrows (keyboard support: ArrowLeft, ArrowRight)
- Slide number indicator (e.g., "5 / 20")
- Home button (returns to index.html)
- Consistent position (bottom of slide)

### Visual Elements

**Diagrams must be created using:**
- Inline SVG (preferred - scales perfectly)
- CSS shapes and flexbox/grid layouts
- CSS animations for flow/movement indication

**Required diagram types:**
1. Box diagrams (components with labels)
2. Flow diagrams (arrows showing data/control flow)
3. Sequence diagrams (vertical timeline with horizontal arrows)
4. Comparison layouts (side-by-side columns)
5. Tree diagrams (parent-child relationships)

**Animation guidelines:**
- Subtle pulse on key elements (draw attention)
- Arrow animations showing direction (dash-offset animation)
- Fade-in on page load (opacity transition)
- No distracting or continuous animations

---

## Subtask Breakdown

Execute these subtasks in order. Some can run in parallel as indicated.

### Subtask 1: Foundation (Sequential - Do First)

**Create the design system and template.**

Files to create:
- `template.html` - Complete HTML template with:
  - Full CSS design system (colors, typography, components)
  - Navigation component (prev/next/home)
  - Keyboard navigation JavaScript
  - Reusable SVG component patterns (boxes, arrows)
  - Slide structure (header, main content area, footer nav)

- `index.html` - Table of contents with:
  - Project title and brief description
  - Visual section groupings
  - Links to all slides
  - Section icons/colors matching content

**Acceptance criteria:**
- Template renders correctly in browser
- Navigation works (keyboard + click)
- Colors and typography are defined
- Index shows all 20 slides organized by section

---

### Subtask 2: Problem & Core Components (Can parallelize after Subtask 1)

**Slides 01-06: Introduction and Architecture**

Create these slides following the template:

| File | Content | Primary Visual |
|------|---------|----------------|
| `01-problem.html` | Single agent limitations | Icon showing one box with limitations listed around it |
| `02-solution.html` | Three-part solution | Three colored boxes (Coordinator, Runner, Dashboard) |
| `03-coordinator.html` | Agent Coordinator deep dive | Blue box with internal components (Sessions, Runs, Blueprints) |
| `04-runner.html` | Agent Runner deep dive | Green box showing poll→execute→report cycle |
| `05-dashboard.html` | Dashboard deep dive | Amber box showing monitoring features |
| `06-architecture.html` | Full architecture | All three components with connection arrows |

**Visual emphasis:** Use the color-coded boxes consistently. Show relationships with arrows.

---

### Subtask 3: First Chat Walkthrough (Can parallelize after Subtask 1)

**Slides 07-08: Basic Usage**

| File | Content | Primary Visual |
|------|---------|----------------|
| `07-chat-overview.html` | What happens in a simple chat | Simple flow: User → Dashboard → Agent → Response |
| `08-chat-flow.html` | Detailed sequence diagram | Vertical sequence: Dashboard → Coordinator → Runner → Executor → back |

**Visual emphasis:** Sequence diagram showing the complete message lifecycle with numbered steps.

---

### Subtask 4: Orchestration Concept (Can parallelize after Subtask 1)

**Slides 09-10: Multi-Agent Orchestration**

| File | Content | Primary Visual |
|------|---------|----------------|
| `09-orchestration.html` | Why agents need to start agents | Split view: simple task (one agent) vs complex task (many agents) |
| `10-parent-child.html` | Parent-child relationship | Tree diagram: parent at top, 2-3 children below, MCP server in middle |

**Visual emphasis:** Tree structure, show the MCP server as the "bridge" enabling orchestration.

---

### Subtask 5: Execution Modes (Can parallelize after Subtask 1)

**Slides 11-15: The Four Patterns**

| File | Content | Primary Visual |
|------|---------|----------------|
| `11-mode-sync.html` | Synchronous execution | Timeline: Parent blocked (gray), Child working (green), Parent resumes |
| `12-mode-polling.html` | Async with polling | Timeline: Parent working + polling arrows, Child working in parallel |
| `13-mode-fire-forget.html` | Fire and forget | Timeline: Parent fires arrow and continues, Child works independently |
| `14-mode-callback.html` | Callback mode | Timeline: Parent working, Child completes → callback arrow → Parent notified |
| `15-modes-comparison.html` | All four compared | Four-column layout with mini timelines side by side |

**Visual emphasis:** Timeline diagrams are critical here. Use horizontal time axis, show blocking vs non-blocking clearly with color coding.

---

### Subtask 6: Blueprints & Capabilities (Can parallelize after Subtask 1)

**Slides 16-19: Configuration System**

| File | Content | Primary Visual |
|------|---------|----------------|
| `16-blueprints.html` | What is a blueprint | Blueprint "card" showing: name, system prompt, MCP config, metadata |
| `17-capabilities-problem.html` | The copy-paste problem | Multiple blueprints with duplicate config sections highlighted in red |
| `18-capabilities-solution.html` | Capabilities concept | Blueprint + Capability boxes → merged result (visual merge animation) |
| `19-capabilities-example.html` | Neo4j knowledge graph | Specific example: capability card with Neo4j config, multiple agents referencing it |

**Visual emphasis:** Show the before/after of capabilities. The merge diagram is key.

---

### Subtask 7: Summary (After all others complete)

**Slide 20: Putting It All Together**

| File | Content | Primary Visual |
|------|---------|----------------|
| `20-summary.html` | Complete system overview | Full architecture diagram with all concepts: Coordinator, Runners, Agents, Sessions, Capabilities, execution modes indicated |

**Visual emphasis:** This is the "hero" diagram. It should be the most detailed but still readable. Consider using hover states to highlight different parts.

---

## Quality Checklist

Before considering complete, verify:

- [ ] All 20 slides + index.html created
- [ ] Navigation works on all slides (keyboard + click)
- [ ] Colors consistent (Coordinator=blue, Runner=green, Dashboard=amber)
- [ ] Each slide has a dominant visual element (not text-heavy)
- [ ] SVG diagrams scale properly on different screen sizes
- [ ] Slide numbers accurate
- [ ] Previous disabled on first slide, Next disabled on last slide
- [ ] Index.html links to all slides correctly
- [ ] No external dependencies (everything inline or local)

---

## Example Code Patterns

### Basic Slide Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Slide Title - Agent Orchestrator</title>
  <style>
    /* Include full design system or link to shared CSS */
  </style>
</head>
<body>
  <div class="slide">
    <header>
      <h1>Slide Title</h1>
      <p class="subtitle">Brief context</p>
    </header>

    <main>
      <!-- Primary visual content here -->
      <svg>...</svg>
    </main>

    <nav class="slide-nav">
      <a href="previous.html" class="nav-prev">←</a>
      <span class="slide-number">5 / 20</span>
      <a href="index.html" class="nav-home">☰</a>
      <a href="next.html" class="nav-next">→</a>
    </nav>
  </div>

  <script>
    document.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') document.querySelector('.nav-prev')?.click();
      if (e.key === 'ArrowRight') document.querySelector('.nav-next')?.click();
    });
  </script>
</body>
</html>
```

### SVG Box Component Pattern
```svg
<svg viewBox="0 0 200 100">
  <!-- Coordinator box (blue) -->
  <rect x="10" y="10" width="180" height="80" rx="8"
        fill="#1e293b" stroke="#3b82f6" stroke-width="2"/>
  <text x="100" y="55" text-anchor="middle" fill="#f8fafc" font-size="16">
    Agent Coordinator
  </text>
</svg>
```

### Animated Arrow Pattern
```css
.arrow-animated {
  stroke-dasharray: 5;
  animation: flow 1s linear infinite;
}
@keyframes flow {
  to { stroke-dashoffset: -10; }
}
```

---

## Final Notes

- Prioritize visual clarity over completeness
- If a diagram is complex, simplify rather than cram
- Each slide should communicate ONE main idea
- Test in browser frequently during development
- The presentation should be self-explanatory without a presenter
