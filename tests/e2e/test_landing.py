"""Marketing landing: Get started opens the risk flow, clause link, Resume."""

import json

from playwright.sync_api import expect

from conftest import choose_clause_path, choose_risk_path, finish_open, goto_review

HEADLINE = "Controls you can test."
SUBHEAD = (
    "Identified risks and policy clauses become control statements. "
    "Export OSCAL 1.1.2. Test them as Rego."
)


def _open(browser, base_url, *, resume=False, color_scheme="dark", width=1360, height=900):
    context = browser.new_context(
        viewport={"width": width, "height": height}, color_scheme=color_scheme
    )
    if resume:
        payload = json.dumps({
            "project": {"title": "Saved policy", "controls": []},
            "saved": "2026-10-07T12:00:00.000Z",
        })
        context.add_init_script(f"localStorage.setItem('codify:project', {payload!r});")
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    return context, page


def test_first_open_is_a_marketing_landing(browser, base_url):
    ctx, page = _open(browser, base_url)
    expect(page.locator("#splash")).to_have_count(0)
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#landing-flow")).to_have_count(0)
    expect(page.locator(".flow-card")).to_have_count(0)
    expect(page.locator("#sidebar")).to_be_hidden()
    expect(page.locator("#landing-bar")).to_be_visible()
    expect(page.locator("#landing-docs")).to_be_visible()
    expect(page.locator("#landing-docs")).to_have_text("Docs")
    expect(page.locator("#landing-github")).to_be_visible()
    expect(page.locator("#landing-github")).to_have_text("GitHub")
    expect(page.locator("#landing-nav-start")).to_have_count(0)
    expect(page.locator("#start-title")).to_have_text(HEADLINE)
    expect(page.locator("#landing-subhead")).to_contain_text(SUBHEAD)
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#start-from-risks")).to_have_text("Get started with identified risks")
    expect(page.locator("#landing-cta-start")).to_have_text("Get started")
    expect(page.locator("#start-from-clause")).to_be_visible()
    expect(page.locator("#start-from-clause")).to_have_text("Get started with an existing policy clause")
    expect(page.locator("#landing-privacy-badge")).to_contain_text("Private by design: runs in your browser")
    expect(page.locator("#landing-mock")).to_contain_text("Customer data stored unencrypted")
    expect(page.locator("#landing-mock")).to_contain_text("Encrypt customer data at rest")
    expect(page.locator("#landing-mock")).to_contain_text("sc-28")
    expect(page.locator("#landing-mock")).to_contain_text("deny contains msg if")
    expect(page.locator("#landing-chips")).to_have_count(0)
    expect(page.locator("#landing-scroll")).to_have_count(0)
    expect(page.locator("#landing-features")).to_have_count(0)
    expect(page.locator("#how-it-works")).to_contain_text("How it works")
    expect(page.locator("#how-it-works")).to_contain_text("Rego")
    expect(page.locator("#landing-trust")).to_contain_text("NIST 800-53")
    expect(page.locator("#landing-trust")).to_contain_text("ISO 27001")
    expect(page.locator("#landing-trust")).to_contain_text("OSCAL 1.1.2")
    expect(page.locator("#landing-trust")).to_contain_text("Runs in your browser")
    expect(page.locator("#landing-trust")).to_contain_text("No data leaves your device")
    expect(page.locator("#landing-trust")).not_to_contain_text("SOC 2")
    expect(page.locator("#landing-contribute")).to_contain_text("Star or contribute on GitHub")
    expect(page.locator("#landing-star")).to_be_visible()
    expect(page.locator("#landing-template")).to_have_text("Contribute a control template")
    expect(page.locator("#landing-enact")).to_have_text("Enact")
    expect(page.locator("#landing-enact")).to_have_attribute("href", "https://github.com/code1sentinel/enact")
    expect(page.locator("#landing-mock")).to_be_visible()
    expect(page.locator("#landing-cta")).to_be_visible()
    expect(page.locator("#landing-footer")).to_be_visible()
    expect(page.locator(".checklist")).to_have_count(0)
    expect(page.get_by_text("Set up this workspace")).to_have_count(0)
    expect(page.get_by_text("Open a saved project")).to_have_count(0)
    expect(page.locator("#resume")).to_be_hidden()
    ctx.close()


