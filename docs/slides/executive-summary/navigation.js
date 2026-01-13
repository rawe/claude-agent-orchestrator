/**
 * Slide Navigation System
 *
 * This script reads slides.json and dynamically builds navigation for each slide.
 * - Main flow slides get prev/next/home navigation
 * - Deep dive slides get back-to-parent navigation
 * - Handles keyboard navigation (arrows, Home, Escape)
 * - Fills in data-deep-dive links automatically
 */

(function() {
  'use strict';

  const SLIDES_JSON = 'slides.json';

  // Get current filename from URL
  function getCurrentFile() {
    return window.location.pathname.split('/').pop() || 'index.html';
  }

  // Find slide info in the navigation structure
  function findSlideInfo(slides, currentFile) {
    // Check main flow
    const mainIndex = slides.mainFlow.findIndex(s => s.file === currentFile);
    if (mainIndex !== -1) {
      return {
        type: 'main',
        index: mainIndex,
        slide: slides.mainFlow[mainIndex],
        prev: slides.mainFlow[mainIndex - 1] || null,
        next: slides.mainFlow[mainIndex + 1] || null,
        total: slides.totalSlides
      };
    }

    // Check deep dives
    for (const mainSlide of slides.mainFlow) {
      if (mainSlide.deepDives) {
        const deepDive = mainSlide.deepDives.find(d => d.file === currentFile);
        if (deepDive) {
          return {
            type: 'deepDive',
            slide: deepDive,
            parent: mainSlide
          };
        }
      }
    }

    return null;
  }

  // Render navigation for main flow slides
  function renderMainNav(container, info) {
    const prevDisabled = !info.prev ? 'disabled' : '';
    const nextDisabled = !info.next ? 'disabled' : '';
    const prevHref = info.prev ? info.prev.file : '#';
    const nextHref = info.next ? info.next.file : '#';

    container.innerHTML = `
      <a href="${prevHref}" class="nav-prev ${prevDisabled}" ${!info.prev ? 'tabindex="-1"' : ''}>&#8592;</a>
      <a href="index.html" class="nav-home">&#8962;</a>
      <span class="slide-number">${info.index + 1} / ${info.total}</span>
      <a href="${nextHref}" class="nav-next ${nextDisabled}" ${!info.next ? 'tabindex="-1"' : ''}>&#8594;</a>
    `;
  }

  // Render navigation for deep dive slides
  function renderDeepDiveNav(container, info) {
    const backLabel = info.slide.backLabel || `Back to ${info.parent.title}`;

    container.innerHTML = `
      <a href="${info.parent.file}" class="nav-back" title="Back to overview">&#8592;</a>
      <span class="nav-label">${backLabel}</span>
    `;
  }

  // Fill in data-deep-dive links
  function fillDeepDiveLinks(info) {
    if (info.type !== 'main' || !info.slide.deepDives) return;

    document.querySelectorAll('[data-deep-dive]').forEach(link => {
      const id = link.dataset.deepDive;
      const deepDive = info.slide.deepDives.find(d => d.id === id);
      if (deepDive) {
        link.href = deepDive.file;
      } else {
        console.warn(`Deep dive not found: "${id}" in slide "${info.slide.id}"`);
      }
    });
  }

  // Setup keyboard navigation
  function setupKeyboardNav(info) {
    document.addEventListener('keydown', (e) => {
      // Ignore if typing in an input
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (info.type === 'main') {
        if (e.key === 'ArrowLeft') {
          const prev = document.querySelector('.nav-prev:not(.disabled)');
          if (prev) prev.click();
        }
        if (e.key === 'ArrowRight') {
          const next = document.querySelector('.nav-next:not(.disabled)');
          if (next) next.click();
        }
        if (e.key === 'Home' || e.key === 'h') {
          const home = document.querySelector('.nav-home');
          if (home) home.click();
        }
      } else if (info.type === 'deepDive') {
        if (e.key === 'Escape' || e.key === 'ArrowLeft') {
          const back = document.querySelector('.nav-back');
          if (back) back.click();
        }
      }
    });
  }

  // Validate deep dive IDs are unique within their parent scope
  function validateDeepDiveIds(slides) {
    const errors = [];
    for (const slide of slides.mainFlow) {
      if (slide.deepDives) {
        const ids = slide.deepDives.map(d => d.id);
        const duplicates = ids.filter((id, i) => ids.indexOf(id) !== i);
        if (duplicates.length) {
          errors.push(`Duplicate deep dive IDs in "${slide.id}": ${duplicates.join(', ')}`);
        }
      }
    }
    if (errors.length) {
      console.error('Navigation validation errors:', errors);
    }
  }

  // Main initialization
  async function init() {
    try {
      const response = await fetch(SLIDES_JSON);
      if (!response.ok) throw new Error(`Failed to load ${SLIDES_JSON}`);

      const slides = await response.json();
      const currentFile = getCurrentFile();
      const info = findSlideInfo(slides, currentFile);

      if (!info) {
        console.warn(`Current file "${currentFile}" not found in slides.json`);
        return;
      }

      // Validate on load (dev helper)
      validateDeepDiveIds(slides);

      // Find nav container
      const navContainer = document.getElementById('slide-nav') ||
                          document.querySelector('.slide-nav');

      if (navContainer) {
        if (info.type === 'main') {
          renderMainNav(navContainer, info);
        } else {
          renderDeepDiveNav(navContainer, info);
        }
      }

      // Fill deep dive links
      fillDeepDiveLinks(info);

      // Setup keyboard
      setupKeyboardNav(info);

      // Expose for debugging
      window.__slideNav = { slides, currentFile, info };

    } catch (error) {
      console.error('Navigation init failed:', error);
    }
  }

  // Run when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
