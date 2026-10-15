"""One landing: headline, converging flow, two start cards. No splash."""

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


def test_landing_has_headline_flow_and_two_cards():
    assert HEADLINE in INDEX
    assert 'id="start-title"' in INDEX
    assert 'id="landing-flow"' in INDEX
    assert "Risks" in INDEX.split('id="landing-flow"', 1)[1][:1200]
    assert "Policy clause" in INDEX.split('id="landing-flow"', 1)[1][:1200]
    assert "Control statements" in INDEX.split('id="landing-flow"', 1)[1][:1200]
    assert "Enact" in INDEX.split('id="landing-flow"', 1)[1][:1200]
    assert 'id="start-from-risks"' in INDEX
    assert 'id="start-from-clause"' in INDEX
    risks = INDEX.split('id="start-from-risks"', 1)[1].split('id="start-from-clause"', 1)[0]
    assert "Recommended" in risks
    assert "Start from risks" in risks
    assert "Screens left unlocked" in risks
    clause = INDEX.split('id="start-from-clause"', 1)[1].split("</button>", 1)[0]
    assert "Start from a policy clause" in clause
    assert "Users shall lock screens" in clause


def test_landing_has_no_splash_or_checklist_clutter():
    assert 'id="splash"' not in INDEX
    assert 'id="splash-continue"' not in INDEX
    assert "Welcome to Codify" not in INDEX
    assert "Get started" not in INDEX
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


def test_landing_has_quiet_secondary_resume_open_and_docs():
    assert 'id="resume"' in INDEX
    assert 'id="resume-open"' in INDEX
    assert "Resume" in INDEX.split('id="resume"', 1)[1][:800]
    assert 'id="open-saved"' in INDEX
    assert "Open a saved project" in INDEX
    assert 'id="landing-docs"' in INDEX
    assert "getting-started.md" in INDEX.split('id="landing-docs"', 1)[0][-200:] + INDEX.split(
        'id="landing-docs"', 1
    )[1][:400]


def test_landing_uses_existing_tokens_and_system_fonts():
    assert ".landing" in CSS
    landing_css = CSS.split(".landing {", 1)[1]
    assert "var(--text)" in landing_css
    assert "var(--muted)" in landing_css
    assert "fonts.googleapis" not in landing_css
    assert "Inter" not in landing_css
    assert ".choice-card" in CSS
    assert "fonts.googleapis" not in CSS
    assert 'href="#main"' in INDEX
