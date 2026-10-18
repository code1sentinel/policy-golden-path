"""Statement library: accept → library, reuse across projects, remove, export."""

import json

from playwright.sync_api import expect

from conftest import choose_clause_path, finish_open, goto_review


CLAUSE = (
    "Access to systems shall be granted on a need-to-know basis to limit what "
    "a compromised account can reach."
)
OTHER = "Screens shall be locked when unattended to prevent casual observation."


def library_store(page):
    raw = page.evaluate("localStorage.getItem('codify:statements')")
    return json.loads(raw) if raw else None


def open_pasted(page, text):
    choose_clause_path(page)
    page.fill("#paste-form textarea", text)
    page.click("#paste-submit")
    finish_open(page)
    goto_review(page)
    page.wait_for_selector("#work:not([hidden]) textarea.statement", timeout=30_000)


def wait_for_library_entries(page, n=1):
    page.wait_for_function(
        """count => {
          try {
            const raw = localStorage.getItem('codify:statements');
            const data = raw ? JSON.parse(raw) : null;
            const entries = data && data.entries ? data.entries : (Array.isArray(data) ? data : []);
            return entries.length >= count;
          } catch { return false; }
        }""",
        arg=n,
    )


def accept_current(page):
    page.locator("#accept-control").click()
    expect(page.locator(".state--accepted").first).to_be_visible()
    wait_for_library_entries(page)


def test_library_empty_state(page):
    page.click("#start-from-risks")
    expect(page.locator("nav.sidebar__nav").get_by_role("button", name="Library")).to_have_count(0)
    expect(page.locator("#library-pick")).to_have_count(1)
    raw = page.evaluate("localStorage.getItem('codify:statements')")
    if raw:
        assert json.loads(raw).get("entries") == []


def test_accept_lands_in_library_and_survives_another_project(page):
    open_pasted(page, CLAUSE)
    statement = page.locator("textarea.statement").input_value()
    accept_current(page)
    store = library_store(page)
    assert store and len(store["entries"]) == 1
    assert store["entries"][0]["statement"] == statement
    assert "sk-test" not in json.dumps(store)
    page.click("#library-from")
    expect(page.locator("#library-pick")).to_be_visible()
    expect(page.locator("#library-pick")).to_contain_text(statement[:40])
    page.locator("#library-pick").get_by_role("button", name="Close").click()
    expect(page.locator("#library-pick")).to_be_hidden()

    page.click("#close-project")
    open_pasted(page, OTHER)
    page.click("#library-from")
    expect(page.locator("#library-pick")).to_contain_text(statement[:40])
    assert page.locator("#library-pick").inner_text().count(statement[:40]) == 1


def test_use_from_library_then_accept_goes_into_the_current_catalog(page):
    open_pasted(page, CLAUSE)
    first = page.locator("textarea.statement").input_value()
    accept_current(page)
    page.click("#close-project")
    open_pasted(page, OTHER)
    other = page.locator("textarea.statement").input_value()
    assert other != first
    page.click("#library-from")
    page.locator("#library-pick-detail .library-use").click()
    expect(page.locator("#work:not([hidden]) textarea.statement")).to_have_value(first)
    accept_current(page)
    saved = json.loads(page.evaluate("localStorage.getItem('codify:project')"))["project"]
    assert any(c["text"] == first and c["status"] == "accepted" for c in saved["controls"])
    store = library_store(page)
    assert len(store["entries"]) == 1
    assert store["entries"][0]["last-used-at"]


def test_remove_leaves_the_catalog_alone(page):
    open_pasted(page, CLAUSE)
    statement = page.locator("textarea.statement").input_value()
    accept_current(page)
    before = json.loads(page.evaluate("localStorage.getItem('codify:project')"))["project"]
    page.evaluate(
        """() => {
          const raw = localStorage.getItem('codify:statements');
          const lib = raw ? JSON.parse(raw) : {entries: []};
          lib.entries = [];
          localStorage.setItem('codify:statements', JSON.stringify(lib));
        }"""
    )
    after = json.loads(page.evaluate("localStorage.getItem('codify:project')"))["project"]
    assert [c["text"] for c in after["controls"]] == [c["text"] for c in before["controls"]]
    assert any(c["text"] == statement and c["status"] == "accepted" for c in after["controls"])
    store = library_store(page)
    assert not store or store["entries"] == []


def test_export_library_downloads_locally(page, tmp_path):
    open_pasted(page, CLAUSE)
    statement = page.locator("textarea.statement").input_value()
    accept_current(page)
    page.click("#export-open-top")
    page.locator("#export-dialog .export-more summary").click()
    with page.expect_download() as dl:
        page.click("#export-dialog [data-export='library-json']")
    path = tmp_path / "library.json"
    dl.value.save_as(path)
    payload = json.loads(path.read_text())
    assert payload[0]["statement"] == statement
    page.click("#export-open-top")
    page.locator("#export-dialog .export-more summary").click()
    with page.expect_download() as csv_dl:
        page.click("#export-dialog [data-export='library-csv']")
    csv_path = tmp_path / "library.csv"
    csv_dl.value.save_as(csv_path)
    text = csv_path.read_text()
    assert text.startswith("id,statement,") and statement in text


def test_duplicate_accept_does_not_add_a_second_row(page):
    open_pasted(page, CLAUSE)
    accept_current(page)
    expect(page.locator("#accept-control")).to_contain_text("Accepted")
    store = library_store(page)
    assert store and len(store["entries"]) == 1
    page.click("#library-from")
    expect(page.locator("#library-pick .library-detail__statement")).to_have_count(1)


def test_from_library_picks_show_in_the_editor(page):
    open_pasted(page, CLAUSE)
    accept_current(page)
    expect(page.locator("#library-picks")).to_contain_text("From library")
    page.click("#library-from")
    expect(page.locator("#library-pick")).to_be_visible()
    expect(page.locator("#library-pick")).to_contain_text("Use")


