"""Landing: two flow cards with Get started, plus a quiet Resume. No splash."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
THEME = (ROOT / "src/codify/static/theme.js").read_text(encoding="utf-8")

HEADLINE = (
    "Codify turns what you need to address into clear control statements, "
    "which you then test in Enact."
)


def _card(index: str, start_id: str) -> str:
    after = index.split(f'id="{start_id}"', 1)
    assert len(after) == 2, start_id
    before = after[0].rsplit("<article", 1)
    assert len(before) == 2, start_id
    return "<article" + before[1] + after[1].split("</article>", 1)[0]


def test_landing_is_two_flow_cards_with_get_started():
    assert 'id="start-from-risks"' in INDEX
    assert 'id="start-from-clause"' in INDEX
    assert INDEX.count(">Get started<") == 2
    risks = _card(INDEX, "start-from-risks")
    assert "Identify risk" in risks
    assert "Control statement" in risks
    assert "Technical policy (Rego)" in risks
    assert ">Enact<" not in risks
    assert "Get started" in risks
    assert "Recommended" not in risks
    assert "Screens left unlocked" not in risks
    clause = _card(INDEX, "start-from-clause")
    assert "Policy clause" in clause
    assert "Control statement" in clause
    assert "Technical policy (Rego)" in clause
    assert ">Enact<" not in clause
    assert "Get started" in clause
    assert "Users shall lock screens" not in clause
    assert 'id="landing-flow"' not in INDEX
    assert HEADLINE not in INDEX
    assert 'id="start-title"' in INDEX
    assert 'class="visually-hidden"' in INDEX.split('id="start-title"', 1)[0][-80:] + INDEX.split(
        'id="start-title"', 1
    )[1][:80]


def test_landing_has_no_splash_or_checklist_clutter():
    assert 'id="splash"' not in INDEX
    assert 'id="splash-continue"' not in INDEX
    assert "Welcome to Codify" not in INDEX
    assert "checklist__list" not in INDEX
    assert "Set up this workspace" not in INDEX
    assert 'id="current-project"' not in INDEX
    assert "How do you want to start?" not in INDEX
    assert "data-splash" not in THEME
    assert "shouldShowSplash" not in JS
    assert "dismissSplash" not in JS
    assert "codify:splash-seen" not in JS
    assert "codify:splash-seen" not in THEME
    assert 'html[data-splash="open"]' not in CSS


def test_landing_has_only_a_quiet_resume_link():
    assert 'id="resume"' in INDEX
    assert 'id="resume-open"' in INDEX
    assert "Resume" in INDEX.split('id="resume"', 1)[1][:400]
    assert 'id="resume-discard"' not in INDEX
    assert 'id="open-saved"' not in INDEX
    assert "Open a saved project" not in INDEX
    assert 'id="landing-docs"' not in INDEX
    assert "btn--primary" not in INDEX.split('id="resume"', 1)[1].split("</p>", 1)[0]
    assert "landing__quiet" in INDEX.split('id="resume"', 1)[1][:500] or "landing-resume" in CSS


def test_landing_uses_existing_tokens_and_system_fonts():
    assert ".landing" in CSS
    landing_css = CSS.split(".landing {", 1)[1]
    assert "var(--text)" in landing_css
    assert "var(--muted)" in landing_css
    assert "fonts.googleapis" not in landing_css
    assert "Inter" not in landing_css
    assert ".flow-card" in CSS
    assert "fonts.googleapis" not in CSS
    assert 'href="#main"' in INDEX


def test_landing_caption_explains_oscal_and_enact():
    assert 'id="landing-caption"' in INDEX
    caption = INDEX.split('id="landing-caption"', 1)[1][:400]
    assert "Exported as OSCAL and tested as Rego in" in caption
    assert "code1sentinel.github.io/enact" in caption
    assert "Enact" in caption


def test_send_to_enact_keeps_action_and_explains_rego():
    assert "Send to Enact" in INDEX
    assert "testable Rego policy" in INDEX
    assert "testable Rego policy" in JS
    assert 'enact: "Send to Enact"' in JS
    assert 'title: "Send to Enact"' in JS
    assert 'enact: "Enact"' not in JS
