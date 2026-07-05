"""Playground — try commands and shortcuts.

* :class:`PlaygroundPage` — Qt page with a command input and quick-action
  cards (Insert Text functional, Smart Rewrite stub).
* :class:`InsertTextAction` / :class:`SmartRewriteAction` — handlers used
  by the cards.

The Qt page is imported lazily so ``InsertTextAction`` /
``SmartRewriteAction`` are usable in environments without PySide6.
"""

from soundflow.playground.actions import InsertTextAction, SmartRewriteAction

__all__ = ["InsertTextAction", "PlaygroundPage", "SmartRewriteAction"]


def __getattr__(name: str):
    if name == "PlaygroundPage":
        from soundflow.playground.page import PlaygroundPage
        return PlaygroundPage
    raise AttributeError(f"module 'soundflow.playground' has no attribute {name!r}")