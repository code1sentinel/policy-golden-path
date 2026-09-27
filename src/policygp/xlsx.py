"""Read rows from an Excel workbook (.xlsx) with the standard library only.

An .xlsx file is a zip of XML parts. This reads the cell values of one
worksheet: the first sheet whose header row has the golden-path columns, or
else the first sheet. Formulas are read as their last calculated value.

Workbooks are untrusted input, so the reader refuses anything that looks
hostile: oversized zips or parts (zip bombs), and XML with a DOCTYPE (entity
expansion), which a genuine workbook never contains.
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile
from xml.etree import ElementTree as ET

MAX_UNCOMPRESSED = 50 * 1024 * 1024  # bytes across all parts read
MAX_ROWS = 20000

_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
_R_ID = "{%s}id" % _NS["r"]
_CELL_REF = re.compile(r"([A-Z]+)(\d+)")


class WorkbookError(ValueError):
    pass


def _column_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _read_xml(zf: zipfile.ZipFile, name: str, budget: list[int]) -> ET.Element:
    try:
        info = zf.getinfo(name)
    except KeyError:
        raise WorkbookError(f"workbook is missing {name}") from None
    budget[0] -= info.file_size
    if budget[0] < 0:
        raise WorkbookError("workbook is too large to read")
    data = zf.read(name)
    if b"<!DOCTYPE" in data[:4096].upper():
        raise WorkbookError("workbook contains a DOCTYPE, which is not allowed")
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise WorkbookError(f"workbook part {name} is not valid XML ({exc})") from None


def _shared_strings(zf: zipfile.ZipFile, budget: list[int]) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = _read_xml(zf, "xl/sharedStrings.xml", budget)
    # A shared string is either <t> or rich text runs <r><t>; join all text nodes in each <si>.
    return ["".join(t.text or "" for t in si.iter(f"{{{_NS['m']}}}t")) for si in root.findall("m:si", _NS)]


def _sheet_paths(zf: zipfile.ZipFile, budget: list[int]) -> list[tuple[str, str]]:
    """(sheet name, part path) for each worksheet, in workbook order."""
    workbook = _read_xml(zf, "xl/workbook.xml", budget)
    rels = _read_xml(zf, "xl/_rels/workbook.xml.rels", budget)
    targets = {r.get("Id"): r.get("Target", "") for r in rels.findall("rel:Relationship", _NS)}
    out = []
    for sheet in workbook.findall("m:sheets/m:sheet", _NS):
        target = targets.get(sheet.get(_R_ID), "")
        path = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        out.append((sheet.get("name", ""), path))
    return out


def _cell_value(cell: ET.Element, shared: list[str]) -> str:
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(f"{{{_NS['m']}}}t"))
    value = cell.find("m:v", _NS)
    text = value.text if value is not None and value.text is not None else ""
    if kind == "s":
        try:
            return shared[int(text)]
        except (ValueError, IndexError):
            return ""
    if kind == "b":
        return "TRUE" if text == "1" else "FALSE"
    if kind == "n" and text.endswith(".0"):
        return text[:-2]
    return text


def _rows(zf: zipfile.ZipFile, path: str, shared: list[str], budget: list[int]) -> list[list[str]]:
    root = _read_xml(zf, path, budget)
    rows: list[list[str]] = []
    for row in root.iterfind("m:sheetData/m:row", _NS):
        values: list[str] = []
        for cell in row.findall("m:c", _NS):
            match = _CELL_REF.match(cell.get("r", ""))
            col = _column_index(match.group(1)) if match else len(values)
            while len(values) < col:
                values.append("")  # empty cells are omitted from the XML
            values.append(_cell_value(cell, shared))
        rows.append(values)
        if len(rows) > MAX_ROWS:
            raise WorkbookError(f"worksheet has more than {MAX_ROWS} rows")
    while rows and not any(v.strip() for v in rows[-1]):
        rows.pop()
    return rows


def read_rows(data: bytes, wanted_header: tuple[str, ...] = ()) -> tuple[str, list[list[str]]]:
    """Return (sheet name, rows) from a workbook.

    `wanted_header` is a set of normalised column names; the first sheet whose
    first row contains all of them is chosen, otherwise the first sheet.
    """
    if not data.startswith(b"PK"):
        if data.startswith(b"\xd0\xcf\x11\xe0"):
            raise WorkbookError("this is an old-style .xls workbook: save it as .xlsx or CSV")
        raise WorkbookError("not an Excel .xlsx workbook")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise WorkbookError("not an Excel .xlsx workbook (the file is damaged)") from None
    with zf:
        if sum(i.file_size for i in zf.infolist()) > 4 * MAX_UNCOMPRESSED:
            raise WorkbookError("workbook is too large to read")
        budget = [MAX_UNCOMPRESSED]
        shared = _shared_strings(zf, budget)
        sheets = _sheet_paths(zf, budget)
        if not sheets:
            raise WorkbookError("workbook has no worksheets")
        first = None
        for name, path in sheets:
            rows = _rows(zf, path, shared, budget)
            if first is None:
                first = (name, rows)
            if wanted_header and rows:
                from .tabular import _normalise  # local import: tabular imports this module

                header = {_normalise(h) for h in rows[0] if h}
                if set(wanted_header) <= header:
                    return name, rows
        return first


def _col_letter(index: int) -> str:
    letters = ""
    index += 1
    while index:
        index, rem = divmod(index - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _esc(text: str) -> str:
    text = "".join(ch for ch in text if ch in "\t\n\r" or ord(ch) >= 0x20)  # XML 1.0 forbids other controls
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def write_rows(rows: list[list[str]], sheet_name: str = "Policies", widths: list[int] | None = None) -> bytes:
    """A minimal single-sheet .xlsx holding the rows as text, with the header row frozen."""
    sheet_rows = []
    for r, row in enumerate(rows, start=1):
        cells = "".join(
            f'<c r="{_col_letter(c)}{r}" t="inlineStr"><is><t xml:space="preserve">{_esc(v)}</t></is></c>'
            for c, v in enumerate(row) if v != ""
        )
        sheet_rows.append(f'<row r="{r}">{cells}</row>')
    cols = ""
    if widths:
        cols = "<cols>" + "".join(
            f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths, start=1)
        ) + "</cols>"
    main = _NS["m"]
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        ),
        "_rels/.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{_NS["rel"]}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/></Relationships>'
        ),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{main}" xmlns:r="{_NS["r"]}">'
            f'<sheets><sheet name="{_esc(sheet_name)}" sheetId="1" r:id="rId1"/></sheets></workbook>'
        ),
        "xl/_rels/workbook.xml.rels": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{_NS["rel"]}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/></Relationships>'
        ),
        "xl/worksheets/sheet1.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<worksheet xmlns="{main}">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" '
            'state="frozen"/></sheetView></sheetViews>'
            f'{cols}<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>'
        ),
    }
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, xml in parts.items():
            zf.writestr(name, xml)
    return out.getvalue()
