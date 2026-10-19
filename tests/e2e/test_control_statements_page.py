"""Control statements page (shared step 2): select, edit, coverage, Continue."""

import json

from playwright.sync_api import expect

from conftest import add_flow_clauses, add_flow_risk, choose_clause_path, choose_risk_path

UNLOCKED = "Screens left unlocked at unattended desks."
SHARED = "Shared admin accounts on customer systems."
LOCK = "Require users to lock screens when they leave their desk."
ENCRYPT = (
    "Customer data at rest is encrypted with AES-256 using managed keys; "
    "encryption is verified monthly by automated scan."
)
CLAUSE = "Users shall lock screens when they leave their desk."


def _open_statements(page, *risks):
    choose_risk_path(page)
    for statement in risks:
        add_flow_risk(page, statement)
    page.click("#identify-continue")
    expect(page.locator("#statements-title")).to_be_visible()


def test_statements_page_shows_title_steps_tip_and_disabled_continue(page):
    _open_statements(page, UNLOCKED)
    expect(page.locator("#statements-title")).to_have_text(
        "Write a control statement for each risk")
    expect(page.locator("#statements-lede")).to_be_visible()
    expect(page.locator("#statements-steps")).to_contain_text("Identify risks")
    expect(page.locator("#statements-steps")).to_contain_text("Control statements")
    expect(page.locator("#statements-steps")).to_contain_text("Policy as code (Rego)")
    expect(page.locator("#statements-steps [aria-current='step']")).to_contain_text(
        "Control statements")
    expect(page.locator("#statements-back")).to_be_visible()
    expect(page.locator("#statements-progress")).to_contain_text("0 of 1 risk covered")
    expect(page.locator("#statements-continue")).to_be_disabled()
    expect(page.locator("#statements-tip")).to_contain_text(
        "What makes a good control statement")
    page.locator("#statements-tip summary").click()
    expect(page.locator("#statements-tip")).to_contain_text(ENCRYPT)


def test_statements_page_hides_wizard_guide_and_clutter(page):
    _open_statements(page, UNLOCKED)
    expect(page.locator("#step-guide")).to_be_hidden()
    expect(page.locator("#step-guide-open")).to_be_hidden()
    expect(page.locator("#flow-next")).to_be_hidden()
    expect(page.locator("#flow-back")).to_be_hidden()
    expect(page.locator("#flow-error")).to_be_hidden()
    expect(page.locator("#statements-page")).not_to_contain_text("Develop control statements")
    expect(page.locator("#statements-page")).not_to_contain_text("Common mistakes")
    expect(page.locator("#statements-page")).not_to_contain_text("Suggest from library")
    expect(page.locator("#statements-page")).not_to_contain_text("optional")
    expect(page.locator("#statements-page")).not_to_contain_text(
        "Every risk needs at least one control statement.")
    expect(page.locator("#statements-page table")).to_have_count(0)


