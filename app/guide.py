"""First-run guide: a step-by-step walkthrough of where everything is.

How it works
------------
* On a visitor's first visit to the Pricer, the guide opens automatically. Finishing,
  skipping or closing it stores a cookie (``opl_guide=done``), so it does not come back;
  ``GUIDE`` in the top bar reopens it at any time.
* Each step opens as a drawer on the side of the screen *away* from the element it
  describes, outlines that element on the real page, scrolls it into view, and shows a
  mini-map of the layout with the same region lit up.
* ``?guide=off`` in the URL suppresses the automatic opening (used by tests and handy
  for sharing links); ``?guide=on`` forces it.

All wording lives in :mod:`app.content` under ``guide.*``.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Literal, Optional

import streamlit as st

from app.content import t
from app.ui import is_pro, mode, upper

COOKIE = "opl_guide"


@dataclass(frozen=True)
class Step:
    """One stop on the guide."""

    key: str
    target: Optional[str]  # CSS selector of the element to outline, if any
    region: Optional[str]  # mini-map region to light up
    side: Literal["left", "right", "center"]  # where the drawer opens (away from the target)


STEPS: tuple[Step, ...] = (
    Step("welcome", None, None, "center"),
    Step("tools", ".st-key-topnav", "tools", "right"),
    Step("mode", ".st-key-topmode", "mode", "left"),
    Step("readout", ".opl-telemetry", "readout", "left"),
    Step("inputs", ".st-key-panel_pricer_inputs", "inputs", "right"),
    Step("examples", ".st-key-preset_pill", "examples", "right"),
    Step("value", ".opl-grid:has(.opl-readout)", "value", "left"),
    Step("methods", ".opl-ledger", "methods", "left"),
    Step("greeks", ".opl-grid:has(.opl-greek)", "greeks", "left"),
    Step("chart", ".st-key-pricer_value_chart", "chart", "left"),
    Step("done", None, None, "center"),
)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def start(*_: object) -> None:
    """Open the guide at step 1 on the Pricer (used by the GUIDE button)."""
    st.session_state["guide_active"] = True
    st.session_state["guide_step"] = 0
    if st.session_state.get("nav_tool") != "pricer":
        st.session_state["_goto"] = "pricer"


def _close() -> None:
    st.session_state["guide_active"] = False
    st.session_state["guide_set_cookie"] = True


def maybe_auto_open(current: str) -> None:
    """Open the guide automatically on a first visit to the Pricer (once per session)."""
    if st.session_state.get("guide_checked"):
        return
    if st.session_state.get("mode") == "Simple":  # the guide tours the full lab, not the Simple screens
        return
    st.session_state["guide_checked"] = True
    flag = str(st.query_params.get("guide", "")).strip().lower()
    if flag == "off":
        return
    first_visit = st.context.cookies.get(COOKIE) != "done"
    if current == "pricer" and (flag == "on" or first_visit):
        st.session_state["guide_active"] = True
        st.session_state["guide_step"] = 0


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _labels(text: str) -> str:
    """Escape ``text`` and render top-level ``[LABEL]`` spans as on-screen key caps (nesting allowed)."""
    out, buf, depth = [], [], 0
    for ch in text:
        if ch == "[":
            if depth == 0:
                out.append(html.escape("".join(buf)))
                buf = []
            else:
                buf.append(ch)
            depth += 1
        elif ch == "]" and depth > 0:
            depth -= 1
            if depth == 0:
                out.append(f'<span class="opl-key">{html.escape("".join(buf))}</span>')
                buf = []
            else:
                buf.append(ch)
        else:
            buf.append(ch)
    out.append(html.escape("".join(buf)))
    return "".join(out)


def _body_html(text: str) -> str:
    """Paragraphs, with lines starting ``- `` grouped into a list."""
    parts, items = [], []
    for line in text.split("\n"):
        if line.startswith("- "):
            items.append(f"<li>{_labels(line[2:])}</li>")
            continue
        if items:
            parts.append(f"<ul>{''.join(items)}</ul>")
            items = []
        if line.strip():
            parts.append(f"<p>{_labels(line)}</p>")
    if items:
        parts.append(f"<ul>{''.join(items)}</ul>")
    return "".join(parts)


def _minimap(active: Optional[str]) -> str:
    """A schematic of the screen with the region being described lit up."""

    def cell(region: str, area: str) -> str:
        on = " on" if region == active else ""
        return f'<div class="m{on}" style="grid-area:{area}">{html.escape(upper(t(f"guide.map.{region}")))}</div>'

    return (
        '<div class="opl-minimap">'
        + cell("tools", "tools") + cell("readout", "readout") + cell("guide", "guide") + cell("mode", "mode")
        + cell("examples", "examples") + cell("inputs", "inputs")
        + cell("value", "value") + cell("methods", "methods") + cell("greeks", "greeks") + cell("chart", "chart")
        + "</div>"
    )


def _spotlight(step: Step, index: int) -> None:
    """Outline the step's element on the real page and scroll it into view."""
    if not step.target:
        return
    st.html(
        f"<style>{step.target} {{ outline: 2px solid #FF5500 !important; outline-offset: 3px; }}</style>"
    )
    selector = step.target.replace("\\", "\\\\").replace("'", "\\'")
    st.html(
        "<script>"
        f"/* guide step {index} */"
        "setTimeout(function () {"
        f"  var el = document.querySelector('{selector}');"
        "  if (el) { el.scrollIntoView({behavior: 'smooth', block: 'center'}); }"
        "}, 350);"
        "</script>",
        unsafe_allow_javascript=True,
    )


