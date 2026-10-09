"""Second first-time GRC walkthrough: accepted state, [N], first look, nav, export."""

import re

from playwright.sync_api import expect

from conftest import finish_open


EXAMPLE = (
    "Access to systems shall be granted on a need-to-know basis.\n\n"
    "User accounts shall be reviewed regularly."
)


def open_example(page):
    page.fill("#paste-form textarea", EXAMPLE)
    page.click("#paste-submit")
    page.wait_for_selector("#result:not([hidden])", timeout=120_000)


def test_first_look_card_shows_and_more_for_acme(page):
    page.click("#demo")
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
    work = page.locator("#work").inner_text().lower()
    assert work.count("say why this control exists") <= 1
    expect(page.locator("#editor .subitems")).to_have_count(1)
    expect(page.locator("#editor .parts")).to_have_count(0)
    expect(page.locator(".flow__caption")).to_be_visible()
    expect(page.locator("#work-counts")).to_contain_text("requirements drafted into")


def test_n_placeholder_is_a_set_this_value_prompt(page):
    open_example(page)
    finish_open(page)
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
    expect(page.locator("#work-title")).not_to_have_value("pasted text")
    title = page.locator("#work-title").input_value()
    assert "Access" in title or title == "Untitled policy"
    page.fill("#work-title", "Need-to-know policy")
    page.locator("#work-title").blur()
    expect(page.locator("#crumb")).to_contain_text("Need-to-know policy")
    page.click("[data-nav='workspace']")
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#current-project:not([hidden])")).to_be_visible()
    expect(page.locator("#current-project")).to_contain_text("Need-to-know policy")
    expect(page.locator("#work")).to_be_hidden()
    page.click("#current-project-open")
    expect(page.locator("#work:not([hidden])")).to_be_visible()


def test_library_lists_a_statement_once(page):
    open_example(page)
    finish_open(page)
    page.click("#accept-control")
    page.click("[data-nav='library']")
    statement = "Grant access to systems on a need-to-know basis."
    body = page.locator("#library").inner_text()
    assert body.count(statement) == 1
    expect(page.locator("#library-detail .library-detail__statement")).to_have_count(1)
    expect(page.locator("#library-detail")).to_contain_text("OSCAL")
    expect(page.locator("#catalog .view-head__lede, #library .view-head__lede").first).to_be_attached()


def test_oscal_tab_has_a_visible_explanation(page):
    open_example(page)
    finish_open(page)
    page.get_by_role("tab", name="OSCAL JSON").click()
    expect(page.locator(".oscal-view__help")).to_contain_text("NIST")
    page.click("[data-nav='catalog']")
    expect(page.locator("#catalog")).to_contain_text("OSCAL")
    expect(page.locator("#catalog")).to_contain_text("Library")
