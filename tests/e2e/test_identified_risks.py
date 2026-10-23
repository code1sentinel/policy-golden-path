"""Identified risks as input: add, coverage flags, library suggestions, mapped links."""

import json

from playwright.sync_api import expect

from conftest import add_flow_clauses, add_flow_risk, choose_clause_path, choose_risk_path, goto_review
from test_statement_library import CLAUSE, accept_current, open_pasted, wait_for_library_entries


def test_add_identified_risk_and_flag_uncovered(page):
    choose_risk_path(page)
    add_flow_risk(page, "Company data is breached due to human error.", note="From the workshop.")
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert saved["project"]["risks"][0]["statement"] == "Company data is breached due to human error."
    assert saved["project"]["risks"][0]["note"] == "From the workshop."
    assert saved["project"]["risks"][0]["id"] == "R-001"
    page.click("#identify-continue")
    expect(page.locator("#statements-list [data-covered='false']")).to_be_visible()
    expect(page.locator("#statements-list [aria-label='Not covered']")).to_be_visible()


def test_suggest_dialog_adds_library_statement_and_clears_coverage(page):
    open_pasted(page, CLAUSE)
    accept_current(page)
    wait_for_library_entries(page, 1)
    page.click("[data-nav='risk-entry']")
    add_flow_risk(page, "Access that is no longer needed could be misused.")
    page.click("#identify-continue")
    page.click("#statements-library")
    expect(page.locator("#risk-suggest-dialog")).to_be_visible()
    expect(page.locator("#risk-suggest-dialog")).not_to_contain_text("null")
    expect(page.locator("#risk-suggest-scenario")).to_contain_text("Access that is no longer needed")
    expect(page.locator(".risk-suggest__row")).to_contain_text("need-to-know")
    page.locator(".risk-suggest__row button", has_text="Add").first.click()
    page.locator("#risk-suggest-not-now").click()
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    linked = [c for c in saved["project"]["controls"] if "R-001" in (c.get("risk_ids") or [])]
    assert linked
    page.click("#statements-continue")
    goto_review(page)
    expect(page.locator("#editor .mapped-risk").first).to_be_visible()
    expect(page.locator("#editor .mapped-risk").first).to_contain_text("R-001")


def test_unlinked_control_is_flagged_in_related_table(page):
    choose_clause_path(page)
    add_flow_clauses(page, CLAUSE)
    page.click("#clause-continue")
    page.locator("#statements-editor textarea").first.fill(
        "Grant access to systems on a need-to-know basis.")
    page.locator("#statements-editor textarea").first.blur()
    page.click("#statements-continue")
    expect(page.locator("#flow-step")).to_contain_text("This control is not linked to a risk.")
    expect(page.locator("#legacy-risk-prompt")).to_contain_text("risk")
