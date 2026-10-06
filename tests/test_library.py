"""Device-wide Statement library: normalize, upsert, search, remove, export."""

import json

import pytest

from codify import api, library


NOW = "2026-10-06T12:00:00+00:00"
LATER = "2026-10-06T13:00:00+00:00"
STATEMENT = "Review user accounts at least every [90] days to remove access that is no longer needed."
SAME = "  REVIEW   user accounts at least every [90] days to remove access that is no longer needed.  "
OTHER = "Restrict access to agency systems to authorised users to prevent unauthorised use."


def _upsert(entries, statement=STATEMENT, **kwargs):
    kwargs.setdefault("now", NOW)
    return library.upsert(entries, statement, **kwargs)


def test_normalize_collapses_whitespace_and_case():
    assert library.normalize_statement(SAME) == library.normalize_statement(STATEMENT)
    assert library.normalize_statement("  A\nB  ") == "a b"
    assert library.normalize_statement("") == ""


def test_upsert_adds_an_entry_with_the_agreed_schema():
    entry, entries = _upsert([], parts={"action": "Review", "scope": "user accounts",
                                        "limit": "at least every [90] days",
                                        "purpose": "to remove access that is no longer needed."})
    assert len(entries) == 1
    assert entry["id"] == "S-001"
    assert entry["statement"] == STATEMENT
    assert entry["source-type"] == "clause"
    assert entry["risk-id"] == ""
    assert entry["accepted-at"] == NOW
    assert entry["last-used-at"] == ""
    assert entry["parts"]["action"] == "Review"
    assert set(entry) == {"id", "statement", "parts", "source-type", "risk-id",
                          "accepted-at", "last-used-at"}


def test_duplicate_normalized_text_updates_metadata_not_a_second_row():
    first, entries = _upsert([], source_type="clause")
    second, entries = _upsert(entries, SAME, source_type="risk", risk_id="R-001", now=LATER)
    assert len(entries) == 1
    assert second["id"] == first["id"] == "S-001"
    assert second["source-type"] == "risk"
    assert second["risk-id"] == "R-001"
    assert second["accepted-at"] == LATER
    assert second["statement"] == " ".join(SAME.split())  # latest wording, whitespace collapsed


def test_use_sets_last_used_without_a_second_row():
    _, entries = _upsert([])
    used, entries = library.upsert(entries, STATEMENT, used=True, now=LATER)
    assert len(entries) == 1
    assert used["last-used-at"] == LATER
    assert used["accepted-at"] == NOW


def test_remove_drops_only_that_row():
    _, entries = _upsert([])
    _, entries = _upsert(entries, OTHER, now=LATER)
    assert [e["id"] for e in entries] == ["S-001", "S-002"]
    left = library.remove(entries, "S-001")
    assert [e["id"] for e in left] == ["S-002"]
    assert library.remove(left, "missing") == left


def test_search_filters_and_prefers_recent_use():
    _, entries = _upsert([])
    _, entries = _upsert(entries, OTHER, source_type="risk", risk_id="R-001", now=LATER)
    _, entries = library.upsert(entries, STATEMENT, used=True, now="2026-10-06T14:00:00+00:00")
    hits = library.search(entries, "review")
    assert [e["id"] for e in hits] == ["S-001"]
    ordered = library.search(entries, "")
    assert [e["id"] for e in ordered] == ["S-001", "S-002"]


def test_export_csv_and_json_are_local_payloads():
    _, entries = _upsert([], parts={"action": "Review", "scope": "user accounts",
                                    "limit": None, "purpose": None})
    payload = json.loads(library.to_json(entries))
    assert payload[0]["id"] == "S-001" and payload[0]["statement"] == STATEMENT
    csv_text = library.to_csv(entries)
    assert csv_text.startswith("id,statement,")
    assert "S-001" in csv_text and STATEMENT in csv_text
    # formula-escape, same rule as catalog CSV
    _, evil = _upsert([], statement="=HYPERLINK(\"http://evil.example\")")
    assert "'=HYPERLINK" in library.to_csv(evil)


def test_empty_statement_is_rejected():
    with pytest.raises(ValueError, match="statement"):
        library.upsert([], "   ")


def test_api_upsert_search_remove_export_and_does_not_touch_oscal():
    out = api.call({"action": "library_upsert", "library": [], "statement": STATEMENT,
                    "source_type": "clause", "now": NOW})
    assert out["entry"]["id"] == "S-001"
    again = api.call({"action": "library_upsert", "library": out["library"],
                      "statement": SAME, "source_type": "clause", "now": LATER})
    assert len(again["library"]) == 1 and again["entry"]["accepted-at"] == LATER
    found = api.call({"action": "library_search", "library": again["library"], "query": "accounts"})
    assert found["entries"][0]["id"] == "S-001"
    used = api.call({"action": "library_upsert", "library": again["library"],
                     "statement": STATEMENT, "used": True, "now": LATER})
    assert used["entry"]["last-used-at"] == LATER
    csv_out = api.call({"action": "library_export", "library": used["library"], "format": "csv"})
    assert csv_out["name"] == "statement-library.csv" and csv_out["mime"] == "text/csv"
    json_out = api.call({"action": "library_export", "library": used["library"], "format": "json"})
    assert json_out["name"] == "statement-library.json"
    removed = api.call({"action": "library_remove", "library": used["library"], "id": "S-001"})
    assert removed["library"] == []
    opened = api.call({"action": "open", "text": "Users shall lock screens."})
    saved = api.call({"action": "export", "format": "oscal", "project": opened["project"]})
    assert "statement-library" not in saved["content"]
    assert "codify:statements" not in saved["content"]


def test_library_actions_reject_bad_input():
    with pytest.raises(api.BadRequest, match="enter a control statement"):
        api.call({"action": "library_upsert", "library": [], "statement": ""})
    with pytest.raises(api.BadRequest, match="'format' must be"):
        api.call({"action": "library_export", "library": [], "format": "xlsx"})
    with pytest.raises(api.BadRequest, match="'library' must be a list"):
        api.call({"action": "library_search", "library": {}, "query": "x"})
