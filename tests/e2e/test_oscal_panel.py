"""OSCAL JSON tab, copy, and the split export button."""

from playwright.sync_api import expect


def test_oscal_tab_shows_this_control_and_copy_announces(demo):
    expect(demo.locator(".editor-tabs")).to_contain_text("Statement")
    expect(demo.locator(".editor-tabs")).to_contain_text("OSCAL JSON")
    demo.click(".editor-tabs >> text=OSCAL JSON")
    expect(demo.locator("#oscal-json")).to_be_visible()
    expect(demo.locator("#oscal-json")).to_contain_text('"id"')
    expect(demo.locator("#oscal-json .oscal-ln").first).to_be_visible()
    expect(demo.locator("textarea.statement")).to_have_count(0)
    demo.click("#oscal-copy")
    expect(demo.locator("#oscal-copy-status")).to_have_text("Copied")
    demo.click(".editor-tabs >> text=Statement")
    expect(demo.locator("textarea.statement")).to_be_visible()


def test_save_oscal_is_a_split_button_without_a_duplicate(demo, tmp_path):
    expect(demo.locator(".work__actions [data-export='oscal']")).to_have_text("Save OSCAL (.json)")
    expect(demo.locator("#export-menu [data-export='oscal']")).to_have_count(0)
    demo.click("#export-more")
    expect(demo.locator("#export-menu")).to_be_visible()
    expect(demo.locator("#export-menu [data-export='xlsx']")).to_be_visible()
    expect(demo.locator("#export-menu [data-export='csv']")).to_be_visible()
    expect(demo.locator("#export-menu [data-export='report']")).to_be_visible()
    with demo.expect_download() as dl:
        demo.click(".work__actions [data-export='oscal']")
    path = tmp_path / "catalog.json"
    dl.value.save_as(path)
    assert path.read_text().startswith("{")
