"""Incremental thinking-tag filter for streaming."""

_THINKING_TAGS = ["think", "thinking", "reasoning", "thought", "reflection"]
_OPEN_TAGS = {f"<{t}>" for t in _THINKING_TAGS}
_CLOSE_TAGS = {f"</{t}>" for t in _THINKING_TAGS}
_MAX_TAG_LEN = max(len(t) for t in _OPEN_TAGS | _CLOSE_TAGS)


class FilteredToken:
    """A token emitted by ``_StreamingTagFilter`` with metadata."""

    __slots__ = ("is_thinking", "text")

    def __init__(self, text: str, *, is_thinking: bool = False) -> None:
        self.text = text
        self.is_thinking = is_thinking


class _StreamingTagFilter:
    """Incremental filter that separates thinking content from visible output.

    Feed token strings via ``feed()`` and iterate the yielded ``FilteredToken``
    items. Each item has ``text`` (the content) and ``is_thinking`` (whether it
    came from inside a thinking tag).

    Content outside thinking tags is yielded immediately, except for a small
    look-ahead buffer to detect tag boundaries.
    """

    def __init__(self) -> None:
        self._buf = ""
        self._suppressing = False

    # noinspection PyMethodMayBeStatic
    def _is_open_tag(self, text: str) -> str | None:
        low = text.lower()
        for tag in _OPEN_TAGS:
            if low.startswith(tag):
                return tag
        return None

    def _is_close_tag(self, text: str) -> str | None:
        low = text.lower()
        for tag in _CLOSE_TAGS:
            if low.startswith(tag):
                return tag
        return None

    def feed(self, token: str) -> list[FilteredToken]:
        """Feed a token and return list of ``FilteredToken`` items to emit."""
        self._buf += token
        out: list[FilteredToken] = []

        while self._buf:
            if self._suppressing:
                # Look for a closing tag in the buffer
                close = self._is_close_tag(self._buf)
                if close:
                    # Emit accumulated thinking content before the close tag
                    (
                        self._buf[: self._buf.lower().index(close.lower())]
                        if close.lower() in self._buf.lower()
                        else ""
                    )
                    # Actually, the close tag sits at index 0 since we already
                    # consumed the open tag.  Emit the buffered thinking content.
                    self._buf = self._buf[len(close) :]
                    self._suppressing = False
                    continue

                # Check if buffer *could* start with a partial close tag
                could_be_close = any(
                    self._buf.lower().startswith(t[: len(self._buf)])
                    for t in _CLOSE_TAGS
                    if len(self._buf) < len(t)
                )
                if could_be_close:
                    break  # Wait for more data

                # Not a close tag — emit the first char as thinking content
                out.append(FilteredToken(self._buf[0], is_thinking=True))
                self._buf = self._buf[1:]
                continue

            # --- Not suppressing ---

            # Check for an opening tag
            open_tag = self._is_open_tag(self._buf)
            if open_tag:
                self._buf = self._buf[len(open_tag) :]
                self._suppressing = True
                continue

            # Could this be the start of an opening tag?  (e.g. "<thi")
            if "<" in self._buf:
                lt_pos = self._buf.index("<")
                # Emit everything before the '<'
                if lt_pos > 0:
                    out.append(FilteredToken(self._buf[:lt_pos]))
                    self._buf = self._buf[lt_pos:]

                # Check if the remainder could still become a thinking tag
                remainder = self._buf.lower()
                could_be_open = any(t.startswith(remainder) for t in _OPEN_TAGS)
                if could_be_open and len(self._buf) < _MAX_TAG_LEN:
                    break  # Wait for more data

                # Not a thinking tag — emit the '<' and continue
                out.append(FilteredToken(self._buf[0]))
                self._buf = self._buf[1:]
                continue

            # No '<' at all — emit the entire buffer
            out.append(FilteredToken(self._buf))
            self._buf = ""

        return out

    def flush(self) -> list[FilteredToken]:
        """Flush any remaining buffered content (call at end of stream)."""
        if self._suppressing:
            # Still inside a thinking tag at end — emit as thinking
            if self._buf:
                result = [FilteredToken(self._buf, is_thinking=True)]
                self._buf = ""
                return result
            return []
        result = [FilteredToken(self._buf)] if self._buf else []
        self._buf = ""
        return result
