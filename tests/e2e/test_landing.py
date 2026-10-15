"""Landing: two flow cards, both Get started buttons, and a quiet Resume."""

import json

from playwright.sync_api import expect

from conftest import choose_clause_path, choose_risk_path, finish_open, goto_review

HEADLINE = (
    "Codify turns what you need to address into clear control statements, "
    "which you then test in Enact."
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


def test_first_open_is_two_flow_cards(browser, base_url):
    ctx, page = _open(browser, base_url)
    expect(page.locator("#splash")).to_have_count(0)
    expect(page.locator("#start:not([hidden])")).to_be_visible()
    expect(page.locator("#landing-flow")).to_have_count(0)
    expect(page.get_by_text(HEADLINE)).to_have_count(0)
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#start-from-risks")).to_have_text("Get started")
    expect(page.locator("#start-from-clause")).to_be_visible()
    expect(page.locator("#start-from-clause")).to_have_text("Get started")
    expect(page.locator(".flow-card")).to_have_count(2)
    expect(page.locator(".flow-card").nth(0)).to_contain_text("Identify risk")
    expect(page.locator(".flow-card").nth(0)).to_contain_text("Control statement")
    expect(page.locator(".flow-card").nth(0)).to_contain_text("Technical policy (Rego)")
    expect(page.locator(".flow-card").nth(1)).to_contain_text("Policy clause")
    expect(page.locator(".flow-card").nth(1)).to_contain_text("Control statement")
    expect(page.locator(".flow-card").nth(1)).to_contain_text("Technical policy (Rego)")
    expect(page.locator("#landing-caption")).to_contain_text(
        "Exported as OSCAL and tested as Rego in"
    )
    expect(page.locator("#landing-caption a")).to_have_text("Enact")
    expect(page.locator("#landing-caption a")).to_have_attribute(
        "href", "https://code1sentinel.github.io/enact/"
    )
    expect(page.locator(".checklist")).to_have_count(0)
    expect(page.get_by_text("Set up this workspace")).to_have_count(0)
    expect(page.get_by_text("How to use Codify")).to_have_count(0)
    expect(page.get_by_text("Open a saved project")).to_have_count(0)
    expect(page.locator("#resume")).to_be_hidden()
    ctx.close()


def test_start_from_risks_get_started_opens_path_a(page):
    expect(page.locator("#start-from-risks")).to_have_text("Get started")
    expect(page.locator("#start-from-risks")).not_to_contain_text("Recommended")
    choose_risk_path(page)
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#stepper")).to_be_visible()
    expect(page.locator("#flow-risk-statement")).to_be_visible()


def test_start_from_clause_get_started_opens_path_b(page):
    expect(page.locator("#start-from-clause")).to_have_text("Get started")
    choose_clause_path(page)
    expect(page.locator("#paste-form")).to_be_visible()
    expect(page.locator("#paste-submit")).to_have_text("Codify")
    expect(page.locator("#demo")).to_be_visible()


def test_resume_is_a_quiet_link_and_opens_the_saved_project(browser, base_url):
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
    expect(page.locator("#resume-open")).to_have_text("Resume")
    expect(page.locator("#resume-open")).not_to_have_class("btn--primary")
    expect(page.locator("#resume-discard")).to_have_count(0)
    page.click("#resume-open")
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    expect(page.locator("#legacy-risk-prompt")).to_contain_text("started from clauses")
    context.close()


def test_landing_has_no_docs_or_open_saved(page):
    expect(page.locator("#landing-docs")).to_have_count(0)
    expect(page.locator("#open-saved")).to_have_count(0)
    expect(page.locator("#start-from-risks")).to_have_text("Get started")
    expect(page.locator("#start-from-clause")).to_have_text("Get started")


def test_landing_is_keyboard_reachable_and_stacks_on_mobile(browser, base_url):
    ctx, page = _open(browser, base_url, width=390, height=844)
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#start-from-clause")).to_be_visible()
    page.locator("#start-from-risks").focus()
    expect(page.locator("#start-from-risks")).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#flow:not([hidden])")).to_be_visible()
    ctx.close()


def test_landing_uses_theme_tokens_in_light_and_dark(browser, base_url):
    ctx, page = _open(browser, base_url, color_scheme="light")
    expect(page.locator("html")).to_have_attribute("data-theme", "light")
    expect(page.locator("#start-from-risks")).to_be_visible()
    ctx.close()
    ctx, page = _open(browser, base_url, color_scheme="dark")
    expect(page.locator("html")).to_have_attribute("data-theme", "dark")
    expect(page.locator("#start-from-risks")).to_be_visible()
    ctx.close()


def test_try_an_example_still_works_from_the_clause_card(page):
    choose_clause_path(page)
    page.click("#demo")
    finish_open(page)
    goto_review(page)
    expect(page.locator("#work-summary")).to_contain_text("38 control drafts")
