import base64
import datetime
import io
import zipfile

import pytest

from vitals.models import IDENTIFIED_RISK, IMPLEMENTATION, RECOMMENDATION, RISK_STATEMENT
from vitals.service import parse_document
from vitals.tabular import parse_xlsx, template_xlsx
from vitals.xlsx import MAX_UNCOMPRESSED, WorkbookError, read_rows, write_rows


def test_template_round_trips():
    items = parse_xlsx(template_xlsx(), "t.xlsx")
    assert [s.kind for s in items] == [IDENTIFIED_RISK] + [IMPLEMENTATION, RISK_STATEMENT, RECOMMENDATION] * 2
    assert items[3].deadline == "2026-11-30" and items[2].ratings == {"likelihood": "high", "impact": "high"}


def test_writer_escapes_text_and_skips_control_characters():
    rows = [["policy intent", "control statement", "risk statement", "recommendation"],
            ["A & B <c> \"d\"", "line one\nline two\x01", "", ""]]
    _, read = read_rows(write_rows(rows))
    assert read[1][:2] == ["A & B <c> \"d\"", "line one\nline two"]


def test_parse_document_dispatches_by_extension():
    items = parse_document("Policies.XLSX", template_xlsx())
    assert len(items) == 7
    with pytest.raises(ValueError, match="must be read as bytes"):
        parse_document("p.xlsx", "text")


def _zip(parts: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in parts.items():
            zf.writestr(name, data)
    return out.getvalue()


def test_rejects_non_workbooks_and_old_xls():
    with pytest.raises(WorkbookError, match="old-style .xls"):
        read_rows(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 100)
    with pytest.raises(WorkbookError, match="not an Excel"):
        read_rows(b"policy intent,control statement")
    with pytest.raises(WorkbookError, match="damaged"):
        read_rows(b"PK\x03\x04 garbage")
    with pytest.raises(WorkbookError, match="missing xl/workbook.xml"):
        read_rows(_zip({"hello.txt": b"hi"}))


def test_rejects_doctype_and_zip_bombs():
    good = zipfile.ZipFile(io.BytesIO(template_xlsx()))
    parts = {n: good.read(n) for n in good.namelist()}
    evil = dict(parts)
    evil["xl/workbook.xml"] = b'<?xml version="1.0"?><!DOCTYPE lol [<!ENTITY a "aaaa">]>' + parts["xl/workbook.xml"][38:]
    with pytest.raises(WorkbookError, match="DOCTYPE"):
        read_rows(_zip(evil))
    bomb = dict(parts)
    bomb["xl/worksheets/sheet1.xml"] = b" " * (MAX_UNCOMPRESSED + 1)  # compresses to almost nothing
    with pytest.raises(WorkbookError, match="too large"):
        read_rows(_zip(bomb))


def test_wrong_columns_name_the_sheet():
    data = write_rows([["name", "value"], ["a", "b"]], sheet_name="Budget")
    with pytest.raises(ValueError, match="worksheet 'Budget': CSV needs the columns"):
        parse_xlsx(data)


openpyxl = pytest.importorskip("openpyxl")


def _excel_style_workbook() -> bytes:
    """A workbook as spreadsheet software writes it: shared strings, styles, dates, several sheets."""
    wb = openpyxl.Workbook()
    wb.active.title = "Read me"
    wb.active["A1"] = "Fill in the Policies sheet"
    ws = wb.create_sheet("Policies")
    ws.append(["Control ID", "Policy Intent", "Control Statement", "Risk Statement", "Recommendation",
               "Target Date", "Likelihood"])
    ws.append(["ac-2", "Reviewed quarterly.", "The IAM team reviews access quarterly in Okta.", "", "", None, None])
    ws.append(["au-6", "Logs reviewed daily.", "", "Logs are not reviewed.", "Enable daily review in Splunk.",
               datetime.date(2026, 12, 1), "high"])
    ws["A2"].font = openpyxl.styles.Font(bold=True)
    ws.append([])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_reads_workbooks_written_by_spreadsheet_software():
    items = parse_xlsx(_excel_style_workbook(), "policies.xlsx")
    assert [(s.kind, s.key) for s in items] == [
        (IMPLEMENTATION, "ac-2 [Row 2]"), (RISK_STATEMENT, "Row 3 [au-6]"), (RECOMMENDATION, "Row 3 [au-6]")]
    assert items[0].policy_intent == "Reviewed quarterly."
    assert items[2].deadline == "2026-12-01" and items[1].ratings == {"likelihood": "high"}


def test_template_opens_in_openpyxl():
    ws = openpyxl.load_workbook(io.BytesIO(template_xlsx())).active
    assert ws.title == "Policies" and ws["A1"].value == "policy intent" and ws.freeze_panes == "A2"


def test_web_upload_accepts_base64_workbooks():
    from vitals.api import batch_statements

    doc = {"name": "policies.xlsx", "content_base64": base64.b64encode(_excel_style_workbook()).decode()}
    items, files, names = batch_statements({"documents": [doc]})
    assert files == [{"name": "policies.xlsx", "count": 3, "error": None}] and names == ["policies.xlsx"] * 3
