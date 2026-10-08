"""First-visit splash, dismiss persistence, and resume skip."""

import json
import re

from playwright.sync_api import expect

from conftest import finish_open


def _open(browser, base_url, *, splash_seen=False, resume=False, color_scheme="dark"):
    context = browser.new_context(viewport={"width": 1360, "height": 900}, color_scheme=color_scheme)
    if splash_seen:
        context.add_init_script("localStorage.setItem('codify:splash-seen', '1');")
    if resume:
        payload = json.dumps({
            "project": {"title": "Saved policy", "controls": []},
            "saved": "2026-10-07T12:00:00.000Z",
        })
        context.add_init_script(f"localStorage.setItem('codify:project', {payload!r});")
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    return context, page


def test_first_open_shows_splash_instead_of_paste_start(browser, base_url):
    ctx, page = _open(browser, base_url)
    expect(page.locator("#splash")).to_be_visible()
    expect(page.locator("#splash-title")).to_have_text("Welcome to Codify")
    expect(page.locator("#splash-continue")).to_have_text("Get started")
    expect(page.locator("#splash-continue")).to_have_class(re.compile(r"btn--primary"))
    expect(page.locator("#start")).to_be_hidden()
    expect(page.locator("#paste-submit")).to_be_hidden()
    ctx.close()


def test_get_started_reveals_paste_start_and_persists(browser, base_url):
    ctx, page = _open(browser, base_url)
    page.click("#splash-continue")
    expect(page.locator("#splash")).to_be_hidden()
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#paste-submit")).to_be_visible()
    expect(page.locator("#paste-submit")).to_have_text("Codify")
    expect(page.locator("#start .btn--primary:visible")).to_have_count(1)
    assert page.evaluate("localStorage.getItem('codify:splash-seen')") == "1"

    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#splash")).to_be_hidden()
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#paste-submit")).to_have_text("Codify")
    ctx.close()


def test_seen_flag_skips_splash(browser, base_url):
    ctx, page = _open(browser, base_url, splash_seen=True)
    expect(page.locator("#splash")).to_be_hidden()
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#paste-submit")).to_have_text("Codify")
    ctx.close()


def test_resume_skips_splash_even_when_unseen(browser, base_url):
    ctx, page = _open(browser, base_url, resume=True)
    expect(page.locator("#splash")).to_be_hidden()
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#resume")).to_be_visible()
    expect(page.locator("#resume-title")).to_contain_text("Saved policy")
    ctx.close()


def test_try_an_example_works_after_dismiss(browser, base_url):
    ctx, page = _open(browser, base_url)
    page.click("#splash-continue")
    expect(page.locator("#demo")).to_be_visible()
    page.click("#demo")
    finish_open(page)
    expect(page.locator("#work-summary")).to_contain_text("38 control drafts")
    ctx.close()


def test_splash_uses_theme_tokens_in_light_and_dark(browser, base_url):
    ctx, page = _open(browser, base_url, color_scheme="light")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("#splash")).to_be_visible()
    ctx.close()
    ctx, page = _open(browser, base_url, color_scheme="dark")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("#splash")).to_be_visible()
    ctx.close()
