# Good and Bad Tests

## Good Tests

**Integration-style**: Test through real interfaces, not mocks of
internal parts.

```python
# GOOD: observable behaviour at the project seam
def test_every_requirement_gets_a_draft_except_the_duplicate(project):
    drafted = {c["clause"] for c in project["controls"]}
    requirements = {c["id"] for c in project["clauses"] if c["type"] == "requirement"}
    assert drafted == requirements - {"6.3"}
```

```python
# GOOD: independent expected — a committed golden, not recomputed OSCAL
def test_control_oscal_matches_the_catalog_control_and_golden():
    project = new_project(parse_text("Users shall lock screens."), source="")
    project["uuid"] = "00000000-0000-4000-8000-000000000000"
    control = control_oscal(project, project["controls"][0]["id"])
    frozen = json.loads(json.dumps(control))
    assert frozen == json.loads(GOLDEN.read_text())
```

```python
# GOOD: Playwright at the page seam the slice named
def test_welcome_splash_then_paste_start(page):
    page.goto(base_url)
    expect(page.locator("h1")).to_have_text("Welcome to Codify")
    page.get_by_role("button", name="Get started").click()
    expect(page.locator("#clause-text")).to_be_visible()
```

Characteristics:

- Tests behavior callers / reviewers care about
- Uses the public API or the page only
- Survives internal refactors
- Describes WHAT, not HOW
- One logical assertion per test
- Expected value is a literal, a key, or a committed golden

## Bad Tests

**Implementation-detail tests**: Coupled to internal structure.

```python
# BAD: mocks an internal collaborator
def test_draft_calls_split_sentences(monkeypatch):
    called = []
    monkeypatch.setattr("codify.draft.split_sentences", lambda text: called.append(text) or ["x"])
    draft("Users shall lock screens.")
    assert called == ["Users shall lock screens."]
```

Red flags:

- Mocking internal collaborators
- Testing private helpers
- Asserting on call counts or order
- Test breaks when refactoring without behavior change
- Test name describes HOW not WHAT

```python
# BAD: bypasses the interface to verify
def test_open_writes_clause_dicts():
    project = new_project(parse_text("Users shall lock screens."), source="")
    assert project["_clauses_raw"][0]["tokens"]  # internal

# GOOD: verifies through the interface
def test_open_sorts_a_requirement():
    project = new_project(parse_text("Users shall lock screens."), source="")
    assert project["clauses"][0]["type"] == "requirement"
```

**Tautological tests**: Expected value restates the implementation.

```python
# BAD: expected is recomputed the way the code computes it
def test_catalog_matches_itself(project):
    expected = to_oscal(project)
    assert to_oscal(project) == expected

# BAD: golden generated from the function under test in the same run
def test_writes_a_fresh_golden(tmp_path, project):
    path = tmp_path / "out.json"
    path.write_text(json.dumps(to_oscal(project)))
    assert to_oscal(project) == json.loads(path.read_text())

# GOOD: expected is an independent, known literal or committed golden
def test_catalog_oscal_version(project):
    assert to_oscal(project)["catalog"]["metadata"]["oscal-version"] == "1.1.2"
```
