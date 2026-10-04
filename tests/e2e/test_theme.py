"""Light / dark / system theme: default, persistence, no extra network."""

from urllib.parse import urlparse

from playwright.sync_api import expect


def _open(browser, base_url, color_scheme="dark", theme_pref=None):
    context = browser.new_context(viewport={"width": 1360, "height": 900}, color_scheme=color_scheme)
    if theme_pref:
        context.add_init_script(f"localStorage.setItem('codify:theme', {theme_pref!r});")
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    page.wait_for_selector("#start:not([hidden])")
    return context, page


def test_system_default_follows_prefers_color_scheme(browser, base_url):
    ctx, page = _open(browser, base_url, color_scheme="light")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("[data-theme-choice='system']")).to_have_attribute("aria-checked", "true")
    ctx.close()
    ctx, page = _open(browser, base_url, color_scheme="dark")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    ctx.close()


def test_theme_toggle_persists_and_system_clears_override(browser, base_url):
    ctx, page = _open(browser, base_url, color_scheme="dark")
    page.click("[data-theme-choice='light']")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("[data-theme-choice='light']")).to_have_attribute("aria-checked", "true")
    assert page.evaluate("localStorage.getItem('codify:theme')") == "light"
    page.reload()
    page.wait_for_selector("#start:not([hidden])")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    page.click("[data-theme-choice='system']")
    assert page.evaluate("localStorage.getItem('codify:theme')") is None
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("[data-theme-choice='system']")).to_have_attribute("aria-checked", "true")
    ctx.close()


def test_theme_toggle_makes_no_third_party_requests(browser, base_url):
    ctx, page = _open(browser, base_url, color_scheme="dark")
    seen = []
    page.on("request", lambda req: seen.append(req.url))
    page.click("[data-theme-choice='light']")
    page.click("[data-theme-choice='dark']")
    page.click("[data-theme-choice='system']")
    hosts = {urlparse(u).hostname for u in seen}
    assert hosts <= {"127.0.0.1", "localhost", None}
    ctx.close()


def test_ai_chip_is_not_a_view_tab(page):
    expect(page.locator("#ai-open")).to_have_text("AI: Off")
    expect(page.locator("nav.views [data-view]")).to_have_count(2)
    expect(page.locator("nav.views #ai-open")).to_have_count(0)
