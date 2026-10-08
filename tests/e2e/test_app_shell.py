"""App shell: sidebar, catalog, properties, export dialog, accept shortcut."""

from playwright.sync_api import expect


def test_sidebar_lists_the_authoring_destinations(page):
    nav = page.locator("nav.sidebar__nav")
    expect(nav.get_by_role("button", name="Workspace")).to_be_visible()
    expect(nav.get_by_role("button", name="Clauses")).to_be_visible()
    expect(nav.get_by_role("button", name="Risks")).to_be_visible()
    expect(nav.get_by_role("button", name="Catalog")).to_be_visible()
    expect(nav.get_by_role("button", name="Library")).to_be_visible()
    expect(nav.get_by_role("button", name="Export")).to_be_visible()
    expect(nav.get_by_role("button", name="Guide")).to_be_visible()


def test_start_has_a_setup_checklist(page):
    expect(page.locator(".checklist")).to_contain_text("Set up this workspace")
    expect(page.locator(".checklist")).to_contain_text("Paste a clause")


def test_clauses_catalog_and_risks_views(demo):
    expect(demo.locator("#sidebar")).to_be_visible()
    expect(demo.locator("#props")).to_be_visible()
    expect(demo.locator("#props")).to_contain_text("Properties")
    expect(demo.locator("#props")).to_contain_text("Review suggestions")
    expect(demo.locator("#props")).to_contain_text("Source")
    expect(demo.locator("#props")).not_to_contain_text("null")
    expect(demo.locator(".subitems")).to_be_visible()

    demo.click("[data-nav='catalog']")
    expect(demo.locator("#catalog:not([hidden])")).to_be_visible()
    expect(demo.locator(".data-table")).to_contain_text("Source")
    expect(demo.locator(".data-table")).to_contain_text("Clause")

    demo.click("[data-nav='risks']")
    expect(demo.locator("#risks:not([hidden])")).to_be_visible()
    expect(demo.locator("#risks")).to_contain_text("No risks yet.")

    demo.click("[data-nav='library']")
    expect(demo.locator("#library:not([hidden])")).to_be_visible()
    expect(demo.locator("#library")).to_contain_text("No statements saved yet")


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


def test_export_from_the_sidebar_needs_a_policy(page):
    page.click("[data-nav='export']")
    expect(page.locator("#error")).to_contain_text("Load a policy before exporting")
