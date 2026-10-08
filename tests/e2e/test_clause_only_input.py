"""Browser: the start form is clause text only; numbers are not shown."""

from playwright.sync_api import expect

from conftest import finish_open


def test_start_form_has_no_title_field(page):
    expect(page.locator("#paste-form")).to_be_visible()
    expect(page.locator("#paste-form input[name='title']")).to_have_count(0)
    expect(page.locator("#paste-form textarea[name='text']")).to_be_visible()


def test_unnumbered_paste_opens_a_control(page):
    page.fill("#paste-form textarea", "Users shall lock screens when they leave their desk.")
    page.click("#paste-submit")
    finish_open(page)
    expect(page.locator(".clause__text")).to_contain_text("Users shall lock screens")
    expect(page.locator(".clause__id")).to_have_count(0)
    expect(page.locator(".ctl__id")).to_have_count(0)
    expect(page.locator("textarea.statement")).to_be_visible()


def test_workspace_hides_clause_numbers(demo):
    expect(demo.locator(".clause__id")).to_have_count(0)
    expect(demo.locator(".ctl__id")).to_have_count(0)
    expect(demo.locator(".editor__where")).not_to_contain_text("5.1")
    expect(demo.locator(".legacy__label")).to_have_text("Legacy clause")
