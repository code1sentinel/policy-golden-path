"""Marketing landing: Base-style hero, then Get started into the risk flow."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
THEME = (ROOT / "src/codify/static/theme.js").read_text(encoding="utf-8")
CONTRIBUTING = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

HEADLINE = "Turn risks and policy into controls you can test."
SUBHEAD = (
    "Draft control statements from risks or policy clauses, export OSCAL, "
    "and ship them as policy as code."
)
OLD_HEADLINE = (
    "Codify turns what you need to address into clear control statements, "
    "which you then test in Enact."
)
BASE_BLUE = "#0052FF"


def test_landing_is_a_marketing_page_not_two_flow_cards():
    assert HEADLINE in INDEX
    assert 'id="start-title"' in INDEX
    assert SUBHEAD in INDEX
    assert 'id="landing-subhead"' in INDEX
    assert 'id="landing-bar"' in INDEX
    assert 'id="landing-docs"' in INDEX
    assert "Docs" in INDEX.split('id="landing-docs"', 1)[1][:400]
    assert 'id="landing-github"' in INDEX
    assert "GitHub" in INDEX.split('id="landing-github"', 1)[1][:400]
    assert "github.com/code1sentinel/policy-golden-path" in INDEX
    assert 'id="landing-nav-start"' not in INDEX
    assert 'id="start-from-risks"' in INDEX
    assert 'id="landing-cta-start"' in INDEX
    assert INDEX.count(">Get started<") == 2
    assert 'id="start-from-clause"' in INDEX
    clause = INDEX.split('id="start-from-clause"', 1)[1][:160]
    assert "Start from a policy clause" in clause
    assert "btn--on-hero-secondary" in INDEX.split('id="start-from-clause"', 1)[0][-80:] + clause
    assert 'id="landing-how-link"' in INDEX
    assert "See how it works" in INDEX
    assert 'href="#how-it-works"' in INDEX
    assert 'id="how-it-works"' in INDEX
    assert "Identify risks or pick a policy clause" in INDEX
    assert "Draft control statements" in INDEX
    assert "Export as OSCAL" in INDEX
    assert "Policy as code (Rego)" in INDEX
    assert 'id="landing-features"' in INDEX
    assert "Risk-first or clause-first" in INDEX
    assert "Plain-language guides" in INDEX
    assert "Standards-based OSCAL export" in INDEX
    assert "Private by design" in INDEX
    assert "No AI keys stored" in INDEX
    assert 'id="landing-mock"' in INDEX
    assert 'id="landing-chips"' in INDEX
    assert "Scroll to explore" in INDEX
    assert 'id="landing-scroll"' in INDEX
    assert 'id="landing-privacy-badge"' in INDEX
    assert "Private by design: runs in your browser" in INDEX
    assert "Works with frameworks like ISO 27001, SOC 2 and NIST" in INDEX
    assert 'id="landing-contribute"' in INDEX
    assert "Star or contribute on GitHub" in INDEX
    assert "Contribute a control template" in INDEX
    assert "CONTRIBUTING.md#control-templates" in INDEX
    assert "GRC Engineering Club" not in INDEX
    assert 'id="landing-cta"' in INDEX
    assert 'id="landing-footer"' in INDEX
    assert 'class="flow-card"' not in INDEX
    assert 'id="landing-flow"' not in INDEX
    assert 'id="start-choice"' not in INDEX
    assert OLD_HEADLINE not in INDEX
    assert "Identify risk → Control statement" not in INDEX


def test_landing_hero_uses_base_blue_and_a_centered_mock():
    assert BASE_BLUE in CSS
    assert "--hero:" in CSS
    assert ".landing-hero" in CSS
    hero_css = CSS.split(".landing-hero", 1)[1][:2500]
    assert "var(--hero)" in hero_css
    assert 'id="landing-mock"' in INDEX
    mock = INDEX.split('id="landing-mock"', 1)[1]
    mock = mock.split("</figure>", 1)[0]
    assert "<img" not in mock
    assert "http" not in mock
    assert "Identified risk" in mock
    assert "Customer data stored unencrypted" in mock
    assert "Control statement" in mock
    assert "Encrypt customer data at rest" in mock
    assert "OSCAL" in mock
    assert '"id": "sc-28"' in mock
    assert "Policy as code (Rego)" in mock
    assert "deny contains msg if" in mock
    chips = INDEX.split('id="landing-chips"', 1)[1].split("</ul>", 1)[0]
    assert chips.count("<li") <= 6
    assert chips.count("<li") >= 4


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
    assert 'id="open-saved"' not in INDEX
    assert "Open a saved project" not in INDEX


def test_landing_has_resume_your_project():
    assert 'id="resume"' in INDEX
    assert 'id="resume-open"' in INDEX
    resume = INDEX.split('id="resume"', 1)[1][:500]
    assert "Resume your project" in resume
    assert 'id="resume-discard"' not in INDEX
    assert "btn--primary" not in INDEX.split('id="resume"', 1)[1].split("</p>", 1)[0]


def test_landing_uses_existing_tokens_and_system_fonts():
    assert ".landing" in CSS
    landing_css = CSS.split(".landing {", 1)[1]
    assert "var(--text)" in landing_css
    assert "var(--muted)" in landing_css
    assert "fonts.googleapis" not in landing_css
    assert "Inter" not in landing_css
    assert "fonts.googleapis" not in CSS
    assert 'href="#main"' in INDEX


def test_landing_explains_oscal_and_enact():
    how = INDEX.split('id="how-it-works"', 1)[1][:2500]
    assert "OSCAL" in how
    assert "Policy as code (Rego)" in how
    assert "github.com/code1sentinel/enact" in how
    assert "Enact" in how
    assert 'id="landing-enact"' in how


def test_send_to_enact_keeps_action_and_explains_rego():
    assert "Send to Enact" in INDEX
    assert "testable Rego policy" in INDEX
    assert "testable Rego policy" in JS
    assert 'enact: "Send to Enact"' in JS
    assert 'title: "Send to Enact"' in JS
    assert 'enact: "Enact"' not in JS


def test_contributing_has_a_control_templates_section():
    assert "## Control templates" in CONTRIBUTING
    assert "fictional" in CONTRIBUTING.lower()
    assert "GRC Engineering Club" not in CONTRIBUTING


def test_get_started_buttons_share_the_risk_path_hook():
    assert "data-start-risks" in INDEX
    assert "data-start-risks" in JS or "[data-start-risks]" in JS
    assert "startRiskPath" in JS
    assert "showClausePath" in JS
