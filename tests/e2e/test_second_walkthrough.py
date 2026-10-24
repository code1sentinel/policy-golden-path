"""Second first-time GRC walkthrough: accepted state, [N], first look, nav, export."""

import re

from playwright.sync_api import expect

from conftest import add_flow_clauses, choose_clause_path, finish_open, goto_review, goto_workspace, open_acme_demo


EXAMPLE = (
    "Access to systems shall be granted on a need-to-know basis.\n\n"
    "User accounts shall be reviewed regularly."
)


def open_example(page):
    choose_clause_path(page)
    add_flow_clauses(page, *EXAMPLE.split("\n\n"))
    page.click("#clause-continue")
    statements = [
        "Grant access to systems on a need-to-know basis.",
        "Review user accounts at least every [N] days.",
    ]
    items = page.locator("#statements-list [data-statement-item]")
    for i in range(items.count()):
        items.nth(i).click()
        area = page.locator("#statements-editor textarea").first
        area.fill(statements[i] if i < len(statements) else statements[0])
        area.blur()


def test_first_look_card_shows_and_more_for_acme(page):
    open_acme_demo(page)
    page.wait_for_selector("#result:not([hidden])", timeout=120_000)
    expect(page.locator("#result-drafts")).to_contain_text("Draft 1")
    expect(page.locator("#result-drafts")).to_contain_text("Draft 3")
    expect(page.locator("#result-drafts")).to_contain_text("and 35 more")
    lede = page.locator("#result-lede")
    expect(lede).to_contain_text("duplicate")
    expect(lede).to_contain_text("context")


def test_accept_becomes_accepted_with_next_primary_and_undo(page):
    open_example(page)
    finish_open(page)
    goto_review(page)
    goto_workspace(page)
    expect(page.locator("#accept-control")).to_have_text("Accept")
    expect(page.locator("#next-control")).not_to_have_class(re.compile(r"btn--primary"))
    page.click("#accept-control")
    expect(page.locator("#accept-control")).to_contain_text("Accepted")
    expect(page.locator("#next-control")).to_have_class(re.compile(r"btn--primary"))
    expect(page.locator("#undo-accept")).to_be_visible()
    expect(page.locator("#props")).to_contain_text("Optional")
    page.click("#undo-accept")
    expect(page.locator("#accept-control")).to_have_text("Accept")
    expect(page.locator(".state--accepted")).to_have_count(0)


def test_review_does_not_repeat_parts_or_say_why(page):
    open_example(page)
    finish_open(page)
    goto_review(page)
    goto_workspace(page)
    work = page.locator("#work").inner_text().lower()
    assert work.count("say why this control exists") <= 1
    expect(page.locator("#editor .subitems")).to_have_count(1)
    expect(page.locator("#editor .parts")).to_have_count(0)
    expect(page.locator(".flow__caption")).to_be_visible()
    expect(page.locator("#work-counts")).to_contain_text("requirements drafted into")


def test_n_placeholder_is_a_set_this_value_prompt(page):
    open_example(page)
    finish_open(page)
    goto_review(page)
    goto_workspace(page)
    page.locator("#list .ctl__open", has_text="[N]").click()
    prompt = page.locator(".param-prompt")
    expect(prompt).to_be_visible()
    expect(prompt).to_contain_text("Set this value")
    expect(prompt.locator(".param-token")).to_contain_text("[N]")
    prompt.locator("input").fill("90")
    prompt.get_by_role("button", name="Set").click()
    value = page.locator("textarea.statement").input_value()
    assert "[90]" in value
    assert "[N]" not in value


def test_export_hides_library_behind_optional_and_drops_save_file(page):
    open_example(page)
    finish_open(page)
    goto_review(page)
    goto_workspace(page)
    page.click("#export-open-top")
    dialog = page.locator("#export-dialog")
    expect(dialog).to_contain_text("recommended")
    expect(dialog).to_contain_text("OSCAL")
    expect(dialog).not_to_contain_text("save file")
    expect(dialog.locator(".export-list__row--recommended, .export-list__row.is-recommended")).to_contain_text("OSCAL")
    expect(dialog.locator(".export-more")).to_contain_text("Statement library")
    expect(dialog.locator(".export-more[open]")).to_have_count(0)


def test_workspace_opens_start_and_pasted_title_is_not_pasted_text(page):
    open_example(page)
    finish_open(page)
    goto_review(page)
    goto_workspace(page)
    expect(page.locator("#work-title")).not_to_have_value("pasted text")
    title = page.locator("#work-title").input_value()
    assert "Access" in title or title == "Untitled policy"
    page.fill("#work-title", "Need-to-know policy")
    page.locator("#work-title").blur()
    expect(page.locator("#crumb")).to_contain_text("Need-to-know policy")
    page.click("[data-nav='home']")
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#resume:not([hidden])")).to_be_visible()
    expect(page.locator("#resume")).to_contain_text("Need-to-know policy")
    expect(page.locator("#work")).to_be_hidden()
    page.click("#resume-open")
    expect(page.locator("#work:not([hidden])")).to_be_visible()


def test_library_lists_a_statement_once(page):
    open_example(page)
    finish_open(page)
    goto_review(page)
    goto_workspace(page)
    page.click("#accept-control")
    statement = "Grant access to systems on a need-to-know basis."
    page.wait_for_function("() => Boolean(localStorage.getItem('codify:statements'))")
    store = page.evaluate("localStorage.getItem('codify:statements')")
    assert store and store.count(statement) == 1
    page.click("#library-from")
    expect(page.locator("#library-pick")).to_contain_text(statement)
    expect(page.locator("#library-pick")).to_contain_text("OSCAL")
    expect(page.locator("#library-pick .library-detail__statement")).to_have_count(1)


def test_oscal_tab_has_a_visible_explanation(page):
    open_example(page)
    finish_open(page)
    goto_review(page)
    goto_workspace(page)
    page.get_by_role("tab", name="OSCAL JSON").click()
    expect(page.locator(".oscal-view__help")).to_contain_text("NIST")
    expect(page.locator("#catalog")).to_be_attached()
    expect(page.locator("#library")).to_be_attached()
