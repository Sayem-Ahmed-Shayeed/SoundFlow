# Geist Typography and Motion Design

## Goal

Give Soundflow a sharper, more professional typographic identity and add restrained micro-interactions that clarify state changes without distracting from dictation.

## Typography

Soundflow will replace its bundled Roboto family with the official Geist family:

```text
SOUNDFLOW TYPOGRAPHY
│
├── Page title ........ Geist Sans · 25–32px · 700
├── Section title ..... Geist Sans · 16–22px · 600–700
├── Control label ..... Geist Sans · 13–14px · 600
├── Body text ......... Geist Sans · 14px · 400
├── Supporting text ... Geist Sans · 11–12px · 400
└── Technical values .. Geist Mono · 10–12px · 500
    ├── Shortcuts
    ├── Directory paths
    ├── Model sizes
    └── Download progress
```

The application bundles official Geist Sans and Geist Mono font files and the upstream SIL Open Font License. Runtime font registration must succeed without requiring system installation. `DISPLAY_FONT` and `BODY_FONT` resolve to Geist Sans, while `MONO_FONT` resolves to the bundled Geist Mono family.

Ordinary interface text remains proportional. Geist Mono is limited to technical values where fixed-width alignment or visual distinction improves scanning. Existing font-size tokens remain the source of truth; this change corrects family, weight, and hierarchy rather than globally enlarging the interface.

Roboto font binaries and their license file are removed after Geist registration and packaging tests prove they are no longer referenced.

## Motion Language

Motion stays short, interruptible, and functional:

```text
USER ACTION
    │
    ├── Navigation ───── 200 ms fade · OutCubic
    ├── Toggle ───────── 160 ms thumb glide · OutCubic
    ├── Button press ─── 120 ms feedback · OutCubic
    ├── Progress update  160 ms interpolation · OutCubic
    └── New status ───── 200 ms soft fade-in · OutCubic
```

The existing navigation fade, dictation-state fade, and active-status pulse establish the animation vocabulary. Their timing remains based on `ANIMATION_FAST`, `ANIMATION_NORMAL`, and `ANIMATION_SLOW`.

### Toggle Motion

`ToggleSwitch` exposes a floating-point thumb-position property. Toggling starts a 160 ms `QPropertyAnimation` from the current position to the checked or unchecked endpoint. A rapid second toggle stops the current animation and continues from the visible position, avoiding jumps. Native checkbox semantics, keyboard input, focus drawing, accessible names, and checked-state signals remain unchanged.

### Button Feedback

Push buttons retain their immediate pressed stylesheet state. A shared event-filter helper adds a brief 120 ms opacity recovery after mouse or keyboard activation. It operates only on enabled `QPushButton` instances, never delays the click signal, stops an earlier animation before restarting, and removes its temporary graphics effect at completion.

The helper is installed once at application startup and owns all temporary animation objects. It does not alter button subclasses or their business logic.

### Progress Motion

Determinate Whisper model download updates interpolate from the current bar value to the newest fill value over 160 ms. The visible `downloaded MB / total MB` text updates immediately so reported bytes are always current. A new update stops the prior interpolation and continues from the visible fill.

Indeterminate, Preparing, Verifying, completion, cancellation, and error transitions stop any active value animation before changing range or hiding the bar. Progress animation must not change byte accounting or download behavior.

### Status Motion

Existing status and page fades are retained. A status message that changes fades from reduced opacity to fully visible over 200 ms. Repeated state changes restart from the current opacity, and the existing recording pulse remains the only looping opacity animation.

## Architecture

- `soundflow.design.fonts` owns bundled font registration and family constants.
- `soundflow.design.spacing` remains the source for animation durations.
- `soundflow.design.motion` owns shared button feedback so application pages do not duplicate event handling.
- `ToggleSwitch` owns its thumb animation because it owns thumb painting.
- `ModelManagerWidget` owns model progress animations because it owns model-row lifecycle.
- `StatusBar` owns message fade behavior because it owns persistent status state.

No third-party animation dependency is added; all motion uses PySide6 `QPropertyAnimation`, `QVariantAnimation`, easing curves, and graphics effects.

## Reliability and Accessibility

- Animations never gate commands, persistence, navigation, cancellation, or downloads.
- Every animation can be stopped safely during rapid input or widget destruction.
- Final values are set explicitly at animation completion.
- Disabled controls do not animate.
- Focus indicators and keyboard behavior remain visible and native.
- No animated backgrounds, bouncing, large translations, or decorative motion are introduced.
- The application remains usable if animations are interrupted or never receive a final frame.

## Testing

Typography tests verify:

- both Geist families register successfully;
- display, body, and mono constants use the expected bundled families;
- Roboto is no longer bundled or referenced;
- packaging includes Geist font files and the SIL license; and
- screenshots render the intended hierarchy in light and dark modes.

Motion tests verify:

- toggle duration, easing, endpoints, keyboard behavior, and interruption;
- button feedback duration, click delivery, disabled behavior, and effect cleanup;
- progress duration, immediate MB text, newest-value wins, unknown-total behavior, and cleanup;
- status fade duration, final opacity, interrupted updates, and non-looping behavior; and
- existing navigation and recording animation contracts remain intact.

After focused tests, every non-audio test module must pass. The PyInstaller application is rebuilt, freshly uninstalled and installed, checked for an enabled and active user service, compared by executable hash, and visually reviewed in light and dark themes.

## Out of Scope

- Animated backgrounds or decorative particles.
- Large page slides, bounce easing, or motion longer than 320 ms.
- Redesigning spacing, colors, controls, or navigation structure.
- Download-speed or time-remaining animation.
- A user-facing animation preference in this iteration.
