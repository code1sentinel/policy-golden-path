"""The web app, end to end: open a policy, review, AI drafting, IM8 mapping and coverage, exports."""

import json
import re

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


def turn_on_ollama(page):
    page.click("#ai-open")
    page.select_option("#ai-provider", "ollama")
    expect(page.locator("#ai-key-field")).to_be_hidden()
    page.check("#ai-ack")
    page.click("#ai-on")
    expect(page.locator("#ai-open")).to_have_text("AI drafting: on")


def open_more(page):
    page.locator("#work-more").evaluate("el => { el.open = true }")


def open_im8_fold(page):
    page.locator("#im8-fold").evaluate("el => { el.open = true }")


# --- Opening and reviewing ----------------------------------------------------------------------------

def test_demo_opens_with_drafts_scored(demo):
    expect(demo.locator("#work-summary")).to_contain_text("43 clauses → 38 controls")
    expect(demo.locator(".scoreline__pct")).to_be_visible()
    expect(demo.locator("textarea.statement")).to_be_visible()
    expect(demo.locator(".editor__primary")).to_contain_text("Accept")
    expect(demo.locator(".editor__primary")).to_contain_text("Next")
    expect(demo.locator("#clause-5\\.1")).to_be_visible()
    expect(demo.locator("#clause-3\\.3")).to_have_count(0)
    expect(demo.locator("#work-more .filters")).to_be_hidden()
    expect(demo.locator("#select-shown")).to_be_hidden()
    expect(demo.locator("#im8-fold")).not_to_have_attribute("open")


def test_start_is_a_short_cta_not_a_wall(page):
    expect(page.locator("#start-title")).to_have_text("Turn a policy into control statements")
    expect(page.locator("#demo")).to_be_visible()
    expect(page.locator(".steps")).to_have_count(0)
    expect(page.locator("#paste-form")).to_be_visible()
    expect(page.locator("#file")).to_be_attached()


def test_happy_path_edit_accept_next(demo):
    expect(demo.locator(".editor__where")).to_contain_text("5.1a")
    demo.locator(".editor__primary >> text=Accept").click()
    expect(demo.locator(ctl("5.1a") + " .state")).to_have_text("Accepted")
    demo.locator(".editor__primary >> text=Next").click()
    expect(demo.locator(".editor__where")).to_contain_text("5.1b")


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


def test_ollama_turns_on_without_a_key_and_drafts(demo, provider):
    turn_on_ollama(demo)
    expect(demo.locator("#ai-open")).to_have_class(re.compile(r"\bis-on\b"))
    demo.click(ctl("5.1a") + " input[type=checkbox]")
    expect(demo.locator("#ai-bulk")).to_be_visible()
    demo.click("#select-none")
    demo.click(clause("5.1") + " .clause__select")
    demo.click("#editor >> text=Draft with AI")
    expect(demo.locator(".editor__where")).to_contain_text("drafted by AI")
    (sent,) = provider.requests
    assert "localhost:11434" in sent["url"]
    assert "authorization" not in sent["headers"] and "x-api-key" not in sent["headers"]
    assert sent["body"]["model"] == "llama3.2"
    assert control(demo, "5.1")["origin"] == "ai"


def test_ollama_unreachable_is_reported(demo):
    turn_on_ollama(demo)
    demo.context.unroute("http://localhost:11434/**")
    demo.context.unroute("http://127.0.0.1:11434/**")
    demo.context.route("http://localhost:11434/**", lambda route: route.abort())
    demo.context.route("http://127.0.0.1:11434/**", lambda route: route.abort())
    demo.click(clause("5.1") + " .clause__select")
    demo.click("#editor >> text=Draft with AI")
    expect(demo.locator("#error")).to_contain_text("Could not reach Ollama")


def test_shortcuts_do_not_fire_while_ai_dialog_is_open(demo):
    demo.click(ctl("5.1a") + " .ctl__open")
    demo.click("#ai-open")
    demo.locator("#ai-on").focus()
    demo.keyboard.press("r")
    expect(demo.locator(ctl("5.1a") + " .state")).to_have_text("Draft")
    demo.keyboard.press("Escape")
    expect(demo.locator("#ai-dialog")).to_be_hidden()


