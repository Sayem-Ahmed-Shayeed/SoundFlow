"""UI widgets — small reusable components.

During the incremental migration these are mostly re-exports from the
legacy module. New widgets added by the redesign live directly in
files under this directory.
"""

from __future__ import annotations

# Re-export the widgets that still live in the legacy module.
from soundflow._legacy.ui_module import (  # type: ignore[attr-defined]
    ActionButton,
    AnimatedRecordButton,
    RecordingOverlay,
    ShortcutPicker,
    VoiceOrb,
    WaveformWidget,
)

# New widgets introduced by the redesign.
from soundflow.ui.widgets.compat import AppearanceSelector
from soundflow.ui.widgets.status_bar import StatusBar
from soundflow.ui.widgets.sidebar import AppSidebar
from soundflow.ui.widgets.top_tab_bar import TopTabBar
from soundflow.ui.widgets.toggle_switch import PreferenceToggleRow, ToggleSwitch
from soundflow.ui.widgets.waveform_ring import WaveformRing
from soundflow.ui.widgets.window_chrome import WindowChrome

__all__ = [
    "ActionButton",
    "AnimatedRecordButton",
    "AppearanceSelector",
    "AppSidebar",
    "RecordingOverlay",
    "PreferenceToggleRow",
    "ShortcutPicker",
    "StatusBar",
    "TopTabBar",
    "ToggleSwitch",
    "VoiceOrb",
    "WaveformRing",
    "WaveformWidget",
    "WindowChrome",
]  # type: ignore[assignment]  # re-export surface
