from __future__ import annotations

import asyncio
import logging
import os
import secrets
import sys
import threading
from collections.abc import Callable
from typing import Any

from soundflow.portal import register_host_app

LOGGER = logging.getLogger(__name__)


class HotkeyError(RuntimeError):
    pass


MODIFIERS = ("ctrl", "alt", "shift", "cmd")
MODIFIER_SET = frozenset(MODIFIERS)
KEY_ALIASES = {
    "control": "ctrl",
    "ctl": "ctrl",
    "option": "alt",
    "super": "cmd",
    "win": "cmd",
    "windows": "cmd",
    "return": "enter",
}
NAMED_TRIGGER_KEYS = frozenset(
    {"space", "enter", "tab", "escape", "backspace"}
    | {f"f{number}" for number in range(1, 13)}
)


def hotkey_parts(value: str) -> tuple[str, ...]:
    raw_parts = value.split("+")
    if any(not part.strip() for part in raw_parts):
        raise ValueError("Push-to-talk contains an empty key")
    parts = tuple(
        KEY_ALIASES.get(part.strip().lower(), part.strip().lower())
        for part in raw_parts
    )
    if len(parts) not in {2, 3}:
        raise ValueError("Push-to-talk must contain two or three keys")
    if len(set(parts)) != len(parts):
        raise ValueError("Push-to-talk cannot contain duplicate keys")
    modifiers = [part for part in parts if part in MODIFIER_SET]
    triggers = [part for part in parts if part not in MODIFIER_SET]
    if not modifiers:
        raise ValueError("Push-to-talk requires at least one modifier")
    if len(triggers) != 1:
        raise ValueError("Push-to-talk requires one non-modifier key")
    trigger = triggers[0]
    if not (
        trigger in NAMED_TRIGGER_KEYS
        or (len(trigger) == 1 and trigger.isalnum())
    ):
        raise ValueError(f"Unsupported push-to-talk key: {trigger}")
    ordered_modifiers = tuple(
        modifier for modifier in MODIFIERS if modifier in modifiers
    )
    return (*ordered_modifiers, trigger)


def canonical_hotkey(value: str) -> str:
    return "+".join(hotkey_parts(value))


_TRIGGER_NAMES = {
    "primary": "ctrl",
    "mod1": "alt",
    "meta": "cmd",
    "logo": "cmd",
    "mod4": "cmd",
    "kp_enter": "enter",
}


def hotkey_from_trigger(text: str | None) -> str | None:
    """Read the keys the desktop actually bound, e.g. "Ctrl+Space" or "<Control>z".

    The desktop's approval dialog lets people pick other keys than the ones
    Soundflow asked for; this turns its description back into a hotkey.
    Returns None when the text cannot be understood.
    """
    if not text:
        return None
    value = text.strip()
    # GTK accelerator form: <Control><Alt>space
    value = value.replace("<", "").replace(">", "+")
    parts = [part.strip() for part in value.split("+") if part.strip()]
    if not parts:
        return None
    # Drop any words before the first key ("Press Ctrl").
    parts[0] = parts[0].split()[-1]
    parts = [_TRIGGER_NAMES.get(part.lower(), part) for part in parts]
    try:
        return canonical_hotkey("+".join(parts))
    except ValueError:
        return None


def display_hotkey(value: str) -> str:
    labels = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "cmd": "Super"}
    def label(part: str) -> str:
        if part in labels:
            return labels[part]
        if len(part) == 1 or (part[:1] == "f" and part[1:].isdigit()):
            return part.upper()
        return part.capitalize()

    return " + ".join(label(part) for part in hotkey_parts(value))


def parse_hotkey(value: str) -> frozenset[str]:
    return frozenset(hotkey_parts(value))


