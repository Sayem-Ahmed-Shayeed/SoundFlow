from __future__ import annotations

from pathlib import Path


class ExportError(RuntimeError):
    pass


def export_transcript(path: Path, text: str) -> None:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ""}:
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
        return
    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise ExportError("DOCX export requires the python-docx package") from exc
        document = Document()
        for paragraph in text.splitlines() or [""]:
            document.add_paragraph(paragraph)
        document.save(path)
        return
    raise ExportError(f"Unsupported export format: {suffix}")

