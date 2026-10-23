"""Step 3: generate a Rego starter, copy it, and download a .rego file."""

from playwright.sync_api import expect

from conftest import add_flow_risk, choose_risk_path


def test_generate_rego_starter_copy_and_download(page, tmp_path):
    choose_risk_path(page)
    add_flow_risk(page, "Public object storage exposes customer data.")
    page.click("#identify-continue")
    page.locator("#statements-editor textarea").first.fill(
        "Block public access on all object-storage buckets.")
    page.locator("#statements-editor textarea").first.blur()
    page.click("#statements-continue")
    expect(page.locator("#work:not([hidden])")).to_be_visible()
    page.locator(".editor__primary >> text=Accept").click()
    page.click("#flow-next")
    expect(page.locator("#enact-step")).to_be_visible()
    starters = page.locator("#rego-starters")
    expect(starters).to_contain_text("Starter to review — not a finished policy")
    expect(starters).to_contain_text("Generate Rego starter")
    expect(starters).not_to_contain_text("GRC Engineering Club")
    card = starters.locator(".rego-starter").first
    expect(card.locator("[data-generate]")).to_have_text("Generate Rego starter")
    card.locator("[data-generate]").click()
    code = card.locator(".rego-starter__code")
    expect(code).to_be_visible()
    expect(code).to_contain_text("import rego.v1")
    expect(code).to_contain_text("Starter — review before use. Not a finished policy.")
    expect(code).to_contain_text("Block public access on all object-storage buckets.")
    card.locator("[data-copy]").click()
    expect(card.locator("[data-copy-status]")).to_have_text("Copied")
    with page.expect_download() as dl:
        card.locator("[data-download]").click()
    path = tmp_path / dl.value.suggested_filename
    dl.value.save_as(path)
    assert path.suffix == ".rego"
    body = path.read_text(encoding="utf-8")
    assert "import rego.v1" in body
    assert "deny contains msg if" in body
