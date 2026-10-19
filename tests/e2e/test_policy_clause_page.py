"""Policy clause page (Flow B step 1): paste, multiple clauses, remove, Continue, old project."""

import json

from playwright.sync_api import expect

from conftest import add_flow_clauses, choose_clause_path

LOCK = "Users shall lock screens when they leave their desk."
NEED = "Access to systems shall be granted on a need-to-know basis."
REVIEW = "User accounts shall be reviewed regularly."


def test_clause_page_shows_title_steps_empty_state_and_disabled_continue(page):
    choose_clause_path(page)
    expect(page.locator("#clause-title")).to_have_text("Paste your policy clause")
    expect(page.locator("#clause-lede")).to_be_visible()
    expect(page.locator("#clause-lede")).to_contain_text("write a control statement for each one next")
    expect(page.locator("#clause-steps")).to_contain_text("Policy clause")
    expect(page.locator("#clause-steps")).to_contain_text("Control statements")
    expect(page.locator("#clause-steps")).to_contain_text("Policy as code (Rego)")
    expect(page.locator("#clause-steps [aria-current='step']")).to_contain_text("Policy clause")
    expect(page.locator("#clause-back")).to_be_visible()
    expect(page.locator("#clause-empty")).to_be_visible()
    expect(page.locator("#clause-paste")).to_be_visible()
    expect(page.locator("#clause-example")).to_be_visible()
    expect(page.locator("#clause-example")).to_contain_text("blank line")
    expect(page.locator("#clause-continue")).to_be_disabled()
    expect(page.locator("#clause-details")).to_contain_text("Add details")


def test_clause_page_hides_codify_demo_file_and_wizard(page):
    choose_clause_path(page)
    expect(page.locator("#step-guide")).to_be_hidden()
    expect(page.locator("#step-guide-open")).to_be_hidden()
    expect(page.locator("#flow-next")).to_be_hidden()
    expect(page.locator("#flow-back")).to_be_hidden()
    expect(page.locator("#flow-error")).to_be_hidden()
    expect(page.locator("#clause-page")).not_to_contain_text("Codify")
    expect(page.locator("#clause-page")).not_to_contain_text("Try an example")
    expect(page.locator("#clause-page")).not_to_contain_text("Open a file")
    expect(page.locator("#clause-page")).not_to_contain_text("Example clause")
    expect(page.locator("#clause-page")).not_to_contain_text("Common mistakes")
    expect(page.locator("#clause-page")).not_to_contain_text("here's what we drafted")
    expect(page.locator("#clause-page table")).to_have_count(0)
    expect(page.locator("#clause-page input[name='title']")).to_have_count(0)
    expect(page.locator("#paste-submit")).to_have_count(0)


def test_paste_one_clause_enables_continue(page):
    choose_clause_path(page)
    expect(page.locator("#clause-continue")).to_be_disabled()
    add_flow_clauses(page, LOCK)
    row = page.locator("#clause-list .clause-row")
    expect(row).to_have_count(1)
    expect(row.locator(".clause-row__text")).to_have_value(LOCK)
    expect(page.locator("#clause-paste")).to_have_value("")
    expect(page.locator("#clause-continue")).to_be_enabled()
    expect(page.locator("#clause-empty")).to_have_count(0)
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["clauses"][0]["text"] == LOCK
    assert saved["project"]["clauses"][0]["id"] == "c1"
    assert "authoring_path" not in saved["project"]


def test_blank_line_splits_into_editable_clauses(page):
    choose_clause_path(page)
    add_flow_clauses(page, NEED, REVIEW)
    rows = page.locator("#clause-list .clause-row")
    expect(rows).to_have_count(2)
    expect(rows.nth(0).locator(".clause-row__text")).to_have_value(NEED)
    expect(rows.nth(1).locator(".clause-row__text")).to_have_value(REVIEW)
    rows.nth(1).locator(".clause-row__text").fill(LOCK)
    rows.nth(1).locator(".clause-row__text").blur()
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert [c["text"] for c in saved["project"]["clauses"]] == [NEED, LOCK]
    assert [c["id"] for c in saved["project"]["clauses"]] == ["c1", "c2"]


def test_remove_last_clause_restores_empty_state_and_focus(page):
    choose_clause_path(page)
    add_flow_clauses(page, LOCK)
    page.locator("#clause-list .clause-row__remove").click()
    expect(page.locator("#clause-list .clause-row")).to_have_count(0)
    expect(page.locator("#clause-empty")).to_be_visible()
    expect(page.locator("#clause-continue")).to_be_disabled()
    expect(page.locator("#clause-paste")).to_be_focused()
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["clauses"] == []


def test_continue_opens_control_statements_for_each_clause(page):
    choose_clause_path(page)
    expect(page.locator("#clause-continue")).to_be_disabled()
    add_flow_clauses(page, LOCK)
    page.click("#clause-continue")
    expect(page.locator("#statements-title")).to_have_text(
        "Write a control statement for each clause")
    expect(page.locator("#statements-steps")).to_contain_text("Policy clause")
    expect(page.locator("#statements-list [data-statement-item]")).to_have_count(1)
    expect(page.locator("#statements-source")).to_contain_text("lock screens")
    expect(page.locator("#flow-next")).to_be_hidden()
    expect(page.locator("#result")).to_be_hidden()


def test_continue_stays_disabled_until_a_clause_exists(page):
    choose_clause_path(page)
    expect(page.locator("#clause-continue")).to_be_disabled()
    page.fill("#clause-paste", "   ")
    expect(page.locator("#clause-continue")).to_be_disabled()
    page.fill("#clause-paste", LOCK)
    expect(page.locator("#clause-continue")).to_be_enabled()
    page.click("#clause-continue")
    expect(page.locator("#statements-title")).to_have_text(
        "Write a control statement for each clause")


def test_back_link_returns_to_the_landing(page):
    choose_clause_path(page)
    page.click("#clause-back")
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#start-from-clause")).to_be_visible()
    expect(page.locator("#flow")).to_be_hidden()


def test_old_clause_project_opens_on_this_page(browser, base_url):
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
    page.click("#resume-open")
    page.click("[data-nav='policy-clause']")
    expect(page.locator("#clause-title")).to_have_text("Paste your policy clause")
    expect(page.locator("#clause-list .clause-row__text")).to_have_value("Users shall lock screens.")
    expect(page.locator("#clause-continue")).to_be_enabled()
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["clauses"][0]["id"] == "c1"
    assert saved["project"]["controls"][0]["id"] == "c1"
    page.click("#clause-continue")
    expect(page.locator("#statements-title")).to_have_text(
        "Write a control statement for each clause")
    expect(page.locator("#statements-editor textarea").first).to_have_value(
        "Require users to lock screens.")
    context.close()


def test_clause_page_is_usable_on_a_small_viewport(browser, base_url):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    choose_clause_path(page)
    expect(page.locator("#clause-title")).to_be_visible()
    expect(page.locator("#clause-paste")).to_be_visible()
    expect(page.locator("#clause-example")).to_be_visible()
    expect(page.locator("#clause-continue")).to_be_visible()
    add_flow_clauses(page, LOCK)
    expect(page.locator("#clause-continue")).to_be_enabled()
    overflow = page.evaluate(
        """() => document.documentElement.scrollWidth > window.innerWidth + 1"""
    )
    assert overflow is False
    context.close()
