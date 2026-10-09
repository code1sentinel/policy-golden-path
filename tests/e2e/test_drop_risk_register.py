"""Older saved projects with a risk register still open; the register is gone."""

import json

from playwright.sync_api import expect


def test_resume_drops_register_fields_and_keeps_controls(browser, base_url):
    payload = json.dumps({
        "project": {
            "uuid": "00000000-0000-4000-8000-000000000000",
            "title": "Saved with risks",
            "source": "",
            "clauses": [{
                "id": "c1", "text": "Users shall lock screens.", "section": "0", "heading": "",
                "type": "requirement", "reason": "shall", "duplicate_of": None,
            }],
            "controls": [{
                "id": "c1", "clause": "c1", "text": "Require users to lock screens.",
                "guidance": "", "risk": "Screens left unlocked.", "who": "", "notes": [],
                "status": "draft", "origin": "rules", "source_type": "risk", "risk_id": "R-001",
            }],
            "risks": [{
                "id": "R-001", "title": "Unauthorised access", "likelihood": 4, "impact": 5, "score": 20,
            }],
        },
        "scores": {},
        "saved": "2026-10-08T12:00:00.000Z",
    })
    library = json.dumps({
        "entries": [{
            "id": "S-001", "statement": "Restrict access to agency systems to authorised users.",
            "parts": None, "source-type": "risk", "risk-id": "R-001",
            "accepted-at": "2026-10-08T12:00:00+00:00", "last-used-at": "",
        }],
        "saved": "2026-10-08T12:00:00.000Z",
    })
    context = browser.new_context(viewport={"width": 1360, "height": 900})
    context.add_init_script("localStorage.setItem('codify:splash-seen', '1');")
    context.add_init_script(f"localStorage.setItem('codify:project', {payload!r});")
    context.add_init_script(f"localStorage.setItem('codify:statements', {library!r});")
    context.add_init_script("localStorage.setItem('codify:risks', '[{\"id\":\"R-001\"}]');")
    page = context.new_page()
    page.goto(base_url, wait_until="domcontentloaded")
    expect(page.locator("#resume")).to_be_visible()
    page.click("#resume-open")
    expect(page.locator("#work:not([hidden])")).to_be_visible()
    expect(page.locator("textarea.statement")).to_have_value("Require users to lock screens.")
    expect(page.locator("nav.sidebar__nav")).not_to_contain_text("Risks")
    page.click("#export-open-top")
    expect(page.locator("#export-dialog")).not_to_contain_text("Risk register")
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))
    assert "risks" not in saved["project"]
    assert saved["project"]["controls"][0]["text"] == "Require users to lock screens."
    assert saved["project"]["controls"][0]["risk"] == "Screens left unlocked."
    statements = json.loads(page.evaluate("localStorage.getItem('codify:statements')"))
    assert statements["entries"][0]["source-type"] == "risk"
    assert statements["entries"][0]["risk-id"] == "R-001"
    assert page.evaluate("localStorage.getItem('codify:risks')") is None
    context.close()
