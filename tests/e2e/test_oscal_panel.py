"""OSCAL JSON tab, copy, and the export dialog."""

from playwright.sync_api import expect


def test_oscal_tab_shows_this_control_and_copy_announces(demo):
    tabs = demo.locator("#editor .editor-tabs")
    expect(tabs).to_contain_text("Statement")
    expect(tabs).to_contain_text("OSCAL JSON")
    demo.locator("#editor .editor-tabs >> text=OSCAL JSON").click()
    expect(demo.locator("#oscal-json")).to_be_visible()
    expect(demo.locator("#oscal-json")).to_contain_text('"id"')
    expect(demo.locator("#oscal-json .oscal-ln").first).to_be_visible()
    expect(demo.locator("textarea.statement")).to_have_count(0)
    demo.click("#oscal-copy")
    expect(demo.locator("#oscal-copy-status")).to_have_text("Copied")
    demo.locator("#editor .editor-tabs >> text=Statement").click()
    expect(demo.locator("textarea.statement")).to_be_visible()


def test_export_dialog_lists_each_format_once(demo, tmp_path):
    demo.locator(".editor__primary >> text=Accept").click()
    expect(demo.locator("#export-open-top")).to_be_visible()
    expect(demo.locator("#export-dialog")).to_be_hidden()
    demo.click("#export-open-top")
    expect(demo.locator("#export-dialog")).to_be_visible()
    expect(demo.locator("#export-dialog [data-export='oscal']")).to_have_count(1)
    expect(demo.locator("#export-dialog [data-export='xlsx']")).to_be_visible()
    expect(demo.locator("#export-dialog [data-export='csv']")).to_be_visible()
    expect(demo.locator("#export-dialog [data-export='report']")).to_be_visible()
    with demo.expect_download() as dl:
        demo.click("#export-dialog [data-export='oscal']")
    path = tmp_path / "catalog.json"
    dl.value.save_as(path)
    assert path.read_text().startswith("{")
