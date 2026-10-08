"""Start hierarchy and empty-state next steps in the browser."""

import re

from playwright.sync_api import expect

from conftest import finish_open


def test_start_has_one_primary_and_a_quiet_example(page):
    expect(page.locator("#start .btn--primary:visible")).to_have_count(1)
    expect(page.locator("#paste-submit")).to_have_text("Codify")
    expect(page.locator("#demo")).to_have_text("Try an example")
    expect(page.locator("#demo")).not_to_have_class("btn--primary")
    expect(page.locator("#file")).to_be_attached()
    expect(page.locator(".start__cta")).to_have_count(0)
    expect(page.get_by_text("Or load your policy")).to_have_count(0)
    expect(page.locator("#paste-form input[name='title']")).to_have_count(0)


def test_start_has_no_club_or_version_chrome(page):
    expect(page.get_by_text("GRC Engineering Club Singapore")).to_have_count(0)
    expect(page.get_by_text("open source (MIT)")).to_have_count(0)
    expect(page.locator("footer")).to_have_count(0)
    expect(page.locator("#version")).to_have_count(0)
    expect(page.get_by_text(re.compile(r"Version \d+\.\d+"))).to_have_count(0)


def test_example_chip_still_opens_the_acme_demo(page):
    page.click("#demo")
    finish_open(page)
    expect(page.locator("#work-summary")).to_contain_text("38 control drafts")


def test_filter_empty_state_can_show_all(demo):
    demo.click("#work-more summary")
    demo.click("[data-filter='accepted']")
    expect(demo.locator("#list .empty")).to_be_visible()
    expect(demo.locator("#list")).to_contain_text("Nothing matches this filter.")
    demo.click("#list >> text=Show all")
    expect(demo.locator("#list .ctl").first).to_be_visible()
    expect(demo.locator("[data-filter='all']")).to_have_attribute("aria-pressed", "true")


def test_editor_empty_state_opens_the_first_draft(demo):
    demo.click("#work-title")
    demo.keyboard.press("Escape")
    expect(demo.locator("#editor .empty")).to_be_visible()
    expect(demo.locator("#editor")).to_contain_text("Select a clause to draft its control.")
    demo.click("#editor >> text=Open first draft")
    expect(demo.locator("textarea.statement")).to_be_visible()
