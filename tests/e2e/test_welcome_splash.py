"""Splash #28 is folded into the landing. Behaviour lives in test_landing.py."""

from playwright.sync_api import expect


def test_first_open_has_no_splash(page):
    expect(page.locator("#splash")).to_have_count(0)
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#start-from-risks")).to_be_visible()
