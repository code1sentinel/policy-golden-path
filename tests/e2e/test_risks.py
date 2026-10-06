"""Risk register: import locally, draft from templates, accept, export with tracing."""

import json

from playwright.sync_api import expect

from tests.e2e.test_web import export_oscal, turn_on_ai

CSV = """id,title,description,asset,likelihood,impact,threat,vulnerability,owner,status
R-001,Unauthorised access to agency systems,A compromised account could reach systems beyond need-to-know.,Agency systems,4,5,Stolen credentials,Excessive access rights,Jane Smith,identified
"""


def test_risks_empty_state_has_create_and_import(page):
    page.click("[data-nav='risks']")
    expect(page.locator("#risks")).to_contain_text("No risks yet")
    expect(page.locator("#risk-add")).to_be_visible()
    expect(page.locator("#risk-import")).to_be_visible()


def test_risk_import_template_accept_export(page, tmp_path):
    csv = tmp_path / "risks.csv"
    csv.write_text(CSV)
    page.click("[data-nav='risks']")
    page.set_input_files("#risk-file", str(csv))
    expect(page.locator("#risk-import-dialog")).to_contain_text("recognised", timeout=120_000)
    expect(page.locator("#risk-import-dialog")).to_contain_text("title")
    page.click("#risk-import-apply")
    expect(page.locator(".risk-table")).to_contain_text("R-001")
    expect(page.locator("#risk-drawer")).to_contain_text("Jane Smith")
    expect(page.locator(".heatmap")).to_be_visible()
    expect(page.locator("#risk-templates")).to_contain_text("Restrict access", timeout=30_000)
    page.locator('#risk-templates [data-template="restrict-access"] button', has_text="Add").click()
    expect(page.locator("textarea.statement")).to_be_visible()
    expect(page.locator("#props")).to_contain_text("R-001")
    page.locator(".editor__primary >> text=Accept").click()
    page.click("[data-nav='catalog']")
    expect(page.locator("#catalog .data-table")).to_contain_text("R-001")
    with export_oscal(page) as dl:
        page.click("#export-dialog [data-export='oscal']")
    path = tmp_path / "catalog.json"
    dl.value.save_as(path)
    catalog = json.loads(path.read_text())["catalog"]
    controls = [c for g in catalog["groups"] for c in g["controls"]]
    assert any(any(p.get("name") == "source-type" and p.get("value") == "risk" for p in c.get("props", []))
               for c in controls)
    assert any(any(p.get("name") == "risk-id" for p in r.get("props", []))
               for r in catalog["back-matter"]["resources"])
    assert "sk-test" not in path.read_text()


def test_risk_ai_draft_is_faked_and_keeps_keys_out(page, provider, tmp_path):
    csv = tmp_path / "risks.csv"
    csv.write_text(CSV)
    page.click("[data-nav='risks']")
    page.set_input_files("#risk-file", str(csv))
    expect(page.locator("#risk-import-dialog")).to_contain_text("recognised", timeout=120_000)
    page.click("#risk-import-apply")
    expect(page.locator("#risk-drawer")).to_be_visible()
    turn_on_ai(page)
    page.click("[data-nav='risks']")
    expect(page.locator("#risk-templates")).to_contain_text("Draft with AI", timeout=30_000)
    page.click("#risk-templates >> text=Draft with AI")
    expect(page.locator(".editor__where")).to_contain_text("drafted by AI")
    assert provider.requests
    user = provider.requests[0]["body"]["messages"][0]["content"]
    assert "Identified risk R-001" in user
    with export_oscal(page) as dl:
        page.click("#export-dialog [data-export='oscal']")
    dl.value.save_as(tmp_path / "c.json")
    assert "sk-test" not in (tmp_path / "c.json").read_text()
    saved = page.evaluate("localStorage.getItem('codify:project')")
    assert "sk-test" not in saved
