# History Card Clipping Fix

## Problem

Transcript cards on the History page are capped at 50 pixels tall, so their
body text and actions are clipped. A shared theme selector applies compact-card
height limits to `#historyCard` along with quick-action and preference cards.

## Design

- Keep the shared surface, border, radius, and padding styles for all cards.
- Remove fixed minimum and maximum heights from the shared card selector.
- Scope compact height rules only to widgets that are intentionally compact.
- Let history cards use their layout-driven height so wrapped transcripts and
  the inline editor can expand naturally.

## Verification

- Add a Qt regression test that applies the application theme and confirms a
  populated transcript card is taller than 50 pixels.
- Run the focused History UI tests and the full test suite.
- Render the History page at the reported viewport and confirm the transcript
  text and action row are visible without clipping.

## Scope

This change fixes the erroneous theme constraint and adds regression coverage.
It does not redesign the History page or alter transcript data and behavior.
