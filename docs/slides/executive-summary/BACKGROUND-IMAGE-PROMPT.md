# Add Background Image to Slide

Use this prompt to add a background image to any executive summary slide with consistent styling.

---

## Prompt Template

```
Add a background image to the slide [SLIDE_FILE].

Use the image: [IMAGE_PATH]

Apply these exact CSS rules to the slide:

1. Add to the existing `<style>` section, at the TOP before other styles:

/* Background image styling */
.slide {
  position: relative;
}

.slide::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url('[IMAGE_PATH_RELATIVE]');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  opacity: 0.35;
  z-index: 0;
  /* Soft edge fade using mask */
  -webkit-mask-image: radial-gradient(
    ellipse 85% 80% at center,
    black 40%,
    transparent 100%
  );
  mask-image: radial-gradient(
    ellipse 85% 80% at center,
    black 40%,
    transparent 100%
  );
}

.slide-content {
  position: relative;
  z-index: 1;
}

2. The image path should be relative to the HTML file location (e.g., 'images/my-image.png')
```

---

## What Each Setting Does

| Property | Value | Purpose |
|----------|-------|---------|
| `opacity` | `0.35` | Keeps image subtle, doesn't overwhelm text content |
| `z-index: 0` | Background layer | Ensures image stays behind content |
| `z-index: 1` | Content layer | Ensures text/cards stay on top |
| `background-size: cover` | - | Image fills entire slide area |
| `background-position: center` | - | Image centered in viewport |
| `mask-image: radial-gradient(...)` | Ellipse 85% 80% | Soft fade at edges, blends into dark background |
| `black 40%` | - | Image fully visible in center 40% |
| `transparent 100%` | - | Completely faded at edges |

---

## Example Usage

**To add `closing_b.png` to `closing-b-cost.html`:**

```
Add a background image to the slide closing-b-cost.html.

Use the image: images/closing_b.png

Apply these exact CSS rules...
[paste the CSS from above]
```

---

## Adjustments (Optional)

| To Achieve | Change |
|------------|--------|
| More visible image | Increase `opacity` to `0.5` or `0.6` |
| Subtler image | Decrease `opacity` to `0.2` or `0.25` |
| Larger visible area | Change `black 40%` to `black 60%` |
| Smaller visible area | Change `black 40%` to `black 20%` |
| Wider fade | Change `ellipse 85% 80%` to `ellipse 95% 90%` |
| Tighter fade | Change `ellipse 85% 80%` to `ellipse 70% 65%` |

---

## File Locations

- **Slides:** `docs/slides/executive-summary/*.html`
- **Images:** `docs/slides/executive-summary/images/`
- **Image path in CSS:** Relative from HTML file, e.g., `images/filename.png`

---

## Quick Copy-Paste CSS Block

```css
/* Background image styling */
.slide {
  position: relative;
}

.slide::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: url('images/YOUR_IMAGE.png');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  opacity: 0.35;
  z-index: 0;
  -webkit-mask-image: radial-gradient(
    ellipse 85% 80% at center,
    black 40%,
    transparent 100%
  );
  mask-image: radial-gradient(
    ellipse 85% 80% at center,
    black 40%,
    transparent 100%
  );
}

.slide-content {
  position: relative;
  z-index: 1;
}
```

Replace `YOUR_IMAGE.png` with your actual image filename.
