"""Three-tab nav: Home, Risk Entry, Policy Clause; one row on a 390px phone."""

from playwright.sync_api import expect

from conftest import add_flow_risk, choose_clause_path, choose_risk_path, finish_open

NAV = "nav.sidebar__nav"
GONE = ("Workspace", "Clauses", "Catalog", "Library", "Export", "Guide", "Risks")


def nav(page):
    return page.locator(NAV)


def test_nav_lists_exactly_three_destinations(page):
    choose_risk_path(page)
    bar = nav(page)
    expect(bar.get_by_role("button", name="Home")).to_be_visible()
    expect(bar.get_by_role("button", name="Risk Entry")).to_be_visible()
    expect(bar.get_by_role("button", name="Policy Clause")).to_be_visible()
    expect(bar.locator(".nav-btn")).to_have_count(3)
    for name in GONE:
        expect(bar.get_by_role("button", name=name, exact=True)).to_have_count(0)
    expect(bar).to_have_attribute("aria-label", "Primary")


def test_home_opens_the_landing(page):
    choose_risk_path(page)
    page.click("[data-nav='home']")
    expect(page.locator("#landing:not([hidden])")).to_be_visible()
    expect(page.locator("#start-from-risks")).to_be_visible()
    expect(page.locator("#flow")).to_be_hidden()


def _current_nav_label(page):
    return nav(page).locator("[aria-current='page'] .nav-btn__label")


def test_risk_entry_opens_identify_risks_and_stays_current(page):
    choose_clause_path(page)
    page.click("[data-nav='risk-entry']")
    expect(page.locator("#identify-title")).to_have_text("What risks have you identified?")
    current = nav(page).locator("[aria-current='page']")
    expect(current).to_have_count(1)
    expect(_current_nav_label(page)).to_have_text("Risk Entry")
    expect(current).to_have_attribute("aria-pressed", "true")
    add_flow_risk(page, "Screens left unlocked at unattended desks.")
    page.click("#identify-continue")
    expect(page.locator("#statements-steps, #flow-step")).to_be_visible()
    expect(_current_nav_label(page)).to_have_text("Risk Entry")


def test_policy_clause_opens_paste_step_and_stays_current(page):
    choose_risk_path(page)
    page.click("[data-nav='policy-clause']")
    expect(page.locator("#paste-form")).to_be_visible()
    expect(page.locator("#landing")).to_be_hidden()
    expect(nav(page)).to_be_visible()
    current = nav(page).locator("[aria-current='page']")
    expect(_current_nav_label(page)).to_have_text("Policy Clause")
    expect(current).to_have_attribute("aria-pressed", "true")
    page.fill("#paste-form textarea", "Users shall lock screens when they leave their desk.")
    page.click("#paste-submit")
    finish_open(page)
    expect(_current_nav_label(page)).to_have_text("Policy Clause")


def test_nav_fits_one_row_on_a_390px_phone(page):
    page.set_viewport_size({"width": 390, "height": 844})
    choose_risk_path(page)
    bar = nav(page)
    expect(bar.locator(".nav-btn")).to_have_count(3)
    boxes = [btn.bounding_box() for btn in bar.locator(".nav-btn").all()]
    assert all(boxes)
    tops = [box["y"] for box in boxes]
    assert max(tops) - min(tops) < 4
    overflow = page.evaluate(
        """() => {
          const sidebar = document.querySelector('#sidebar');
          const nav = document.querySelector('nav.sidebar__nav');
          if (!sidebar || !nav) return true;
          return sidebar.scrollWidth > sidebar.clientWidth + 1
            || nav.scrollWidth > nav.clientWidth + 1;
        }"""
    )
    assert overflow is False
