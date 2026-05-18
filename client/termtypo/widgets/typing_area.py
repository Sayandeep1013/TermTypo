"""Core typing test widget — handles input and renders coloured word display."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from textual.app import RenderResult
from textual.events import Key
from textual.message import Message
from textual.widget import Widget
from rich.text import Text


@dataclass
class TypingState:
    words: list[str] = field(default_factory=list)
    typed: list[list[str]] = field(default_factory=list)   # per-word typed chars
    current_word: int = 0
    started: bool = False
    finished: bool = False
    start_time: float = 0.0
    end_time: float = 0.0
    total_keystrokes: int = 0
    correct_keystrokes: int = 0
    wpm_samples: list[tuple[float, float]] = field(default_factory=list)  # (elapsed, wpm)

    def reset(self, words: list[str]) -> None:
        self.words = list(words)
        self.typed = [[] for _ in words]
        self.current_word = 0
        self.started = False
        self.finished = False
        self.start_time = 0.0
        self.end_time = 0.0
        self.total_keystrokes = 0
        self.correct_keystrokes = 0
        self.wpm_samples = []

    @property
    def elapsed(self) -> float:
        if not self.started:
            return 0.0
        end = self.end_time if self.finished else time.monotonic()
        return end - self.start_time

    def wpm(self) -> float:
        elapsed = self.elapsed
        if elapsed < 0.5:
            return 0.0
        correct_chars = sum(
            sum(1 for c, e in zip(self.typed[i], self.words[i]) if c == e)
            for i in range(min(self.current_word + 1, len(self.words)))
        )
        return (correct_chars / 5) / (elapsed / 60)

    def raw_wpm(self) -> float:
        elapsed = self.elapsed
        if elapsed < 0.5:
            return 0.0
        return (self.total_keystrokes / 5) / (elapsed / 60)

    def accuracy(self) -> float:
        if self.total_keystrokes == 0:
            return 100.0
        return (self.correct_keystrokes / self.total_keystrokes) * 100


class TypingArea(Widget):
    """Typing test input + word display."""

    can_focus = True

    DEFAULT_CSS = """
    TypingArea {
        height: auto;
        min-height: 6;
        padding: 1 2;
    }
    """

    class Started(Message):
        pass

    class Finished(Message):
        def __init__(self, state: TypingState) -> None:
            super().__init__()
            self.state = state

    class WordAdvanced(Message):
        pass

    def __init__(self, words: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self.state = TypingState()
        self.state.reset(words)

    def reset(self, words: list[str]) -> None:
        self.state.reset(words)
        self.refresh()

    # ── rendering ────────────────────────────────────────────────────────────

    def render(self) -> RenderResult:
        s = self.state
        text = Text()

        for wi, word in enumerate(s.words):
            if wi > 0:
                text.append(" ")

            typed = s.typed[wi]

            if wi < s.current_word:
                # completed word
                for ci, expected in enumerate(word):
                    if ci < len(typed):
                        style = "#9ece6a" if typed[ci] == expected else "#f7768e"
                        text.append(typed[ci], style=style)
                    else:
                        text.append(expected, style="#f7768e")
                # extra chars typed beyond word length
                for extra in typed[len(word):]:
                    text.append(extra, style="on #f7768e")

            elif wi == s.current_word:
                # active word
                cursor_pos = len(typed)
                for ci, expected in enumerate(word):
                    if ci < len(typed):
                        if typed[ci] == expected:
                            text.append(typed[ci], style="bold #9ece6a")
                        else:
                            text.append(expected, style="bold #f7768e")
                    elif ci == cursor_pos:
                        text.append(expected, style="reverse #7aa2f7")
                    else:
                        text.append(expected, style="#565f89")
                # extra chars beyond word end
                for extra in typed[len(word):]:
                    text.append(extra, style="on #f7768e")
                # cursor at very end of word (all chars typed, correct or not)
                if cursor_pos == len(word) and not typed[len(word):]:
                    pass  # cursor shown by next space character logic

            else:
                # upcoming word
                text.append(word, style="#565f89")

        return text

    # ── input handling ────────────────────────────────────────────────────────

    def on_key(self, event: Key) -> None:
        s = self.state
        if s.finished:
            return

        key = event.key
        char = event.character

        # Start on first printable keypress
        if not s.started and char and char.isprintable() and char != " ":
            s.started = True
            s.start_time = time.monotonic()
            self.post_message(self.Started())

        if not s.started:
            return

        if key == "backspace":
            if s.typed[s.current_word]:
                s.typed[s.current_word].pop()
                s.total_keystrokes += 1
            elif s.current_word > 0:
                # Go back to the previous word and remove its last character
                s.current_word -= 1
                if s.typed[s.current_word]:
                    s.typed[s.current_word].pop()
                    s.total_keystrokes += 1
            self.refresh()
            return

        if key == "ctrl+backspace":
            if s.typed[s.current_word]:
                s.typed[s.current_word].clear()
            elif s.current_word > 0:
                # Ctrl+backspace at word start → jump back and clear previous word
                s.current_word -= 1
                s.typed[s.current_word].clear()
            self.refresh()
            return

        if char == " ":
            # Advance to next word (even if current word is wrong)
            if s.typed[s.current_word]:  # must have typed at least one char
                s.current_word += 1
                s.total_keystrokes += 1
                if s.current_word >= len(s.words):
                    self._finish()
                    return
                self.post_message(self.WordAdvanced())
            self.refresh()
            return

        if char and char.isprintable():
            wi = s.current_word
            ci = len(s.typed[wi])
            expected = s.words[wi][ci] if ci < len(s.words[wi]) else None
            s.typed[wi].append(char)
            s.total_keystrokes += 1
            if expected and char == expected:
                s.correct_keystrokes += 1

            # Auto-finish: end the moment the last word is typed exactly — no
            # trailing space required.  MonkeyType / TypeRacer both do this.
            # Works for words mode, races, and the (unlikely) case where a
            # timed-mode player types every generated word.
            if wi == len(s.words) - 1 and "".join(s.typed[wi]) == s.words[wi]:
                self._finish()
                return

            self.refresh()

    def _finish(self) -> None:
        s = self.state
        s.finished = True
        s.end_time = time.monotonic()
        self.post_message(self.Finished(s))
