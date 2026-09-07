from __future__ import annotations

import asyncio
import os
import secrets
import sys
import threading
import time
from collections.abc import Callable

from soundflow.portal import register_host_app


class InjectionError(RuntimeError):
    pass


class TextInjector:
    def __init__(self, on_ready: Callable[[], None] | None = None) -> None:
        self.on_ready = on_ready or (lambda: None)

    def start(self) -> None:
        self.on_ready()

    def paste(self, shift: bool = False) -> None:
        paste_from_clipboard(shift=shift)

    def stop(self) -> None:
        pass


class PortalTextInjector(TextInjector):
    """Wayland keyboard injection through a user-approved RemoteDesktop session."""

    SERVICE = "org.freedesktop.portal.Desktop"
    DESKTOP_PATH = "/org/freedesktop/portal/desktop"

    def __init__(
        self,
        restore_token: str,
        on_restore_token: Callable[[str], None],
        on_error: Callable[[str], None],
        on_ready: Callable[[], None],
        parent_window: str = "",
    ) -> None:
        self.restore_token = restore_token
        self.on_restore_token = on_restore_token
        self.on_error = on_error
        self.on_ready = on_ready
        self.parent_window = parent_window
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._commands: asyncio.Queue | None = None
        self._ready = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._thread_main,
            name="soundflow-wayland-injector",
            daemon=True,
        )
        self._thread.start()

    def paste(self, shift: bool = False) -> None:
        if not self._ready.is_set() or not self._loop or not self._commands:
            raise InjectionError(
                "Wayland paste permission is not ready. The text is on your clipboard."
            )
        command = "paste-shift" if shift else "paste"
        self._loop.call_soon_threadsafe(self._commands.put_nowait, command)

    def stop(self) -> None:
        if self._loop and not self._loop.is_closed() and self._commands:
            self._loop.call_soon_threadsafe(self._commands.put_nowait, "stop")
        if self._thread and self._thread is not threading.current_thread():
            self._thread.join(timeout=1.5)
        self._thread = None

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._run())
        except Exception as exc:
            self.on_error(f"Wayland auto-paste unavailable: {exc}")

    async def _run(self) -> None:
        from dbus_next import Message, MessageType, Variant
        from dbus_next.aio import MessageBus

        self._loop = asyncio.get_running_loop()
        self._commands = asyncio.Queue()
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
                raise InjectionError(reply.body[0])

        await add_match("type='signal',interface='org.freedesktop.portal.Request'")

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

        create_token = "soundflow_remote_create_" + secrets.token_hex(5)
        response_future = request_future(create_token)
        reply = await bus.call(
            Message(
                destination=self.SERVICE,
                path=self.DESKTOP_PATH,
                interface="org.freedesktop.portal.RemoteDesktop",
                member="CreateSession",
                signature="a{sv}",
                body=[
                    {
                        "handle_token": Variant("s", create_token),
                        "session_handle_token": Variant(
                            "s", "soundflow_remote_session_" + secrets.token_hex(5)
                        ),
                    }
                ],
            )
        )
        if reply.message_type == MessageType.ERROR:
            raise InjectionError(reply.body[0])
        response, results = await asyncio.wait_for(response_future, 20)
        if response != 0:
            raise InjectionError("keyboard-control permission was declined")
        session_handle = results["session_handle"].value

        select_token = "soundflow_remote_select_" + secrets.token_hex(5)
        response_future = request_future(select_token)
        select_options = {
            "handle_token": Variant("s", select_token),
            "types": Variant("u", 1),  # keyboard
            "persist_mode": Variant("u", 2),
        }
        if self.restore_token:
            select_options["restore_token"] = Variant("s", self.restore_token)
        reply = await bus.call(
            Message(
                destination=self.SERVICE,
                path=self.DESKTOP_PATH,
                interface="org.freedesktop.portal.RemoteDesktop",
                member="SelectDevices",
                signature="oa{sv}",
                body=[session_handle, select_options],
            )
        )
        if reply.message_type == MessageType.ERROR:
            raise InjectionError(reply.body[0])
        response, _ = await asyncio.wait_for(response_future, 30)
        if response != 0:
            raise InjectionError("keyboard-control permission was declined")

        start_token = "soundflow_remote_start_" + secrets.token_hex(5)
        response_future = request_future(start_token)
        reply = await bus.call(
            Message(
                destination=self.SERVICE,
                path=self.DESKTOP_PATH,
                interface="org.freedesktop.portal.RemoteDesktop",
                member="Start",
                signature="osa{sv}",
                body=[
                    session_handle,
                    self.parent_window,
                    {"handle_token": Variant("s", start_token)},
                ],
            )
        )
        if reply.message_type == MessageType.ERROR:
            raise InjectionError(reply.body[0])
        response, results = await asyncio.wait_for(response_future, 60)
        if response != 0:
            raise InjectionError("keyboard-control permission was declined")
        if "restore_token" in results:
            self.on_restore_token(results["restore_token"].value)
        self._ready.set()
        self.on_ready()

        while True:
            command = await self._commands.get()
            if command == "stop":
                break
            if command in ("paste", "paste-shift"):
                # XKB keysyms: Control_L, optional Shift_L, and lowercase v.
                sequence = [(0xFFE3, 1)]
                if command == "paste-shift":
                    sequence.append((0xFFE1, 1))
                sequence.append((0x0076, 1))
                sequence.append((0x0076, 0))
                if command == "paste-shift":
                    sequence.append((0xFFE1, 0))
                sequence.append((0xFFE3, 0))
                for keysym, state in sequence:
                    reply = await bus.call(
                        Message(
                            destination=self.SERVICE,
                            path=self.DESKTOP_PATH,
                            interface="org.freedesktop.portal.RemoteDesktop",
                            member="NotifyKeyboardKeysym",
                            signature="oa{sv}iu",
                            body=[session_handle, {}, keysym, state],
                        )
                    )
                    if reply.message_type == MessageType.ERROR:
                        self.on_error(f"Wayland paste failed: {reply.body[0]}")
                        break

        try:
            await bus.call(
                Message(
                    destination=self.SERVICE,
                    path=session_handle,
                    interface="org.freedesktop.portal.Session",
                    member="Close",
                )
            )
        except Exception:
            pass
        bus.disconnect()


def create_text_injector(
    restore_token: str,
    on_restore_token: Callable[[str], None],
    on_error: Callable[[str], None],
    on_ready: Callable[[], None],
    parent_window: str = "",
) -> TextInjector:
    if (
        sys.platform.startswith("linux")
        and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    ):
        return PortalTextInjector(
            restore_token,
            on_restore_token,
            on_error,
            on_ready,
            parent_window,
        )
    return TextInjector(on_ready)


def paste_from_clipboard(shift: bool = False) -> None:
    """Paste into the currently focused application without reading clipboard data."""
    try:
        from pynput.keyboard import Controller, Key

        keyboard = Controller()
        if sys.platform == "win32":
            time.sleep(0.03)
        keyboard.press(Key.ctrl)
        if shift:
            keyboard.press(Key.shift)
        keyboard.press("v")
        keyboard.release("v")
        if shift:
            keyboard.release(Key.shift)
        keyboard.release(Key.ctrl)
    except Exception as exc:
        raise InjectionError(
            "Automatic paste is unavailable. The transcript is still on the clipboard."
        ) from exc
