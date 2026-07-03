from __future__ import annotations

import argparse
import logging
import multiprocessing
import os
import sys
import tempfile
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Private, offline desktop dictation")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use a fake transcriber to test controls without a model",
    )
    parser.add_argument(
        "--no-hotkeys",
        action="store_true",
        help="Disable global keyboard listeners for this run",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Start ready for push-to-talk without opening the main window",
    )
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--self-test-audio",
        type=Path,
        metavar="WAV",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    multiprocessing.freeze_support()
    args = build_parser().parse_args(argv)
    if args.self_test_audio:
        return _run_inference_self_test(args.self_test_audio)
    if (
        sys.platform.startswith("linux")
        and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
    ):
        # PySide does not expose an xdg-foreign token. XWayland provides a
        # stable XID so GNOME can parent its required permission dialogs.
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    try:
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "Soundflow's GUI dependencies are not installed.\n"
            "Create a Python 3.11–3.13 virtual environment and run:\n"
            "  python -m pip install -e .",
            file=sys.stderr,
        )
        return 2

    from soundflow.core.settings import SettingsStore
    from soundflow.portal import APP_ID
    from soundflow.ui import MainWindow
    from PySide6.QtCore import QTimer

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    application = QApplication(["soundflow"])
    application.setApplicationName("Soundflow")
    application.setOrganizationName("Soundflow")
    application.setDesktopFileName(APP_ID)
    application.setQuitOnLastWindowClosed(False)

    server_name = (
        str(Path(tempfile.gettempdir()) / f"soundflow-{os.getuid()}.sock")
        if hasattr(os, "getuid")
        else "soundflow"
    )
    existing = QLocalSocket()
    existing.connectToServer(server_name)
    if existing.waitForConnected(200):
        existing.write(b"background" if args.background else b"show")
        existing.waitForBytesWritten(200)
        existing.disconnectFromServer()
        return 0
    QLocalServer.removeServer(server_name)
    instance_server = QLocalServer(application)
    if not instance_server.listen(server_name):
        print(
            f"Soundflow single-instance channel is unavailable: "
            f"{instance_server.errorString()}",
            file=sys.stderr,
        )

    store = SettingsStore()
    settings = store.load()
    window = MainWindow(settings, store, demo_mode=args.demo, no_hotkeys=args.no_hotkeys)

    def handle_instance_request() -> None:
        client = instance_server.nextPendingConnection()
        if client is None:
            return
        if not client.bytesAvailable():
            client.waitForReadyRead(200)
        command = bytes(client.readAll()).decode("utf-8", errors="ignore")
        if command == "show":
            window._show_window()
        client.disconnectFromServer()
        client.deleteLater()

    if instance_server.isListening():
        instance_server.newConnection.connect(handle_instance_request)
    application.aboutToQuit.connect(window.shutdown)
    setup_required = (
        settings.global_hotkeys
        and not settings.hotkey_authorized
        and not args.no_hotkeys
    )
    if setup_required or (not settings.start_minimized and not args.background):
        window.show()
    if args.smoke_test:
        QTimer.singleShot(300, application.quit)
    return application.exec()

def _run_inference_self_test(path: Path) -> int:
    import wave

    from soundflow.core.settings import default_model_path
    from soundflow.transcription import FasterWhisperTranscriber

    with wave.open(str(path), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != 16_000
        ):
            raise ValueError("Self-test WAV must be 16 kHz, mono, signed 16-bit PCM")
        pcm = source.readframes(source.getnframes())
    text = FasterWhisperTranscriber(
        default_model_path(),
        language="en",
        device="cpu",
        compute_type="int8",
    ).transcribe_pcm(pcm, 16_000)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
