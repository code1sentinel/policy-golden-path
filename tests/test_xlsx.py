import io
import zipfile

import pytest

from codify.xlsx import MAX_UNCOMPRESSED, WorkbookError, read_rows, write_rows


def _zip(parts: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in parts.items():
            zf.writestr(name, data)
    return out.getvalue()


def test_round_trip_escapes_text_and_skips_control_characters():
    rows = [["clause id", "clause text"], ["4.1", "A & B <c> \"d\""], ["4.2", "line one\nline two\x01"]]
    sheet, read = read_rows(write_rows(rows, sheet_name="Clauses"))
    assert sheet == "Clauses" and read == [rows[0], rows[1], ["4.2", "line one\nline two"]]


def test_picks_the_sheet_with_the_wanted_columns():
    data = _zip_two_sheets()
    sheet, rows = read_rows(data, wanted_header=("clause_text",))
    assert sheet == "Policy" and rows[0] == ["Clause ID", "Clause Text"]


def _zip_two_sheets() -> bytes:
    first = write_rows([["Read me"], ["Fill in the other sheet"]], sheet_name="Read me")
    second = write_rows([["Clause ID", "Clause Text"], ["1.1", "Users shall lock screens."]], sheet_name="Policy")
    # merge: take the first workbook's parts and add the second sheet
    a, b = zipfile.ZipFile(io.BytesIO(first)), zipfile.ZipFile(io.BytesIO(second))
    parts = {n: a.read(n) for n in a.namelist()}
    parts["xl/worksheets/sheet2.xml"] = b.read("xl/worksheets/sheet1.xml")
    parts["xl/workbook.xml"] = parts["xl/workbook.xml"].replace(
        b"</sheets>", b'<sheet name="Policy" sheetId="2" r:id="rId2"/></sheets>')
    parts["xl/_rels/workbook.xml.rels"] = parts["xl/_rels/workbook.xml.rels"].replace(
        b"</Relationships>", b'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                             b'relationships/worksheet" Target="worksheets/sheet2.xml"/></Relationships>')
    return _zip(parts)


def test_rejects_non_workbooks_and_old_xls():
    with pytest.raises(WorkbookError, match="old-style .xls"):
        read_rows(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 100)
    with pytest.raises(WorkbookError, match="not an Excel"):
        read_rows(b"clause id,clause text")
    with pytest.raises(WorkbookError, match="damaged"):
        read_rows(b"PK\x03\x04 garbage")
    with pytest.raises(WorkbookError, match="missing xl/workbook.xml"):
        read_rows(_zip({"hello.txt": b"hi"}))


def test_rejects_doctype_and_zip_bombs():
    good = zipfile.ZipFile(io.BytesIO(write_rows([["a"], ["b"]])))
    parts = {n: good.read(n) for n in good.namelist()}
    evil = dict(parts)
    evil["xl/workbook.xml"] = b'<?xml version="1.0"?><!DOCTYPE lol [<!ENTITY a "aaaa">]>' + parts["xl/workbook.xml"][38:]
    with pytest.raises(WorkbookError, match="DOCTYPE"):
        read_rows(_zip(evil))
    bomb = dict(parts)
    bomb["xl/worksheets/sheet1.xml"] = b" " * (MAX_UNCOMPRESSED + 1)  # compresses to almost nothing
    with pytest.raises(WorkbookError, match="too large"):
        read_rows(_zip(bomb))


openpyxl = pytest.importorskip("openpyxl")


def test_reads_workbooks_written_by_spreadsheet_software():
    wb = openpyxl.Workbook()
    wb.active.title = "Read me"
    ws = wb.create_sheet("Clauses")
    ws.append(["Clause ID", "Clause Text", "Section"])
    ws.append(["5.1", "Access shall be granted on a need-to-know basis.", "Access Control"])
    ws.append([5.2, "User accounts shall be reviewed regularly.", "Access Control"])
    buf = io.BytesIO()
    wb.save(buf)
    sheet, rows = read_rows(buf.getvalue(), wanted_header=("clause_text",))
    assert sheet == "Clauses" and rows[2][:2] == ["5.2", "User accounts shall be reviewed regularly."]


def test_written_workbooks_open_in_openpyxl():
    ws = openpyxl.load_workbook(io.BytesIO(write_rows([["a", "b"], ["1", "2"]], sheet_name="Controls"))).active
    assert ws.title == "Controls" and ws["B2"].value == "2" and ws.freeze_panes == "A2"
