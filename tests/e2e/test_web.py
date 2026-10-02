"""The web app, end to end: open a policy, review, AI drafting, IM8 mapping and coverage, exports."""

import json

from playwright.sync_api import expect


def ctl(cid):
    return "#ctl-" + cid.replace(".", "\\.")


def clause(cid):
    return "#clause-" + cid.replace(".", "\\.")


def saved_project(page):
    return json.loads(page.evaluate("localStorage.getItem('codify:project')"))["project"]


def control(page, cid):
    return next(c for c in saved_project(page)["controls"] if c["id"] == cid)


def turn_on_ai(page):
    page.click("#ai-open")
    page.fill("#ai-key", "sk-test")
    page.check("#ai-ack")
    page.click("#ai-on")
    expect(page.locator("#ai-open")).to_have_text("AI drafting: on")


# --- Opening and reviewing ----------------------------------------------------------------------------

def test_demo_opens_with_drafts_scored(demo):
    expect(demo.locator("#work-summary")).to_contain_text("43 clauses → 38 controls")
    expect(demo.locator(".scoreline__pct")).to_be_visible()


def test_pasted_text_is_shown_as_text_never_as_html(page):
    page.fill("#paste-form textarea", '1.1 Users shall not run <img src=x onerror="window.pwned=1"> scripts.')
    page.click("#paste-submit")
    page.wait_for_selector("#work:not([hidden]) .ctl", timeout=120_000)
    expect(page.locator(clause("1.1") + " .clause__text")).to_contain_text("<img src=x")
    assert page.evaluate("window.pwned") is None


def test_editing_rescoring_and_status(demo):
    demo.click(ctl("5.1a") + " .ctl__open")
    demo.fill("textarea.statement", "Grant access to Agency systems on a need-to-know basis to limit what a compromised account can reach.")
    expect(demo.locator(".parts .p-purpose")).not_to_have_class("p-purpose is-missing")
    demo.click(".editor__where")
    demo.keyboard.press("r")
    expect(demo.locator(ctl("5.1a") + " .state")).to_have_text("Reviewed")
    assert control(demo, "5.1a")["origin"] == "person"


def test_close_and_resume(demo):
    demo.click("#close-project")
    expect(demo.locator("#resume")).to_be_visible()
    demo.click("#resume-open")
    expect(demo.locator("#work-summary")).to_contain_text("38 controls")


# --- Exports ---------------------------------------------------------------------------------------------

def test_oscal_export_opens_again(demo, tmp_path):
    with demo.expect_download() as dl:
        demo.click(".work__actions [data-export='oscal']")
    path = tmp_path / "catalog.json"
    dl.value.save_as(path)
    catalog = json.loads(path.read_text())["catalog"]
    assert sum(len(g["controls"]) for g in catalog["groups"]) == 38
    demo.click("#close-project")
    demo.set_input_files("#file", str(path))
    expect(demo.locator("#work-summary")).to_contain_text("43 clauses → 38 controls")


# --- AI drafting -------------------------------------------------------------------------------------------

def test_ai_is_off_until_turned_on_with_an_acknowledgement(demo, provider):
    expect(demo.locator("#ai-bulk")).to_be_hidden()
    demo.click("#ai-open")
    demo.fill("#ai-key", "sk-test")
    demo.click("#ai-on")
    expect(demo.locator("#ai-form-error")).to_contain_text("Tick the box")
    assert provider.requests == []


def test_ai_drafts_one_clause_and_keeps_the_key_out_of_the_project(demo, provider, tmp_path):
    turn_on_ai(demo)
    assert demo.evaluate("localStorage.getItem('codify:ai-key')") is None  # tab only unless remembered
    demo.click(clause("5.1") + " .clause__select")
    demo.click("#editor >> text=Draft with AI")
    expect(demo.locator(".editor__where")).to_contain_text("drafted by AI")
    (sent,) = provider.requests
    assert sent["headers"]["x-api-key"] == "sk-test" and sent["body"]["model"] == "claude-sonnet-5-5"
    user = sent["body"]["messages"][0]["content"]
    assert "Legacy clause 5.1" in user and "5.2" not in user  # one clause only
    assert control(demo, "5.1")["origin"] == "ai"
    with demo.expect_download() as dl:
        demo.click(".work__actions [data-export='oscal']")
    dl.value.save_as(tmp_path / "c.json")
    assert "sk-test" not in (tmp_path / "c.json").read_text()
    assert "sk-test" not in demo.evaluate("localStorage.getItem('codify:project')")


