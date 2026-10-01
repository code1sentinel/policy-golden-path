"""Read a legacy policy into numbered clauses: from pasted text, a Word document, or a table.

Pasted text and Word documents are split on the policy's own numbering:

    ## 5. Access Control                 a section heading (Markdown or "5. Access Control")
    5.1 Access to Agency systems ...     a clause, numbered 5.1
    (a) ... / a) ...                     a lettered item, numbered 5.1(a)
    - ... / • ...                        a bullet, numbered 5.1-1

Lines that carry on a clause are joined to it; an unnumbered paragraph becomes
a clause numbered after its section (5-p1). A table (CSV or Excel) has one
clause per row: a clause id column and a clause text column.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET


@dataclass
class Clause:
    id: str  # the policy's own number ("5.1"), or one made up from its section ("5-p1")
    text: str
    section: str = ""  # section number ("5")
    heading: str = ""  # section title ("Access Control")


@dataclass
class Policy:
    title: str
    clauses: list[Clause] = field(default_factory=list)


_MD_HEADING = re.compile(r"^#{1,6}\s+(?:(\d+)\.?\s+)?(.+?)\s*#*$")
_PLAIN_HEADING = re.compile(r"^(\d{1,2})\.?\s+([A-Z][^.;:]{1,80})$")  # "5. Access Control": no full stop
_NUMBERED = re.compile(r"^(\d{1,2}(?:\.\d{1,3}){1,3})\.?\s+(\S.*)$")
_LETTERED = re.compile(r"^\(?([a-z]|[ivx]{1,4})[.)]\s+(\S.*)$")
_BULLET = re.compile(r"^[-•*▪◦]\s+(\S.*)$")
_SKIP = re.compile(r"^(\|.*\||[*_].*[*_]|-{3,}|={3,})$")  # Markdown tables, italic notes, rules


def parse_text(text: str, title: str = "") -> Policy:
    """Clauses from pasted text, or the paragraphs of a Word document rendered as lines."""
    policy = Policy(title=title)
    section, heading = "", ""
    current: Clause | None = None
    parent = ""  # the numbered clause that lettered items and bullets belong to
    counters: dict[str, int] = {}
    lead_ins: set[str] = set()  # clauses that only introduce lettered items

    def start(cid: str, body: str) -> Clause:
        clause = Clause(cid, body.strip(), section, heading)
        policy.clauses.append(clause)
        return clause

    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            current = None  # a blank line ends the clause; lettered items still attach to `parent`
            continue
        if _SKIP.match(line):
            continue
        if m := _MD_HEADING.match(line):
            number, name = m.group(1) or "", m.group(2).strip()
            if line.startswith("# ") and not number and not policy.title:
                policy.title = name
            else:
                section, heading, current, parent = number or section, name, None, ""
            continue
        if (m := _PLAIN_HEADING.match(line)) and not _NUMBERED.match(line):
            section, heading, current, parent = m.group(1), m.group(2).strip(), None, ""
            continue
        if m := _NUMBERED.match(line):
            current = start(m.group(1), m.group(2))
            parent = m.group(1)
            if not section:
                section = m.group(1).split(".")[0]
                current.section = section
            continue
        if parent and (m := _LETTERED.match(line)):
            body = m.group(2)
            lead = next((c for c in policy.clauses if c.id == parent), None)
            if lead is not None and lead.text.endswith(":"):
                # "1.2 Users shall: (a) not share passwords" -> each item carries the lead-in
                body = f"{lead.text[:-1].strip()} {body}"
                lead_ins.add(parent)
            current = start(f"{parent}({m.group(1)})", body)
            continue
        if m := _BULLET.match(line):
            base = parent or section or "p"
            counters[base] = counters.get(base, 0) + 1
            current = start(f"{base}-{counters[base]}", m.group(1))
            continue
        if current is not None:
            current.text = f"{current.text} {line}"  # a wrapped line carries on the clause
            continue
        if not policy.title and not policy.clauses:
            policy.title = line  # a first line on its own is the title
            continue
        base = section or "p"
        counters[f"{base}-p"] = counters.get(f"{base}-p", 0) + 1
        current = start(f"{base}-p{counters[f'{base}-p']}", line)
        parent = ""
    policy.clauses = [c for c in policy.clauses if c.text and c.id not in lead_ins]
    return policy


# --- Word ---------------------------------------------------------------------------------------

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_DOCX = 20 * 1024 * 1024  # uncompressed bytes of the document part


def docx_lines(data: bytes) -> tuple[str, list[str]]:
    """(title, lines) from a Word document: headings as Markdown headings, paragraphs as lines."""
    if not data.startswith(b"PK"):
        if data.startswith(b"\xd0\xcf\x11\xe0"):
            raise ValueError("this is an old-style .doc file: save it as .docx")
        raise ValueError("not a Word .docx document")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError("not a Word .docx document (the file is damaged)") from None
    with zf:
        try:
            info = zf.getinfo("word/document.xml")
        except KeyError:
            raise ValueError("not a Word .docx document (no word/document.xml)") from None
        if info.file_size > MAX_DOCX:
            raise ValueError("document is too large to read")
        xml = zf.read(info)
    if b"<!DOCTYPE" in xml[:4096].upper():
        raise ValueError("document contains a DOCTYPE, which is not allowed")
    root = ET.fromstring(xml)
    title, lines = "", []
    for p in root.iter(f"{_W}p"):
        text = "".join(t.text or "" for t in p.iter(f"{_W}t")).strip()
        if not text:
            lines.append("")
            continue
        style = p.find(f"{_W}pPr/{_W}pStyle")
        name = (style.get(f"{_W}val") or "") if style is not None else ""
        if name.lower() == "title" and not title:
            title = text
        elif m := re.match(r"heading\s*(\d)", name, re.I):
            lines += ["", "#" * (int(m.group(1)) + 1) + " " + text, ""]
        elif p.find(f"{_W}pPr/{_W}numPr") is not None and not _NUMBERED.match(text):
            lines.append("- " + text)  # Word's own list numbering is not in the text: keep it as an item
        else:
            lines.append(text)
    return title, lines


def parse_docx(data: bytes) -> Policy:
    title, lines = docx_lines(data)
    return parse_text("\n".join(lines), title=title)


# --- Tables ---------------------------------------------------------------------------------------

_ID_COLUMNS = ("clause_id", "id", "clause", "clause_number", "number", "ref", "reference", "no")
_TEXT_COLUMNS = ("clause_text", "text", "policy_clause", "requirement", "statement", "wording", "policy_statement")
_SECTION_COLUMNS = ("section", "heading", "section_title", "chapter")


def _norm(header: str) -> str:
    return "_".join(header.strip().lower().replace("-", " ").replace("_", " ").split())


def parse_rows(rows: list[list[str]], title: str = "") -> Policy:
    """One clause per row, with a clause text column and, optionally, clause id and section columns."""
    if not rows:
        raise ValueError("the table is empty")
    header = [_norm(h) for h in rows[0]]
    text_col = next((header.index(c) for c in _TEXT_COLUMNS if c in header), None)
    if text_col is None:
        raise ValueError("the table needs a clause text column (named 'clause text' or 'text'); "
                         "a 'clause id' column is optional")
    id_col = next((header.index(c) for c in _ID_COLUMNS if c in header and header.index(c) != text_col), None)
    section_col = next((header.index(c) for c in _SECTION_COLUMNS if c in header), None)
    policy = Policy(title=title)
    for n, row in enumerate(rows[1:], start=1):
        cell = lambda i: row[i].strip() if i is not None and i < len(row) else ""  # noqa: E731
        text = cell(text_col)
        if not text:
            continue
        cid = cell(id_col) or f"row-{n}"
        section = cell(section_col)
        policy.clauses.append(Clause(cid, text, section=cid.split(".")[0] if "." in cid else "", heading=section))
    if not policy.clauses:
        raise ValueError("the table has no clause text")
    return policy


def parse_csv(content: str, title: str = "") -> Policy:
    content = content.lstrip("﻿")
    first = content.splitlines()[0] if content.strip() else ""
    try:
        dialect = csv.Sniffer().sniff(first, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return parse_rows(list(csv.reader(io.StringIO(content), dialect)), title)


def read_policy(name: str, content: str | bytes) -> Policy:
    """A policy from a file: Word (.docx), CSV, Excel (.xlsx), or text (anything else)."""
    lower = name.lower()
    stem = re.sub(r"\.[a-z0-9]+$", "", name.rsplit("/", 1)[-1])
    if lower.endswith((".docx", ".doc")):
        if isinstance(content, str):
            raise ValueError("a Word document must be read as bytes")
        policy = parse_docx(content)
    elif lower.endswith((".xlsx", ".xls")):
        if isinstance(content, str):
            raise ValueError("an Excel workbook must be read as bytes")
        from .xlsx import read_rows

        _, rows = read_rows(content, wanted_header=("clause_text",))
        policy = parse_rows(rows)
    else:
        if isinstance(content, bytes):
            try:
                content = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                raise ValueError("file is not UTF-8 text") from None
        policy = parse_csv(content) if lower.endswith(".csv") else parse_text(content)
    if not policy.clauses:
        raise ValueError("no clauses found: number them (4.1, 4.2 …) or put one per paragraph")
    policy.title = policy.title or stem
    return policy