def portal_trigger(value: str) -> str:
    modifiers = {
        "ctrl": "CTRL",
        "control": "CTRL",
        "alt": "ALT",
        "shift": "SHIFT",
        "cmd": "LOGO",
        "super": "LOGO",
        "win": "LOGO",
    }
    keys = {
        "space": "space",
        "enter": "Return",
        "return": "Return",
        "tab": "Tab",
        "escape": "Escape",
        "backspace": "BackSpace",
        **{f"f{number}": f"F{number}" for number in range(1, 13)},
    }
    result = [
        modifiers.get(part, keys.get(part, part))
        for part in hotkey_parts(value)
    ]
    return "+".join(result)


def portal_shortcut_id(value: str) -> str:
    """The name Soundflow registers its shortcut under with the desktop.

    The desktop remembers the keys it approved for a name and ignores any
    later "preferred" keys for that same name. So each key combination gets
    its own name: changing the shortcut in Preferences asks the desktop to
    approve the new keys instead of silently keeping the old ones. The
    default keeps the original name so existing approvals still apply.
    """
    canonical = canonical_hotkey(value)
    if canonical == canonical_hotkey("ctrl+alt+space"):
        return "push_to_talk"
    return "push_to_talk_" + canonical.replace("+", "_")


class GlobalHotkeys:
    """Keyboard listener used on Windows and Linux/X11."""

    def __init__(
        self,
        push_to_talk: str,
        on_ptt_down: Callable[[], None],
        on_ptt_up: Callable[[], None],
        on_error: Callable[[str], None] | None = None,
        on_ready: Callable[[str], None] | None = None,
    ) -> None:
        self.binding = parse_hotkey(push_to_talk)
        self.on_ptt_down = on_ptt_down
        self.on_ptt_up = on_ptt_up
        self.on_error = on_error or (lambda message: None)
        self.on_ready = on_ready or (lambda shortcut: None)
        self._pressed: set[str] = set()
        self._ptt_active = False
        self._listener: Any = None

    def start(self) -> None:
        try:
            from pynput import keyboard
        except ImportError as exc:
            raise HotkeyError("Global hotkeys require the pynput package") from exc
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()
            self.on_ready(display_hotkey("+".join(self.binding)))
        except Exception as exc:
            raise HotkeyError("Global push-to-talk could not start.") from exc

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None
        if self._ptt_active:
            self.on_ptt_up()
        self._pressed.clear()
        self._ptt_active = False

    def _on_press(self, key: Any) -> None:
        token = self._token(key)
        if not token:
            return
        self._pressed.add(token)
        if self.binding.issubset(self._pressed) and not self._ptt_active:
            self._ptt_active = True
            self.on_ptt_down()

    def _on_release(self, key: Any) -> None:
        token = self._token(key)
        if token:
            self._pressed.discard(token)
        if self._ptt_active and not self.binding.issubset(self._pressed):
            self._ptt_active = False
            self.on_ptt_up()

    @staticmethod
    def _token(key: Any) -> str | None:
        text = str(key).lower()
        if text.startswith("key."):
            text = text[4:]
        aliases = {
            "ctrl_l": "ctrl",
            "ctrl_r": "ctrl",
            "alt_l": "alt",
            "alt_r": "alt",
            "alt_gr": "alt",
            "shift_l": "shift",
            "shift_r": "shift",
            "cmd_l": "cmd",
            "cmd_r": "cmd",
            "' '": "space",
        }
        if text in aliases:
            return aliases[text]
        char = getattr(key, "char", None)
        if char:
            return str(char).lower()
        return text if text else None