def test_start_from_risks_get_started_opens_path_a(page):
    expect(page.locator("#start-from-risks")).to_have_text("Get started with identified risks")
    expect(page.locator("#start-from-risks")).not_to_contain_text("Recommended")
    choose_risk_path(page)
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#identify-steps")).to_be_visible()
    expect(page.locator("#flow-risk-statement")).to_be_visible()


def test_cta_get_started_opens_the_risk_flow(page):
    page.click("#landing-cta-start")
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#flow-risk-statement")).to_be_visible()


def test_start_from_clause_link_opens_path_b(page):
    expect(page.locator("#start-from-clause")).to_have_text("Get started with an existing policy clause")
    choose_clause_path(page)
    expect(page.locator("#paste-form")).to_be_visible()
    expect(page.locator("#paste-submit")).to_have_text("Codify")
    expect(page.locator("#demo")).to_be_visible()


def test_resume_your_project_opens_the_saved_project(browser, base_url):
    payload = json.dumps({
        "project": {
            "uuid": "00000000-0000-4000-8000-000000000000",
            "title": "Saved policy",
            "source": "",
            "clauses": [{
                "id": "c1", "text": "Users shall lock screens.", "section": "0", "heading": "",
                "type": "requirement", "reason": "shall", "duplicate_of": None,
            }],
            "controls": [{
                "id": "c1", "clause": "c1", "text": "Require users to lock screens.",
                "guidance": "", "risk": "Screens left unlocked.", "who": "", "notes": [],
                "status": "draft", "origin": "rules", "source_type": "clause", "risk_ids": [],
            }],
            "risks": [],
        },
        "scores": {},
        "saved": "2026-10-14T12:00:00.000Z",
    })
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    context.add_init_script(f"localStorage.setItem('codify:project', {payload!r});")
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#start-from-clause")).to_be_visible()
    expect(page.locator("#resume")).to_be_visible()
    expect(page.locator("#resume-open")).to_have_text("Resume your project")
    expect(page.locator("#resume-open")).not_to_have_class("btn--primary")
    expect(page.locator("#resume-discard")).to_have_count(0)
    page.click("#resume-open")
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#legacy-risk-prompt")).to_contain_text("started from clauses")
    context.close()


def test_landing_is_keyboard_reachable_and_stacks_on_mobile(browser, base_url):
    ctx, page = _open(browser, base_url, width=390, height=844)
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#start-from-clause")).to_be_visible()
    expect(page.locator("#landing-mock")).to_be_visible()
    risk = page.locator("#start-from-risks").bounding_box()
    clause = page.locator("#start-from-clause").bounding_box()
    assert risk and clause
    assert clause["y"] > risk["y"] + risk["height"] - 2
    overflow = page.evaluate(
        """() => {
          const row = document.querySelector('.landing-hero__cta-row');
          if (!row) return true;
          return row.scrollWidth > row.clientWidth + 1;
        }"""
    )
    assert overflow is False
    page.locator("#start-from-risks").focus()
    expect(page.locator("#start-from-risks")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    ctx.close()


def test_landing_uses_theme_tokens_in_light_and_dark(browser, base_url):
    ctx, page = _open(browser, base_url, color_scheme="light")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("#start-from-risks")).to_be_visible()
    hero = page.locator(".landing-hero")
    bg = hero.evaluate("el => getComputedStyle(el).backgroundColor")
    assert bg not in ("rgb(0, 82, 255)", "rgba(0, 82, 255, 1)")
    color = page.locator("#start-title").evaluate("el => getComputedStyle(el).color")
    assert color in ("rgb(22, 24, 29)", "rgba(22, 24, 29, 1)")
    ctx.close()
    ctx, page = _open(browser, base_url, color_scheme="dark")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("#start-from-risks")).to_be_visible()
    hero = page.locator(".landing-hero")
    bg = hero.evaluate("el => getComputedStyle(el).backgroundColor")
    assert bg not in ("rgb(0, 82, 255)", "rgba(0, 82, 255, 1)")
    color = page.locator("#start-title").evaluate("el => getComputedStyle(el).color")
    assert color in ("rgb(241, 242, 245)", "rgba(241, 242, 245, 1)")
    ctx.close()


def test_try_an_example_still_works_from_the_clause_link(page):
    choose_clause_path(page)
    page.click("#demo")
    finish_open(page)
    goto_review(page)
    expect(page.locator("#work-summary")).to_contain_text("38 control drafts")
