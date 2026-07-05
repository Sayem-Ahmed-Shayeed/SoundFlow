# System Tab Redesign

## Goal

Turn Preferences > System into a useful local-readiness dashboard without
changing Soundflow's runtime, permissions, model, or data-folder behavior.

## Layout

The page uses two stacked `preferencesCard` surfaces. The first is a System
readiness card with a title, explanatory copy, an overall state pill, five
scannable diagnostic rows, the model location, and a compact Run system check
button. The second is a Local data card with explanatory copy, the application
data path, and a compact Open data folder button.

The readiness rows are Model files, Microphone, Global shortcut, Text
insertion, and Processing device. Before a check they show neutral values.
After a check they show clear ready, setup-required, unavailable, or fallback
states derived only from `SystemCheckResult`.

## Behavior

`run_system_check()` remains read-only. `open_data_folder()` remains the only
data-folder action. Long paths wrap and remain selectable. The page stays a
single column at every supported size, and no removed About panel returns.

## Visual Direction

Reuse the current Soundflow spacing, typography, surface, border, status, and
button tokens. Diagnostic rows use subtle raised surfaces, small colored state
dots, and short labels. Buttons keep their natural width instead of stretching
across the card.

## Verification

Qt tests cover the visible structure and readiness-state update. Existing
system-check tests continue to cover model, microphone, permission, and CPU
fallback logic. The complete relevant test set and packaged smoke test must
pass before reinstalling.