class PortalGlobalHotkeys:
    """Wayland global push-to-talk via the XDG GlobalShortcuts portal."""

    SERVICE = "org.freedesktop.portal.Desktop"
    DESKTOP_PATH = "/org/freedesktop/portal/desktop"

    def __init__(
        self,
        push_to_talk: str,
        on_ptt_down: Callable[[], None],
        on_ptt_up: Callable[[], None],
        on_error: Callable[[str], None] | None = None,
        on_ready: Callable[[str], None] | None = None,
        parent_window: str = "",
        shortcut_id: str = "",
    ) -> None:
        self.trigger = portal_trigger(push_to_talk)
        self.shortcut_id = shortcut_id or portal_shortcut_id(push_to_talk)
        self.on_ptt_down = on_ptt_down
        self.on_ptt_up = on_ptt_up
        self.on_error = on_error or (lambda message: None)
        self.on_ready = on_ready or (lambda shortcut: None)
        # Called with the new trigger description when the person rebinds
        # the shortcut in the desktop's own settings.
        self.on_changed: Callable[[str], None] | None = None
        self.parent_window = parent_window
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._session_handle: str | None = None
        self._ready = threading.Event()
        self._state_lock = threading.Lock()
        self._ptt_active = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._thread_main,
            name="soundflow-wayland-shortcuts",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._release_active_shortcut()
        if self._loop and not self._loop.is_closed() and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.5)
        self._thread = None
        self._ready.clear()

    def wait_ready(self, timeout: float) -> bool:
        return self._ready.wait(timeout)

    def _handle_shortcut_event(
        self,
        member: str,
        session_handle: str,
        shortcut_id: str,
    ) -> None:
        if (
            session_handle != self._session_handle
            or shortcut_id != self.shortcut_id
        ):
            return

        callback: Callable[[], None] | None = None
        with self._state_lock:
            if member == "Activated" and not self._ptt_active:
                self._ptt_active = True
                callback = self.on_ptt_down
            elif member == "Deactivated" and self._ptt_active:
                self._ptt_active = False
                callback = self.on_ptt_up

        if callback is not None:
            LOGGER.info(
                "Global push-to-talk %s",
                "pressed" if member == "Activated" else "released",
            )
            callback()

    def _release_active_shortcut(self) -> None:
        callback: Callable[[], None] | None = None
        with self._state_lock:
            if self._ptt_active:
                self._ptt_active = False
                callback = self.on_ptt_up
        if callback is not None:
            LOGGER.info("Releasing active global push-to-talk during shutdown")
            callback()

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
            LOGGER.exception("Wayland global shortcut service stopped")
            self.on_error(f"Wayland push-to-talk could not start: {exc}")

    async def _run(self) -> None:
        try:
            from dbus_next import Message, MessageType, Variant
            from dbus_next.aio import MessageBus
        except ImportError as exc:
            raise HotkeyError("Wayland push-to-talk requires dbus-next") from exc

        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        bus = await MessageBus().connect()
        await register_host_app(bus)

        async def add_match(rule: str) -> None:
            reply = await bus.call(
                Message(
                    destination="org.freedesktop.DBus",
                    path="/org/freedesktop/DBus",
                    interface="org.freedesktop.DBus",
                    member="AddMatch",
                    signature="s",
                    body=[rule],
                )
            )
            if reply.message_type == MessageType.ERROR:
                raise HotkeyError(reply.body[0])

        await add_match(
            "type='signal',interface='org.freedesktop.portal.Request'"
        )
        await add_match(
            "type='signal',interface='org.freedesktop.portal.GlobalShortcuts'"
        )

        def request_future(token: str) -> asyncio.Future:
            future = self._loop.create_future()

            def handler(message) -> bool:
                if (
                    message.message_type == MessageType.SIGNAL
                    and message.interface == "org.freedesktop.portal.Request"
                    and message.member == "Response"
                    and message.path
                    and message.path.endswith("/" + token)
                    and not future.done()
                ):
                    response, results = message.body
                    self._loop.call_soon_threadsafe(
                        future.set_result, (int(response), results)
                    )
                return False

            bus.add_message_handler(handler)
            return future

        create_token = "soundflow_create_" + secrets.token_hex(6)
        create_response = request_future(create_token)
        reply = await bus.call(
            Message(
                destination=self.SERVICE,
                path=self.DESKTOP_PATH,
                interface="org.freedesktop.portal.GlobalShortcuts",
                member="CreateSession",
                signature="a{sv}",
                body=[
                    {
                        "handle_token": Variant("s", create_token),
                        "session_handle_token": Variant(
                            "s", "soundflow_session_" + secrets.token_hex(6)
                        ),
                    }
                ],
            )
        )
        if reply.message_type == MessageType.ERROR:
            raise HotkeyError(reply.body[0])
        response, results = await asyncio.wait_for(create_response, 15)
        if response != 0:
            raise HotkeyError("The desktop declined the shortcut session")
        self._session_handle = results["session_handle"].value

        bind_token = "soundflow_bind_" + secrets.token_hex(6)
        bind_response = request_future(bind_token)
        reply = await bus.call(
            Message(
                destination=self.SERVICE,
                path=self.DESKTOP_PATH,
                interface="org.freedesktop.portal.GlobalShortcuts",
                member="BindShortcuts",
                signature="oa(sa{sv})sa{sv}",
                body=[
                    self._session_handle,
                    [
                        [
                            self.shortcut_id,
                            {
                                "description": Variant(
                                    "s", "Hold to dictate with Soundflow"
                                ),
                                "preferred_trigger": Variant("s", self.trigger),
                            },
                        ]
                    ],
                    self.parent_window,
                    {"handle_token": Variant("s", bind_token)},
                ],
            )
        )
        if reply.message_type == MessageType.ERROR:
            raise HotkeyError(reply.body[0])
        response, results = await asyncio.wait_for(bind_response, 60)
        if response != 0:
            raise HotkeyError("The desktop did not grant the push-to-talk shortcut")
        shortcut_result = results.get("shortcuts")
        shortcuts = getattr(shortcut_result, "value", shortcut_result)
        if not shortcuts:
            raise HotkeyError("No push-to-talk shortcut was assigned")
        assigned = shortcuts[0][1]
        description = assigned.get("trigger_description")
        display_shortcut = (
            description.value
            if description is not None
            else self.trigger.replace("+", " + ")
        )
        self._ready.set()
        LOGGER.info("Global push-to-talk ready: %s", display_shortcut)
        self.on_ready(display_shortcut)

        def shortcut_handler(message) -> bool:
            if (
                message.message_type == MessageType.SIGNAL
                and message.interface == "org.freedesktop.portal.GlobalShortcuts"
                and message.member == "ShortcutsChanged"
                and len(message.body) >= 2
                and message.body[0] == self._session_handle
            ):
                for shortcut_id, props in message.body[1]:
                    if shortcut_id != self.shortcut_id:
                        continue
                    changed = props.get("trigger_description")
                    callback = self.on_changed
                    if changed is not None and callback is not None:
                        LOGGER.info("Global push-to-talk rebound: %s", changed.value)
                        callback(changed.value)
                return False
            if (
                message.message_type == MessageType.SIGNAL
                and message.interface == "org.freedesktop.portal.GlobalShortcuts"
                and len(message.body) >= 2
                and message.body[0] == self._session_handle
                and message.body[1] == self.shortcut_id
            ):
                self._handle_shortcut_event(
                    message.member,
                    message.body[0],
                    message.body[1],
                )
            return False

        bus.add_message_handler(shortcut_handler)

        await self._stop_event.wait()
        if self._session_handle:
            try:
                await bus.call(
                    Message(
                        destination=self.SERVICE,
                        path=self._session_handle,
                        interface="org.freedesktop.portal.Session",
                        member="Close",
                    )
                )
            except Exception:
                pass
        bus.disconnect()


def create_global_hotkeys(
    push_to_talk: str,
    on_ptt_down: Callable[[], None],
    on_ptt_up: Callable[[], None],
    on_error: Callable[[str], None] | None = None,
    on_ready: Callable[[str], None] | None = None,
    parent_window: str = "",
    shortcut_id: str = "",
):
    if (
        sys.platform.startswith("linux")
        and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    ):
        return PortalGlobalHotkeys(
            push_to_talk,
            on_ptt_down,
            on_ptt_up,
            on_error,
            on_ready,
            parent_window,
            shortcut_id,
        )
    return GlobalHotkeys(
        push_to_talk,
        on_ptt_down,
        on_ptt_up,
        on_error,
        on_ready,
    )