def test_ai_rejected_key_is_reported(demo, provider):
    turn_on_ai(demo)
    provider.status = 401
    demo.click(clause("5.1") + " .clause__select")
    demo.click("#editor >> text=Draft with AI")
    expect(demo.locator("#error")).to_contain_text("did not accept the API key")


def test_turning_ai_off_forgets_the_key(demo):
    turn_on_ai(demo)
    demo.click("#ai-open")
    demo.click("#ai-off")
    assert demo.evaluate("[sessionStorage.getItem('codify:ai-key'), localStorage.getItem('codify:ai-key')]") == [None, None]


# --- IM8 Reform mapping -----------------------------------------------------------------------------------

def test_map_from_a_suggestion_and_remove(demo):
    demo.click(ctl("9.1a") + " .ctl__open")
    first = demo.locator(".im8__list li").first
    expect(first).to_contain_text("br-1 Backup")
    first.locator(".btn").click()
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_text("IM8 br-1")
    assert control(demo, "9.1a")["im8"] == ["br-1"]
    demo.click(".im8-chip .chip-x")
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_count(0)


def test_coverage_view_counts_and_jumps_back(demo):
    demo.click("#select-shown")
    demo.click("#im8-bulk")
    expect(demo.locator("#notice")).to_contain_text("Mapped 35 controls")
    demo.click("[data-view='im8']")
    expect(demo.locator(".im8-level").first).to_contain_text("20 of 137")
    demo.click("[data-im8-show='gaps']")
    expect(demo.locator(".im8-rows li.is-covered")).to_have_count(0)
    demo.click("[data-im8-show='all']")
    demo.locator(".im8-from .linkish").first.click()
    expect(demo.locator("#work")).to_be_visible()


def test_redrafting_a_mapped_clause_keeps_the_mappings(demo):
    """A mapping is a person's work: redrafting the clause must not silently lose it."""
    demo.click(ctl("9.1a") + " .ctl__open")
    demo.locator(".im8__list li").first.locator(".btn").click()
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_count(1)
    demo.click(clause("9.1") + " .clause__select")
    demo.click("#editor >> text=Draft again from this clause")
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_text("IM8 br-1")


def test_bulk_ai_leaves_mapped_clauses_alone(demo, provider):
    turn_on_ai(demo)
    demo.click(ctl("9.1a") + " .ctl__open")
    demo.locator(".im8__list li").first.locator(".btn").click()
    demo.click(ctl("9.1a") + " input[type=checkbox]")
    demo.click(ctl("8.1") + " input[type=checkbox]")
    demo.click("#ai-bulk")
    expect(demo.locator("#ai-progress")).to_be_hidden()
    assert len(provider.requests) == 1 and "Legacy clause 8.1" in provider.requests[0]["body"]["messages"][0]["content"]
    assert control(demo, "9.1a")["im8"] == ["br-1"]


def test_notice_clears_when_the_project_closes(demo):
    demo.click("#select-shown")
    demo.click("#im8-bulk")
    expect(demo.locator("#notice")).to_be_visible()
    demo.click("#close-project")
    expect(demo.locator("#notice")).to_be_hidden()


def test_element_ids_are_unique_with_a_clause_open(demo):
    demo.click(clause("9.1") + " .clause__select")
    expect(demo.locator(".editor__where")).to_contain_text("Clause 9.1")
    dupes = demo.evaluate("""() => {
        const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
        return ids.filter((id, i) => ids.indexOf(id) !== i);
    }""")
    assert dupes == []


# --- Layout ---------------------------------------------------------------------------------------------

def test_no_sideways_scroll_on_a_phone(demo):
    demo.set_viewport_size({"width": 390, "height": 844})
    for view in ("work", "im8", "guide"):
        demo.click(f"[data-view='{view}']")
        assert demo.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), view
