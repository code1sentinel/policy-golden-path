"""Marketing landing: short giga-style hero, then Get started into the risk flow."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
THEME = (ROOT / "src/codify/static/theme.js").read_text(encoding="utf-8")
CONTRIBUTING = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

HEADLINE = "Controls you can test."
SUBHEAD = (
    "Identified risks and policy clauses become control statements. "
    "Export OSCAL 1.1.2. Test them as Rego."
)
OLD_HEADLINE = "Turn risks and policy into controls you can test."
BASE_BLUE = "#0052FF"


def test_landing_is_a_short_giga_style_page():
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
    risk = INDEX.split('id="start-from-risks"', 1)[1][:220]
    assert "Get started with identified risks" in risk
    assert 'id="start-from-clause"' in INDEX
    clause = INDEX.split('id="start-from-clause"', 1)[1][:220]
    assert "Get started with an existing policy clause" in clause
    hero_actions = INDEX.split('class="landing-hero__actions"', 1)[1].split("landing-hero__stage", 1)[0]
    assert "Get started with identified risks" in hero_actions
    assert "Get started with an existing policy clause" in hero_actions
    assert "Private by design: runs in your browser" in hero_actions
    assert INDEX.count(">Get started<") == 1
    assert ">Get started<" in INDEX.split('id="landing-cta-start"', 1)[1][:80]
    assert 'id="how-it-works"' in INDEX
    assert 'id="landing-mock"' in INDEX
    assert 'id="landing-privacy-badge"' in INDEX
    assert "Private by design: runs in your browser" in INDEX
    assert 'id="landing-trust"' in INDEX
    assert "NIST 800-53" in INDEX
    assert "ISO 27001" in INDEX
    assert "OSCAL 1.1.2" in INDEX
    assert "Runs in your browser" in INDEX.split('id="landing-trust"', 1)[1]
    assert "No data leaves your device" in INDEX
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
    assert "Scroll to explore" not in INDEX
    assert 'id="landing-scroll"' not in INDEX
    assert 'id="landing-chips"' not in INDEX
    assert 'id="landing-features"' not in INDEX
    assert "Works with frameworks like ISO 27001, SOC 2 and NIST" not in INDEX


def test_landing_does_not_claim_certifications_or_testimonials():
    landing = INDEX.split('id="landing"', 1)[1].split('id="drop"', 1)[0]
    assert "SOC 2" not in landing
    assert "ISO 42001" not in landing
    assert "PCI DSS" not in landing
    assert "certified" not in landing.lower()
    assert "Type II" not in landing
    assert "Co-Founder" not in landing
    assert "testimonial" not in landing.lower()


def test_landing_hero_puts_the_example_below_the_start_buttons():
    hero = INDEX.split('class="landing-hero"', 1)[1].split('id="how-it-works"', 1)[0]
    assert hero.index('class="landing-hero__actions"') < hero.index('id="landing-mock"')
    mock = INDEX.split('id="landing-mock"', 1)[1].split("</figure>", 1)[0]
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


def test_landing_has_one_factual_how_it_works_section():
    how = INDEX.split('id="how-it-works"', 1)[1][:2000]
    assert "How it works" in how
    assert "OSCAL" in how
    assert "Policy as code (Rego)" in how or "Rego" in how
    assert "github.com/code1sentinel/enact" in how
    assert "Enact" in how
    assert 'id="landing-enact"' in how
    assert how.lower().count("<blockquote") == 0 or "testimonial" not in how.lower()


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
    hero_css = CSS.split(".landing-hero", 1)[1][:1800]
    assert "var(--hero)" not in hero_css
    assert BASE_BLUE not in hero_css


def test_landing_explains_oscal_and_enact():
    how = INDEX.split('id="how-it-works"', 1)[1][:2500]
    assert "OSCAL" in how
    assert "Rego" in how
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


def test_hero_start_buttons_stack_on_a_phone():
    assert ".landing-hero__cta-row" in CSS
    mobile = CSS.split("@media (max-width: 520px)", 1)[1]
    assert "flex-direction: column" in mobile.split(".landing-hero__cta-row", 1)[1][:400]
