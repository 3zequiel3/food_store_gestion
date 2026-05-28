"""
Task 2.1 — Failing test: registration.py must NOT use asyncio.get_event_loop().

Strategy: parse the source text of registration.py and assert the substring
`asyncio.get_event_loop(` is NOT present outside of comments and docstrings.

This test FAILS against current code (registration.py:71 uses get_event_loop).
After the fix (2.2), the call is replaced with get_running_loop() and the
test PASSES.

We use source-text inspection instead of runtime monkeypatching because
the deprecated call is a static code smell — we want to ban it permanently.
"""

from __future__ import annotations

import ast
import textwrap
import tokenize
import io


def _load_registration_source() -> str:
    """Load the source text of registration.py."""
    import importlib.util
    import pathlib

    # Resolve relative to the backend package root
    spec = importlib.util.find_spec("features.websocket.registration")
    assert spec is not None, "features.websocket.registration module not found"
    assert spec.origin is not None
    return pathlib.Path(spec.origin).read_text(encoding="utf-8")


def _extract_non_comment_tokens(source: str) -> list[str]:
    """
    Return all token strings from source excluding COMMENT and STRING tokens
    (the latter covers docstrings when they appear as the first statement).

    We strip docstrings conservatively: any STRING token that is a pure string
    literal (starts with ' or " or triple-quote) is excluded.
    """
    tokens = []
    try:
        for tok_type, tok_string, _, _, _ in tokenize.generate_tokens(
            io.StringIO(source).readline
        ):
            if tok_type == tokenize.COMMENT:
                continue
            if tok_type == tokenize.STRING:
                # Docstrings — skip
                continue
            tokens.append(tok_string)
    except tokenize.TokenError:
        # Partial parse is fine for this assertion
        pass
    return tokens


class TestNoGetEventLoop:
    """registration.py must not call asyncio.get_event_loop()."""

    def test_get_event_loop_not_in_source(self):
        """
        Task 2.1: assert asyncio.get_event_loop( is NOT present in the
        non-comment, non-docstring tokens of registration.py.

        FAILS against current code (line 71 uses get_event_loop).
        PASSES after fix (2.2) replaces it with get_running_loop().
        """
        source = _load_registration_source()

        # Reconstruct token stream as a single joined string for substring search.
        # We join with a space so `get_event_loop` as an identifier is preserved.
        token_text = " ".join(_extract_non_comment_tokens(source))

        assert "get_event_loop" not in token_text, (
            "Found `asyncio.get_event_loop` in features/websocket/registration.py "
            "(outside comments/docstrings). "
            "Replace with `asyncio.get_running_loop()` as per Decision 3 (design.md). "
            "`get_event_loop()` is deprecated since Python 3.10 and can yield a "
            "dead loop under uvicorn --reload."
        )
