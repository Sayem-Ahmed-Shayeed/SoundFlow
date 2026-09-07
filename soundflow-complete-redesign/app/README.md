# Soundflow — Luxury Minimalist Redesign

A complete, self-contained front-end redesign of the Soundflow UI shown in the supplied screenshots.

## Included pages and states

- Dictation — idle and active recording states
- History — search, filter, edit, copy, polish, delete
- Playground — Insert Text, Format Text, Smart Rewrite templates and preview
- Preferences
  - General
  - Dictation / local recognition models
  - Playback
  - Shortcuts
  - AI Polish
  - System readiness
- Responsive desktop, tablet, and mobile navigation
- Keyboard focus states and reduced-motion support
- Loading, ready, disabled, success, warning, and modal states

## Run

No build step or dependencies are required.

Option 1: Open `index.html` directly in a modern browser.

Option 2: Run a local static server:

```bash
python -m http.server 8080
```

Then open `http://localhost:8080`.

## Notes

The source project/business logic was not included with the screenshots, so this package is a standalone UI implementation that preserves and recreates the observable product flows. The transcription, OS-level shortcut, text insertion, Whisper model downloads, and external AI-provider calls are represented by polished interactive front-end states rather than native/system integrations.

The project intentionally has no external font, icon, framework, or CDN dependency. It uses system typefaces, inline SVG iconography, CSS, and vanilla JavaScript so it can run offline.