def _remember_done() -> None:
    """Store a one-year cookie so the guide does not reopen on the next visit."""
    if st.session_state.pop("guide_set_cookie", False):
        st.html(
            f"<script>document.cookie = '{COOKIE}=done; max-age=31536000; path=/; SameSite=Lax';</script>",
            unsafe_allow_javascript=True,
        )


# ---------------------------------------------------------------------------
# The dialog
# ---------------------------------------------------------------------------

def _contents() -> None:
    index = int(st.session_state.get("guide_step", 0))
    index = max(0, min(index, len(STEPS) - 1))
    step = STEPS[index]
    total = len(STEPS)
    m = mode()

    progress = "".join(f'<i class="{"on" if i <= index else ""}"></i>' for i in range(total))
    st.html(
        '<div class="opl-guide">'
        f'<div class="opl-guide-progress">{progress}</div>'
        f'<div class="opl-guide-step">{html.escape(upper(t("guide.step_of", n=index + 1, total=total)))}</div>'
        f'<h2>{html.escape(t(f"guide.{step.key}.title", m))}</h2>'
        f'<div class="opl-guide-body">{_body_html(t(f"guide.{step.key}.body", m))}</div>'
        + (_minimap(step.region) if step.key != "done" else "")
        + "</div>"
    )

    with st.container(horizontal=True, gap="small", key="guide_buttons"):
        if index == 0:
            if st.button(upper(t("guide.start")), type="primary", key="guide_next"):
                st.session_state["guide_step"] = 1
                st.rerun()
            st.space("stretch")
            if st.button(upper(t("guide.skip")), type="tertiary", key="guide_skip"):
                _close()
                st.rerun()
        elif index == total - 1:
            if st.button(upper(t("guide.back")), key="guide_back"):
                st.session_state["guide_step"] = index - 1
                st.rerun()
            st.space("stretch")
            if st.button(upper(t("guide.finish")), type="primary", key="guide_finish"):
                _close()
                st.rerun()
        else:
            if st.button(upper(t("guide.back")), key="guide_back"):
                st.session_state["guide_step"] = index - 1
                st.rerun()
            if st.button(upper(t("guide.next")), type="primary", key="guide_next"):
                st.session_state["guide_step"] = index + 1
                st.rerun()
            st.space("stretch")
            if st.button(upper(t("guide.skip")), type="tertiary", key="guide_skip"):
                _close()
                st.rerun()


def _on_dismiss() -> None:
    """Closing the drawer (X, Esc or clicking outside) counts as skipping."""
    _close()


_TITLE = upper(t("guide.dialog_title"))


@st.dialog(_TITLE, width="medium", position="center", on_dismiss=_on_dismiss)
def _dialog_center() -> None:
    _contents()


@st.dialog(_TITLE, width=380, position="left", on_dismiss=_on_dismiss)
def _dialog_left() -> None:
    _contents()


@st.dialog(_TITLE, width=380, position="right", on_dismiss=_on_dismiss)
def _dialog_right() -> None:
    _contents()


def render(current: str) -> None:
    """Draw the guide for this run if it is active (call at the end of every page run)."""
    _remember_done()
    if not st.session_state.get("guide_active"):
        return
    if current != "pricer":
        # The guide describes the Pricer; if the visitor navigated away, close it quietly.
        st.session_state["guide_active"] = False
        return
    index = max(0, min(int(st.session_state.get("guide_step", 0)), len(STEPS) - 1))
    step = STEPS[index]
    if step.key == "examples" and is_pro():
        step = Step(step.key, None, step.region, step.side)  # examples are hidden in Pro mode
    _spotlight(step, index)
    {"left": _dialog_left, "right": _dialog_right, "center": _dialog_center}[step.side]()
