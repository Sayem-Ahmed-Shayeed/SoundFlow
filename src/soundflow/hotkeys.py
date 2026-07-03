from __future__ import annotations

import asyncio
import os
import secrets
import sys
import threading
from collections.abc import Callable
from typing import Any


class HotkeyError(RuntimeError):
    pass


def parse_hotkey(value: str) -> frozenset[str]:
    aliases = {
        "control": "ctrl",
        "ctl": "ctrl",
        "option": "alt",
        "super": "cmd",
        "win": "cmd",
        "windows": "cmd",
    }
    parts = [aliases.get(part.strip().lower(), part.strip().lower()) for part in value.split("+")]
    normalized = frozenset(part for part in parts if part)
    if len(normalized) != 2:
        raise ValueError("Push-to-talk must contain exactly two keys")
    return normalized


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
    }
    result = []
    for part in (piece.strip().lower() for piece in value.split("+")):
        result.append(modifiers.get(part, keys.get(part, part)))
    if len(result) != 2:
        raise ValueError("Push-to-talk must contain exactly two keys")
    return "+".join(result)


class GlobalHotkeys:
    """Keyboard listener used on Windows and Linux/X11."""

    def __init__(
        self,
        push_to_talk: str,
        on_ptt_down: Callable[[], None],
        on_ptt_up: Callable[[], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.binding = parse_hotkey(push_to_talk)
        self.on_ptt_down = on_ptt_down
        self.on_ptt_up = on_ptt_up
        self.on_error = on_error or (lambda message: None)
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
    ) -> None:
        self.trigger = portal_trigger(push_to_talk)
        self.on_ptt_down = on_ptt_down
        self.on_ptt_up = on_ptt_up
        self.on_error = on_error or (lambda message: None)
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._session_handle: str | None = None
        self._ready = threading.Event()

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
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.5)
        self._thread = None
        self._ready.clear()

    def wait_ready(self, timeout: float) -> bool:
        return self._ready.wait(timeout)

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
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
                            "push_to_talk",
                            {
                                "description": Variant(
                                    "s", "Hold to dictate with Soundflow"
                                ),
                                "preferred_trigger": Variant("s", self.trigger),
                            },
                        ]
                    ],
                    "",
                    {"handle_token": Variant("s", bind_token)},
                ],
            )
        )
        if reply.message_type == MessageType.ERROR:
            raise HotkeyError(reply.body[0])
        response, results = await asyncio.wait_for(bind_response, 60)
        if response != 0:
            raise HotkeyError("The desktop did not grant the push-to-talk shortcut")
        if not results.get("shortcuts"):
            raise HotkeyError("No push-to-talk shortcut was assigned")
        self._ready.set()

        def shortcut_handler(message) -> bool:
            if (
                message.message_type == MessageType.SIGNAL
                and message.interface == "org.freedesktop.portal.GlobalShortcuts"
                and len(message.body) >= 2
                and message.body[0] == self._session_handle
                and message.body[1] == "push_to_talk"
            ):
                if message.member == "Activated":
                    self.on_ptt_down()
                elif message.member == "Deactivated":
                    self.on_ptt_up()
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
        )
    return GlobalHotkeys(
        push_to_talk,
        on_ptt_down,
        on_ptt_up,
        on_error,
    )
