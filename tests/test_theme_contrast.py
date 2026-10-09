"""Theme tokens meet WCAG 2.2 AA and every colour lives in a token."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
THEME_JS = ROOT / "src/codify/static/theme.js"

HEX = re.compile(r"#(?:[0-9A-Fa-f]{3,8})\b")
RGBA = re.compile(r"rgba?\([^)]+\)")
BLOCK = re.compile(r'\[data-theme="(dark|light)"\]\s*\{([^{}]+)\}', re.S)
TOKEN = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;]+);")

TEXT_PAIRS = (
    ("--text", "--bg"),
    ("--text", "--surface"),
    ("--muted", "--bg"),
    ("--muted", "--surface"),
    ("--placeholder", "--bg"),
    ("--danger", "--bg"),
    ("--danger", "--surface"),
    ("--ready", "--bg"),
    ("--part-action", "--surface"),
    ("--part-scope", "--surface"),
    ("--part-limit", "--surface"),
    ("--part-purpose", "--surface"),
    ("--accent-text", "--bg"),
    ("--accent-text", "--surface"),
    ("--on-accent", "--orange"),
    ("--on-accent", "--orange-bright"),
)

UI_PAIRS = (
    ("--border", "--bg"),
    ("--focus", "--bg"),
    ("--orange", "--bg"),
    ("--accent-text", "--surface-raised"),
)

LEGACY_ORANGE = ("#e8650a", "#ff7a22", "#ff9a52", "#b54c00")


def _hex_to_rgb(value: str) -> tuple[float, float, float] | None:
    value = value.strip()
    if not value.startswith("#") or len(value) not in (4, 7):
        return None
    if len(value) == 4:
        value = "#" + "".join(ch * 2 for ch in value[1:])
    n = int(value[1:], 16)
    return ((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255


def _channel(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    r, g, b = (_channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def hue_degrees(value: str) -> float:
    rgb = _hex_to_rgb(value)
    assert rgb, value
    r, g, b = rgb
    mx, mn = max(r, g, b), min(r, g, b)
    delta = mx - mn
    if delta == 0:
        return 0.0
    if mx == r:
        h = ((g - b) / delta) % 6
    elif mx == g:
        h = (b - r) / delta + 2
    else:
        h = (r - g) / delta + 4
    return (h * 60) % 360


def contrast_ratio(a: str, b: str) -> float:
    rgb_a, rgb_b = _hex_to_rgb(a), _hex_to_rgb(b)
    assert rgb_a and rgb_b, (a, b)
    l1, l2 = relative_luminance(rgb_a), relative_luminance(rgb_b)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def theme_tokens(name: str) -> dict[str, str]:
    blocks = {m.group(1): m.group(2) for m in BLOCK.finditer(CSS)}
    assert name in blocks, f"missing [data-theme={name!r}]"
    tokens = {}
    for key, raw in TOKEN.findall(blocks[name]):
        tokens[key] = raw.strip()
    return tokens


def test_theme_script_is_same_origin_and_not_inline():
    assert THEME_JS.is_file()
    assert 'src="theme.js"' in INDEX
    assert "<script>" not in INDEX.replace('<script src="theme.js"></script>', "").replace(
        '<script type="module" src="app.js"></script>', ""
    )
    js = THEME_JS.read_text(encoding="utf-8")
    assert "codify:theme" in js
    assert "prefers-color-scheme" in js
    assert "localStorage" in js


def test_ai_control_is_a_status_chip_not_a_view_tab():
    assert 'id="ai-open"' in INDEX
    ai = INDEX.split('id="ai-open"', 1)[0][-80:]
    assert "view-btn" not in ai
    assert "status-chip" in INDEX
    assert INDEX.count('data-view="') == 5
    assert 'data-nav="risks"' not in INDEX
    assert 'data-nav="workspace"' in INDEX
    assert 'data-nav="clauses"' in INDEX
    assert 'data-nav="catalog"' in INDEX
    assert 'data-nav="library"' in INDEX
    assert 'data-nav="export"' in INDEX
    assert 'id="ai-open"' in INDEX
    assert 'data-theme-choice="light"' in INDEX
    assert 'data-theme-choice="dark"' in INDEX
    assert 'data-theme-choice="system"' in INDEX
    assert 'role="radiogroup"' in INDEX


def test_colours_live_in_theme_tokens():
    stripped = BLOCK.sub("", CSS)
    leftover = [m.group(0) for m in HEX.finditer(stripped)] + [m.group(0) for m in RGBA.finditer(stripped)]
    assert leftover == [], leftover


def test_token_pairs_meet_wcag_aa():
    failures = []
    for theme in ("dark", "light"):
        tokens = theme_tokens(theme)
        for a, b in TEXT_PAIRS:
            ratio = contrast_ratio(tokens[a], tokens[b])
            if ratio < 4.5:
                failures.append(f"{theme} {a} on {b}: {ratio:.2f} < 4.5 ({tokens[a]} / {tokens[b]})")
        for a, b in UI_PAIRS:
            ratio = contrast_ratio(tokens[a], tokens[b])
            if ratio < 3:
                failures.append(f"{theme} {a} on {b}: {ratio:.2f} < 3 ({tokens[a]} / {tokens[b]})")
        assert tokens["--placeholder"] != "#6E6E6E"
        if theme == "light":
            assert tokens["--accent-text"].lower() != "#e8650a"
    assert not failures, "\n".join(failures)


def test_accent_is_indigo_on_cool_gray():
    for theme in ("dark", "light"):
        tokens = theme_tokens(theme)
        accent = tokens["--orange"]
        assert accent.lower() not in LEGACY_ORANGE, theme
        hue = hue_degrees(accent)
        assert 220 <= hue <= 250, f"{theme} accent hue {hue:.1f} is not indigo ({accent})"
        on_accent = _hex_to_rgb(tokens["--on-accent"])
        assert on_accent and relative_luminance(on_accent) > 0.7, theme
        bg = _hex_to_rgb(tokens["--bg"])
        assert bg, theme
        r, _g, b = bg
        assert b >= r - 1e-9, f"{theme} --bg {tokens['--bg']} is not cool gray"
        if theme == "dark":
            assert tokens["--bg"].lower() != "#0c0c0c"
        action = hue_degrees(tokens["--part-action"])
        assert 220 <= action <= 260, f"{theme} --part-action hue {action:.1f}"


def test_web_assets_drop_legacy_orange():
    haystacks = (CSS.lower(), INDEX.lower())
    for hex_value in LEGACY_ORANGE:
        for hay in haystacks:
            assert hex_value not in hay, hex_value
