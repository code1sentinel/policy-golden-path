"""App shell: sidebar, catalog, properties, export dialog, accept shortcut."""

from playwright.sync_api import expect


def test_sidebar_lists_the_authoring_destinations(page):
    page.click("#start-from-risks")
    nav = page.locator("nav.sidebar__nav")
    expect(nav.get_by_role("button", name="Home")).to_be_visible()
    expect(nav.get_by_role("button", name="Risk Entry")).to_be_visible()
    expect(nav.get_by_role("button", name="Policy Clause")).to_be_visible()
    expect(nav.locator(".nav-btn")).to_have_count(3)
    expect(nav.get_by_role("button", name="Catalog")).to_have_count(0)
    expect(nav.get_by_role("button", name="Library")).to_have_count(0)
    expect(nav.get_by_role("button", name="Export")).to_have_count(0)
    expect(nav.get_by_role("button", name="Guide")).to_have_count(0)


def test_start_has_no_setup_checklist(page):
    expect(page.locator(".checklist")).to_have_count(0)
    expect(page.get_by_text("Set up this workspace")).to_have_count(0)
    expect(page.locator("#start-from-risks")).to_be_visible()


def test_clauses_catalog_and_library_views(demo):
    expect(demo.locator("#sidebar")).to_be_visible()
    expect(demo.locator("#props")).to_be_visible()
    expect(demo.locator("#props")).to_contain_text("Properties")
    expect(demo.locator("#props")).to_contain_text("Review suggestions")
    expect(demo.locator("#props")).to_contain_text("Source")
    expect(demo.locator("#props")).not_to_contain_text("null")
    expect(demo.locator(".subitems")).to_be_visible()

    expect(demo.locator("#catalog")).to_be_hidden()
    expect(demo.locator("#library")).to_be_hidden()
    expect(demo.locator("#export-dialog")).to_have_count(1)


def test_ctrl_enter_accepts_the_current_control(demo):
    demo.click("#ctl-5\\.1a .ctl__open")
    demo.locator("textarea.statement").focus()
    demo.keyboard.press("Control+Enter")
    expect(demo.locator("#ctl-5\\.1a .state")).to_have_text("Accepted")


def test_review_accept_and_dismiss(demo):
    expect(demo.locator(".editor__primary .btn--primary")).to_have_text("Accept")
    expect(demo.locator("#props .btn--primary")).to_have_count(0)
    tips = demo.locator("#props .suggestion__actions .btn", has_text="Dismiss")
    if tips.count():
        tips.first.click()
    expect(demo.locator("textarea.statement")).to_be_visible()


def test_export_from_the_toolbar_needs_a_policy(page):
    expect(page.locator("#export-open-top")).to_be_hidden()
    page.click("#start-from-risks")
    expect(page.locator("#export-open-top")).to_be_visible()