def test_selection_bar_appears_with_a_selection(demo):
    bar = demo.locator("#selection-bar")
    expect(bar).to_be_hidden()
    expect(demo.locator("[data-bulk='reviewed']")).to_be_hidden()
    demo.click(ctl("5.1a") + " input[type=checkbox]")
    expect(bar).to_be_visible()
    expect(demo.locator("#selected-count")).to_have_text("1 selected")
    expect(demo.locator("[data-bulk='reviewed']")).to_be_enabled()
    expect(demo.locator(ctl("5.1a"))).to_have_class(re.compile(r"\bis-checked\b"))
    demo.click(ctl("8.1") + " input[type=checkbox]")
    expect(demo.locator("#selected-count")).to_have_text("2 selected")
    demo.click("[data-bulk='reviewed']")
    expect(demo.locator(ctl("5.1a") + " .state")).to_have_text("Reviewed")
    expect(demo.locator(ctl("8.1") + " .state")).to_have_text("Reviewed")
    expect(bar).to_be_hidden()


def test_ai_dialog_shows_ready_or_needs_key(demo):
    demo.click("#ai-open")
    expect(demo.locator("#ai-ready-chip")).to_have_text("Needs a key")
    expect(demo.locator("#ai-key-field")).to_be_visible()
    expect(demo.locator("#ai-remember-row")).to_be_visible()
    demo.fill("#ai-key", "sk-test")
    expect(demo.locator("#ai-ready-chip")).to_have_text("Ready")
    demo.select_option("#ai-provider", "ollama")
    expect(demo.locator("#ai-key-field")).to_be_hidden()
    expect(demo.locator("#ai-remember-row")).to_be_hidden()
    expect(demo.locator("#ai-ready-chip")).to_have_text("Ready · no key")
    expect(demo.locator("#ai-local-note")).to_be_visible()
    expect(demo.locator("#ai-local-note")).to_contain_text("localhost:11434")


# --- IM8 Reform mapping -----------------------------------------------------------------------------------

def test_map_from_a_suggestion_and_remove(demo):
    demo.click(ctl("9.1a") + " .ctl__open")
    open_im8_fold(demo)
    first = demo.locator(".im8__list li").first
    expect(first).to_contain_text("br-1 Backup")
    first.locator(".btn").click()
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_text("IM8 br-1")
    assert control(demo, "9.1a")["im8"] == ["br-1"]
    demo.click(".im8-chip .chip-x")
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_count(0)


def test_coverage_view_counts_and_jumps_back(demo):
    open_more(demo)
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
    open_im8_fold(demo)
    demo.locator(".im8__list li").first.locator(".btn").click()
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_count(1)
    demo.click("#editor >> text=Draft again from this clause")
    expect(demo.locator(ctl("9.1a") + " .im8-tag")).to_have_text("IM8 br-1")


def test_bulk_ai_leaves_mapped_clauses_alone(demo, provider):
    turn_on_ai(demo)
    demo.click(ctl("9.1a") + " .ctl__open")
    open_im8_fold(demo)
    demo.locator(".im8__list li").first.locator(".btn").click()
    demo.click(ctl("9.1a") + " input[type=checkbox]")
    demo.click(ctl("8.1") + " input[type=checkbox]")
    demo.click("#ai-bulk")
    expect(demo.locator("#ai-progress")).to_be_hidden()
    assert len(provider.requests) == 1 and "Legacy clause 8.1" in provider.requests[0]["body"]["messages"][0]["content"]
    assert control(demo, "9.1a")["im8"] == ["br-1"]


def test_notice_clears_when_the_project_closes(demo):
    open_more(demo)
    demo.click("#select-shown")
    demo.click("#im8-bulk")
    expect(demo.locator("#notice")).to_be_visible()
    demo.click("#close-project")
    expect(demo.locator("#notice")).to_be_hidden()


def test_element_ids_are_unique_with_a_clause_open(demo):
    demo.click(ctl("9.1a") + " .ctl__open")
    demo.get_by_role("button", name="Clause 9.1").click()
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
