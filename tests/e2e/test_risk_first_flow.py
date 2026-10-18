"""Risk-first authoring: one e2e per start path, plus old clause-first resume."""

import json

from playwright.sync_api import expect

from conftest import add_flow_risk, choose_clause_path, choose_risk_path, finish_open, goto_review


def test_start_offers_two_get_started_paths(page):
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#start-from-risks")).to_have_text("Get started with identified risks")
    expect(page.locator("#start-from-clause")).to_have_text("Get started with an existing policy clause")
    expect(page.locator("#start-from-clause")).to_be_visible()
    expect(page.locator("#paste-form")).to_be_hidden()
    expect(page.locator("#stepper")).to_be_hidden()


def test_path_a_risks_then_controls_then_review_then_enact(page):
    choose_risk_path(page)
    expect(page.locator("#identify-steps")).to_be_visible()
    expect(page.locator("#identify-continue")).to_be_disabled()
    add_flow_risk(
        page, "Screens left unlocked at unattended desks.", note="From the workshop.")
    expect(page.locator("#identify-list .identify-row__statement")).to_have_value(
        "Screens left unlocked at unattended desks.")
    page.click("#identify-continue")
    expect(page.locator("#statements-title")).to_contain_text("control statement for each risk")
    expect(page.locator("#statements-continue")).to_be_disabled()
    page.locator("#statements-editor textarea").first.fill(
        "Require users to lock screens when they leave their desk.")
    page.locator("#statements-editor textarea").first.blur()
    page.click("#statements-continue")
    expect(page.locator("#work:not([hidden])")).to_be_visible()
    expect(page.locator("textarea.statement")).to_be_visible()
    page.locator(".editor__primary >> text=Accept").click()
    page.click("#flow-next")
    expect(page.locator("#enact-step")).to_contain_text("Send to Enact")
    expect(page.locator("#enact-step")).to_contain_text("testable Rego policy")
    expect(page.locator("#stepper")).to_contain_text("Send to Enact")
    expect(page.locator("#enact-download")).to_be_enabled()
    with page.expect_download() as dl:
        page.click("#enact-download")
        oscal = page.locator("#export-dialog [data-export='oscal']")
        if oscal.is_visible():
            oscal.click()
    assert dl.value


def test_path_b_paste_clause_then_link_before_review(page):
    choose_clause_path(page)
    expect(page.locator("#paste-form")).to_be_visible()
    expect(page.locator("#paste-submit")).to_have_text("Codify")
    page.fill("#paste-form textarea", "Users shall lock screens when they leave their desk.")
    page.click("#paste-submit")
    finish_open(page)
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#statements-title")).to_contain_text("for each clause")
    page.click("#statements-continue")
    expect(page.locator("#legacy-risk-prompt")).to_contain_text("risk")
    page.click("#flow-next")
    expect(page.locator("#flow-error")).to_be_visible()
    goto_review(page)
    expect(page.locator("#work:not([hidden]) textarea.statement")).to_be_visible()
    expect(page.locator("#stepper")).to_contain_text("Review")


def test_old_clause_first_project_opens_on_path_b_and_prompts_for_risks(browser, base_url):
    payload = json.dumps({
        "project": {
            "uuid": "00000000-0000-4000-8000-000000000000",
            "title": "Saved policy",
            "source": "",
            "clauses": [{
                "id": "c1", "text": "Users shall lock screens.", "section": "0", "heading": "",
                "type": "requirement", "reason": "shall", "duplicate_of": None,
            }],
            "controls": [{
                "id": "c1", "clause": "c1", "text": "Require users to lock screens.",
                "guidance": "", "risk": "Screens left unlocked.", "who": "", "notes": [],
                "status": "draft", "origin": "rules", "source_type": "clause", "risk_ids": [],
            }],
            "risks": [],
        },
        "scores": {},
        "saved": "2026-10-14T12:00:00.000Z",
    })
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    context.add_init_script(f"localStorage.setItem('codify:project', {payload!r});")
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    expect(page.locator("#resume")).to_be_visible()
    page.click("#resume-open")
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#legacy-risk-prompt")).to_contain_text("started from clauses")
    expect(page.locator("#stepper")).to_contain_text("Link")
    page.click("#export-open-top")
    expect(page.locator("#export-gate")).to_contain_text("risk")
    expect(page.locator("#export-dialog [data-export='oscal']")).to_be_disabled()
    context.close()