def test_select_add_edit_remove_statement_updates_coverage(page):
    _open_statements(page, UNLOCKED, SHARED)
    items = page.locator("#statements-list [data-statement-item]")
    expect(items).to_have_count(2)
    expect(items.nth(0)).to_have_attribute("aria-selected", "true")
    expect(page.locator("#statements-source")).to_contain_text(UNLOCKED)
    expect(page.locator("#statements-progress")).to_contain_text("0 of 2 risks covered")
    expect(page.locator("#statements-list [data-covered='true']")).to_have_count(0)

    page.locator("#statements-editor textarea").first.fill(LOCK)
    page.locator("#statements-editor textarea").first.blur()
    expect(page.locator("#statements-progress")).to_contain_text("1 of 2 risks covered")
    expect(page.locator("#statements-list [data-covered='true']")).to_have_count(1)
    expect(page.locator("#statements-continue")).to_be_disabled()

    page.get_by_role("button", name="Add another statement").click()
    areas = page.locator("#statements-editor textarea")
    expect(areas).to_have_count(2)
    areas.nth(1).fill("Review unattended desks every [90] days.")
    areas.nth(1).blur()

    items.nth(1).click()
    expect(items.nth(1)).to_have_attribute("aria-selected", "true")
    expect(page.locator("#statements-source")).to_contain_text(SHARED)
    page.locator("#statements-editor textarea").first.fill(ENCRYPT)
    page.locator("#statements-editor textarea").first.blur()
    expect(page.locator("#statements-progress")).to_contain_text("2 of 2 risks covered")
    expect(page.locator("#statements-continue")).to_be_enabled()

    page.locator("#statements-editor .statements-remove").first.click()
    expect(page.locator("#statements-editor textarea")).to_have_count(1)
    expect(page.locator("#statements-editor textarea").first).to_have_value("")
    expect(page.locator("#statements-progress")).to_contain_text("1 of 2 risks covered")
    expect(page.locator("#statements-continue")).to_be_disabled()

    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    linked = [c for c in saved["project"]["controls"] if "R-001" in (c.get("risk_ids") or [])]
    assert len(linked) == 2
    assert linked[0]["text"] == LOCK
    assert "R-002" not in [rid for c in saved["project"]["controls"] for rid in (c.get("risk_ids") or [])]


def test_continue_disabled_until_full_coverage_then_opens_next_step(page):
    _open_statements(page, UNLOCKED)
    expect(page.locator("#statements-continue")).to_be_disabled()
    page.locator("#statements-editor textarea").first.fill(LOCK)
    page.locator("#statements-editor textarea").first.blur()
    expect(page.locator("#statements-continue")).to_be_enabled()
    page.click("#statements-continue")
    expect(page.locator("#work:not([hidden])")).to_be_visible()
    expect(page.locator("textarea.statement")).to_be_visible()


def test_clause_flow_uses_clause_label(page):
    choose_clause_path(page)
    add_flow_clauses(page, CLAUSE)
    page.click("#clause-continue")
    expect(page.locator("#statements-title")).to_have_text(
        "Write a control statement for each clause")
    expect(page.locator("#statements-steps")).to_contain_text("Policy clause")
    expect(page.locator("#statements-list [data-statement-item]")).to_have_count(1)
    expect(page.locator("#statements-source")).to_contain_text("lock screens")
    expect(page.locator("#statements-editor textarea").first).to_have_value("")
    expect(page.locator("#statements-continue")).to_be_disabled()


def test_back_link_returns_to_identify_risks(page):
    _open_statements(page, UNLOCKED)
    page.click("#statements-back")
    expect(page.locator("#identify-title")).to_be_visible()
    expect(page.locator("#identify-list .identify-row")).to_have_count(1)
    expect(page.locator("#statements-page")).to_have_count(0)


def test_keyboard_moves_between_items(page):
    _open_statements(page, UNLOCKED, SHARED)
    page.locator("#statements-list").focus()
    page.keyboard.press("ArrowDown")
    expect(page.locator("#statements-list [data-statement-item]").nth(1)).to_have_attribute(
        "aria-selected", "true")
    expect(page.locator("#statements-source")).to_contain_text(SHARED)
    page.keyboard.press("k")
    expect(page.locator("#statements-list [data-statement-item]").nth(0)).to_have_attribute(
        "aria-selected", "true")
    expect(page.locator("#statements-source")).to_contain_text(UNLOCKED)


def test_statements_page_is_usable_on_a_small_viewport(browser, base_url):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    _open_statements(page, UNLOCKED, SHARED)
    expect(page.locator("#statements-title")).to_be_visible()
    expect(page.locator("#statements-list [data-statement-item]")).to_have_count(2)
    page.locator("#statements-list [data-statement-item]").nth(1).click()
    expect(page.locator("#statements-editor textarea")).to_be_visible()
    expect(page.locator("#statements-continue")).to_be_visible()
    context.close()
