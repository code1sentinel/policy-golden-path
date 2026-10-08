"""Workspace and Guide are quieter; the control statement stays obvious."""

from playwright.sync_api import expect


def test_workspace_hides_start_chrome_and_keeps_the_statement_hero(demo):
    expect(demo.locator(".brand__tag")).to_be_hidden()
    expect(demo.locator(".local-note")).to_be_hidden()
    expect(demo.locator("#work-summary")).to_contain_text("38 control drafts")
    expect(demo.locator("textarea.statement")).to_be_visible()
    expect(demo.locator(".editor__primary >> text=Accept")).to_be_visible()
    expect(demo.get_by_text("practices adopted")).to_have_count(0)
    expect(demo.locator(".editor details.fold summary")).to_contain_text("Guidance, risk")
    expect(demo.get_by_placeholder("What could happen without this control")).to_be_hidden()


def test_guide_stacks_practices_in_one_column(demo):
    demo.click("[data-view='guide']")
    expect(demo.locator("#guide:not([hidden])")).to_be_visible()
    expect(demo.locator(".anatomy__key")).to_have_count(0)
    expect(demo.locator(".guide-foot")).to_have_count(0)
    expect(demo.locator("#guide-list .guide").first).to_be_visible()
    expect(demo.locator("#guide-list")).to_contain_text("Weak")
    expect(demo.locator("#guide-list")).to_contain_text("Strong")
    expect(demo.get_by_text("How:", exact=False)).to_have_count(0)
    first = demo.locator("#guide-list .guide").nth(0).bounding_box()
    second = demo.locator("#guide-list .guide").nth(1).bounding_box()
    assert first and second
    assert second["y"] >= first["y"] + first["height"] - 8
    assert abs(second["x"] - first["x"]) < 24
