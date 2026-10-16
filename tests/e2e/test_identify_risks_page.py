"""Identify risks page (Flow A step 1): add, edit, remove, Continue, back."""

import json

from playwright.sync_api import expect

from conftest import add_flow_risk, choose_risk_path

EXAMPLE = "Unauthorised access to customer data due to shared admin accounts"
UNLOCKED = "Screens left unlocked at unattended desks."


def test_identify_page_shows_title_steps_empty_state_and_disabled_continue(page):
    choose_risk_path(page)
    expect(page.locator("#identify-title")).to_have_text("What risks have you identified?")
    expect(page.locator("#identify-lede")).to_be_visible()
    expect(page.locator("#identify-steps")).to_contain_text("Identify risks")
    expect(page.locator("#identify-steps")).to_contain_text("Control statements")
    expect(page.locator("#identify-steps")).to_contain_text("Policy as code (Rego)")
    expect(page.locator("#identify-steps [aria-current='step']")).to_contain_text("Identify risks")
    expect(page.locator("#identify-back")).to_be_visible()
    expect(page.locator("#identify-empty")).to_be_visible()
    expect(page.locator("#flow-risk-statement")).to_be_visible()
    expect(page.locator("#flow-risk-statement")).to_have_attribute("placeholder", "Add a risk")
    expect(page.locator("#identify-continue")).to_be_disabled()
    expect(page.locator("#identify-tip")).to_contain_text("How to write a good risk statement")
    page.locator("#identify-tip summary").click()
    expect(page.locator("#identify-tip")).to_contain_text(EXAMPLE)


def test_identify_page_hides_wizard_guide_and_next(page):
    choose_risk_path(page)
    expect(page.locator("#step-guide")).to_be_hidden()
    expect(page.locator("#step-guide-open")).to_be_hidden()
    expect(page.locator("#flow-next")).to_be_hidden()
    expect(page.locator("#flow-back")).to_be_hidden()
    expect(page.locator("#flow-error")).to_be_hidden()
    expect(page.locator("#identify-page")).not_to_contain_text("R-001")
    expect(page.locator("#identify-page")).not_to_contain_text("Add at least one identified risk to continue.")
    expect(page.locator("#identify-page")).not_to_contain_text("likelihood")
    expect(page.locator("#identify-page")).not_to_contain_text("Common mistakes")
    expect(page.locator("#identify-page table")).to_have_count(0)


def test_enter_adds_a_risk_and_enables_continue(page):
    choose_risk_path(page)
    expect(page.locator("#identify-continue")).to_be_disabled()
    page.fill("#flow-risk-statement", UNLOCKED)
    page.locator("#flow-risk-statement").press("Enter")
    row = page.locator("#identify-list .identify-row")
    expect(row).to_have_count(1)
    expect(row.locator(".identify-row__statement")).to_have_value(UNLOCKED)
    expect(page.locator("#flow-risk-statement")).to_have_value("")
    expect(page.locator("#flow-risk-statement")).to_be_focused()
    expect(page.locator("#identify-continue")).to_be_enabled()
    expect(page.locator("#identify-empty")).to_have_count(0)
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["risks"][0]["statement"] == UNLOCKED
    assert saved["project"]["risks"][0]["id"] == "R-001"
    assert saved["project"]["risks"][0]["note"] == ""


def test_escape_cancels_the_add_row(page):
    choose_risk_path(page)
    page.fill("#flow-risk-statement", "This should not be saved")
    page.locator("#flow-risk-statement").press("Escape")
    expect(page.locator("#flow-risk-statement")).to_have_value("")
    expect(page.locator("#identify-list .identify-row")).to_have_count(0)
    expect(page.locator("#identify-continue")).to_be_disabled()


def test_edit_statement_and_note_in_place(page):
    choose_risk_path(page)
    add_flow_risk(page, UNLOCKED)
    statement = page.locator("#identify-list .identify-row .identify-row__statement")
    note = page.locator("#identify-list .identify-row .identify-row__note")
    statement.fill(EXAMPLE)
    statement.blur()
    note.fill("From the workshop.")
    note.blur()
    expect(statement).to_have_value(EXAMPLE)
    expect(note).to_have_value("From the workshop.")
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["risks"][0]["statement"] == EXAMPLE
    assert saved["project"]["risks"][0]["note"] == "From the workshop."
    assert saved["project"]["risks"][0]["id"] == "R-001"


def test_remove_last_risk_restores_empty_state_and_focus(page):
    choose_risk_path(page)
    add_flow_risk(page, UNLOCKED)
    page.locator("#identify-list .identify-row__remove").click()
    expect(page.locator("#identify-list .identify-row")).to_have_count(0)
    expect(page.locator("#identify-empty")).to_be_visible()
    expect(page.locator("#identify-continue")).to_be_disabled()
    expect(page.locator("#flow-risk-statement")).to_be_focused()
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["risks"] == []


def test_continue_opens_control_statements(page):
    choose_risk_path(page)
    expect(page.locator("#identify-continue")).to_be_disabled()
    add_flow_risk(page, UNLOCKED, note="From the workshop.")
    page.click("#identify-continue")
    expect(page.locator("#flow-step")).to_contain_text("Develop control statements")
    expect(page.locator("#flow-next")).to_be_visible()


def test_back_link_returns_to_the_landing(page):
    choose_risk_path(page)
    page.click("#identify-back")
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#flow")).to_be_hidden()


def test_identify_page_is_usable_on_a_small_viewport(browser, base_url):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    choose_risk_path(page)
    expect(page.locator("#identify-title")).to_be_visible()
    expect(page.locator("#flow-risk-statement")).to_be_visible()
    expect(page.locator("#identify-continue")).to_be_visible()
    add_flow_risk(page, UNLOCKED)
    expect(page.locator("#identify-continue")).to_be_enabled()
    context.close()
