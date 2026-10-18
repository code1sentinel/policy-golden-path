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


def test_guide_stays_off_the_nav_and_step_guides_remain(demo):
    expect(demo.locator("nav.sidebar__nav").get_by_role("button", name="Guide")).to_have_count(0)
    expect(demo.locator("#guide")).to_be_hidden()
    expect(demo.locator("#step-guide, #step-guide-open")).to_have_count(2)
