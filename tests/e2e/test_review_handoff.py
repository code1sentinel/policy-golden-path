"""Step 3: review summary, Rego starter, OSCAL copy/download, Edit back."""

import json

from playwright.sync_api import expect

from conftest import add_flow_clauses, add_flow_risk, choose_clause_path, choose_risk_path

UNLOCKED = "Screens left unlocked at unattended desks."
LOCK = "Require users to lock screens when they leave their desk."
CLAUSE = "Users shall lock screens when they leave their desk."


def _finish_risk_path(page):
    choose_risk_path(page)
    add_flow_risk(page, UNLOCKED)
    page.click("#identify-continue")
    page.locator("#statements-editor textarea").first.fill(LOCK)
    page.locator("#statements-editor textarea").first.blur()
    page.click("#statements-continue")
    expect(page.locator("#review-page")).to_be_visible()


def test_risk_path_opens_review_with_summary_rego_and_oscal(page, tmp_path):
    _finish_risk_path(page)
    expect(page.locator("#review-steps [aria-current='step']")).to_contain_text(
        "Policy as code (Rego)")
    expect(page.locator("#review-title")).to_have_text("Policy as code (Rego)")
    expect(page.locator("#review-banner")).to_contain_text("Review complete")
    expect(page.locator("#review-summary")).to_contain_text(UNLOCKED)
    expect(page.locator("#review-summary")).to_contain_text(LOCK)
    expect(page.locator("#review-summary")).to_contain_text("Covered")
    expect(page.locator("#review-page")).not_to_contain_text("GRC Engineering Club")
    expect(page.locator("#review-page")).not_to_contain_text("Send to Enact")
    expect(page.locator("#review-handoff")).to_be_enabled()
    expect(page.locator("#review-enact-caption")).to_contain_text("Opens in Enact")

    starters = page.locator("#rego-starters")
    expect(starters).to_contain_text("Generate Rego starter")
    expect(starters).to_contain_text("Starter to review — not a finished policy")
    card = starters.locator(".rego-starter").first
    card.locator("[data-generate]").click()
    code = card.locator(".rego-starter__code")
    expect(code).to_contain_text("import rego.v1")
    card.locator("[data-copy]").click()
    expect(card.locator("[data-copy-status]")).to_have_text("Copied")
    with page.expect_download() as rego_dl:
        card.locator("[data-download]").click()
    rego_path = tmp_path / rego_dl.value.suggested_filename
    rego_dl.value.save_as(rego_path)
    assert rego_path.suffix == ".rego"

    preview = page.locator("#oscal-catalog-json")
    expect(preview).to_contain_text('"catalog"')
    expect(preview).to_contain_text("identified-risk-id")
    expect(preview).to_contain_text("treats-risk")
    expect(preview).to_contain_text("policy-as-code")
    page.locator("#oscal-catalog-copy").click()
    expect(page.locator("#oscal-catalog-copy-status")).to_have_text("Copied")
    with page.expect_download() as oscal_dl:
        page.locator("#oscal-catalog-download").click()
    oscal_path = tmp_path / "catalog.json"
    oscal_dl.value.save_as(oscal_path)
    catalog = json.loads(oscal_path.read_text())["catalog"]
    assert catalog["metadata"]["oscal-version"] == "1.1.2"
    risks = [
        r for r in catalog.get("back-matter", {}).get("resources", [])
        if any(p.get("name") == "identified-risk-id" for p in r.get("props", []))
    ]
    assert risks
    control = catalog["groups"][0]["controls"][0]
    assert any(p.get("name") == "treats-risk" for p in control.get("props", []))


def test_clause_path_lists_clauses_then_statements(page):
    choose_clause_path(page)
    add_flow_clauses(page, CLAUSE)
    page.click("#clause-continue")
    page.locator("#statements-editor textarea").first.fill(LOCK)
    page.locator("#statements-editor textarea").first.blur()
    page.click("#statements-continue")
    expect(page.locator("#legacy-risk-prompt")).to_be_visible()
    page.fill("#link-risk-statement", UNLOCKED)
    page.click("#link-risk-add")
    page.click("#link-remaining")
    page.click("#flow-next")
    expect(page.locator("#review-page")).to_be_visible()
    expect(page.locator("#review-summary")).to_contain_text(CLAUSE)
    expect(page.locator("#review-summary")).to_contain_text(LOCK)
    expect(page.locator("#review-handoff")).to_be_enabled()


def test_edit_jumps_back_without_losing_draft(page):
    _finish_risk_path(page)
    page.click("#review-edit-statements")
    expect(page.locator("#statements-page")).to_be_visible()
    expect(page.locator("#statements-editor textarea").first).to_have_value(LOCK)
    page.click("#statements-continue")
    expect(page.locator("#review-page")).to_be_visible()
    page.click("#review-edit-risks")
    expect(page.locator("#identify-page")).to_be_visible()
    expect(page.locator("#identify-list .identify-row__statement")).to_have_value(UNLOCKED)


def test_handoff_disabled_when_review_is_incomplete(browser, base_url):
    payload = json.dumps({
        "project": {
            "uuid": "00000000-0000-4000-8000-000000000001",
            "title": "Untitled policy",
            "source": "",
            "authoring_path": "risks",
            "clauses": [],
            "controls": [],
            "risks": [{"id": "R-001", "statement": UNLOCKED, "note": ""}],
        },
        "scores": {},
        "flowStep": "review",
        "saved": "2026-10-24T12:00:00.000Z",
    })
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    context.add_init_script(f"localStorage.setItem('codify:project', {payload!r});")
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    page.click("#resume-open")
    expect(page.locator("#review-page")).to_be_visible()
    expect(page.locator("#review-banner")).to_contain_text("incomplete")
    expect(page.locator("#review-handoff")).to_be_disabled()
    context.close()
