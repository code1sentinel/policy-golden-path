"""Statement library: accept → library, reuse across projects, remove, export."""

import json

from playwright.sync_api import expect


CLAUSE = (
    "Access to systems shall be granted on a need-to-know basis to limit what "
    "a compromised account can reach."
)
OTHER = "Screens shall be locked when unattended to prevent casual observation."


def library_store(page):
    raw = page.evaluate("localStorage.getItem('codify:statements')")
    return json.loads(raw) if raw else None


def open_pasted(page, text):
    page.fill("#paste-form textarea", text)
    page.click("#paste-submit")
    page.wait_for_selector("#work:not([hidden]) textarea.statement", timeout=120_000)


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
    page.locator(".editor__primary >> text=Accept").click()
    expect(page.locator(".state--accepted").first).to_be_visible()
    wait_for_library_entries(page)


def test_library_empty_state(page):
    page.click("[data-nav='library']")
    expect(page.locator("#library:not([hidden])")).to_be_visible()
    expect(page.locator("#library")).to_contain_text("No statements saved yet")
    expect(page.locator("#library-search")).to_be_visible()
    raw = page.evaluate("localStorage.getItem('codify:statements')")
    if raw:
        assert json.loads(raw).get("entries") == []


def test_accept_lands_in_library_and_survives_another_project(page):
    open_pasted(page, CLAUSE)
    statement = page.locator("textarea.statement").input_value()
    accept_current(page)
    page.click("[data-nav='library']")
    expect(page.locator("#library .library-row")).to_have_count(1)
    expect(page.locator("#library .library-row")).to_contain_text(statement[:40])
    store = library_store(page)
    assert store and len(store["entries"]) == 1
    assert store["entries"][0]["statement"] == statement
    assert "sk-test" not in json.dumps(store)

    page.click("#close-project")
    open_pasted(page, OTHER)
    page.click("[data-nav='library']")
    expect(page.locator("#library .library-row")).to_have_count(1)
    expect(page.locator("#library .library-row")).to_contain_text(statement[:40])


def test_use_from_library_then_accept_goes_into_the_current_catalog(page):
    open_pasted(page, CLAUSE)
    first = page.locator("textarea.statement").input_value()
    accept_current(page)
    page.click("#close-project")
    open_pasted(page, OTHER)
    other = page.locator("textarea.statement").input_value()
    assert other != first
    page.click("[data-nav='library']")
    page.locator(".library-row .library-use").click()
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
    page.click("[data-nav='library']")
    page.locator(".library-row .library-remove").click()
    expect(page.locator("#library")).to_contain_text("No statements saved yet")
    after = json.loads(page.evaluate("localStorage.getItem('codify:project')"))["project"]
    assert [c["text"] for c in after["controls"]] == [c["text"] for c in before["controls"]]
    assert any(c["text"] == statement and c["status"] == "accepted" for c in after["controls"])
    store = library_store(page)
    assert not store or store["entries"] == []


def test_export_library_downloads_locally(page, tmp_path):
    open_pasted(page, CLAUSE)
    statement = page.locator("textarea.statement").input_value()
    accept_current(page)
    page.click("[data-nav='library']")
    with page.expect_download() as dl:
        page.click("#library-export-json")
    path = tmp_path / "library.json"
    dl.value.save_as(path)
    payload = json.loads(path.read_text())
    assert payload[0]["statement"] == statement
    with page.expect_download() as csv_dl:
        page.click("#library-export-csv")
    csv_path = tmp_path / "library.csv"
    csv_dl.value.save_as(csv_path)
    text = csv_path.read_text()
    assert text.startswith("id,statement,") and statement in text


def test_duplicate_accept_does_not_add_a_second_row(page):
    open_pasted(page, CLAUSE)
    accept_current(page)
    page.locator(".editor__primary >> text=Accept").click()
    page.click("[data-nav='library']")
    expect(page.locator("#library .library-row")).to_have_count(1)


def test_from_library_picks_show_in_the_editor(page):
    open_pasted(page, CLAUSE)
    accept_current(page)
    expect(page.locator("#library-picks")).to_contain_text("From library")
    page.click("#library-from")
    expect(page.locator("#library-pick")).to_be_visible()
    expect(page.locator("#library-pick")).to_contain_text("Use")


def test_risk_accept_also_lands_in_the_library(page, tmp_path):
    csv = tmp_path / "risks.csv"
    csv.write_text(
        "id,title,description,asset,likelihood,impact,threat,vulnerability,owner,status\n"
        "R-001,Unauthorised access to agency systems,A compromised account could reach systems "
        "beyond need-to-know.,Agency systems,4,5,Stolen credentials,Excessive access rights,"
        "Jane Smith,identified\n"
    )
    page.click("[data-nav='risks']")
    page.set_input_files("#risk-file", str(csv))
    expect(page.locator("#risk-import-dialog")).to_contain_text("recognised", timeout=120_000)
    page.click("#risk-import-apply")
    expect(page.locator("#risk-templates")).to_contain_text("Restrict access", timeout=30_000)
    page.locator('#risk-templates [data-template="restrict-access"] button', has_text="Accept").click()
    expect(page.locator("textarea.statement")).to_be_visible()
    wait_for_library_entries(page)
    page.click("[data-nav='library']")
    expect(page.locator("#library .library-row")).to_have_count(1)
    expect(page.locator("#library .library-row")).to_contain_text("R-001")
