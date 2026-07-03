from __future__ import annotations

from typing import Any


class PortalRegistrationError(RuntimeError):
    pass


async def register_host_app(bus: Any, app_id: str = "soundflow") -> None:
    """Associate a native application's D-Bus connection with its desktop ID."""
    from dbus_next import Message, MessageType

    reply = await bus.call(
        Message(
            destination="org.freedesktop.portal.Desktop",
            path="/org/freedesktop/portal/desktop",
            interface="org.freedesktop.host.portal.Registry",
            member="Register",
            signature="sa{sv}",
            body=[app_id, {}],
        )
    )
    if reply.message_type == MessageType.ERROR:
        detail = str(reply.body[0]) if reply.body else "unknown portal error"
        raise PortalRegistrationError(f"Could not register app ID: {detail}")
