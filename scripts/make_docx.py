"""Make a Word (.docx) copy of a Markdown policy, for testing and as an example to upload.

    python scripts/make_docx.py examples/acme-information-security-policy-2016.md

Headings become Word headings ("# " the title); table rows and italic notes are left out; every other
line becomes a paragraph. Only the standard library is used.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>'
)
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def paragraph(text: str, style: str = "") -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def docx(paragraphs: list[tuple[str, str]]) -> bytes:
    """A minimal .docx from (style, text) pairs; style is "", "Title" or "Heading1"."""
    body = "".join(paragraph(text, style) for style, text in paragraphs)
    document = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>'
    import io

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/document.xml", document)
    return out.getvalue()


def from_markdown(text: str) -> list[tuple[str, str]]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("|") or (line[0] in "*_" and line[-1] in "*_"):
            continue
        if line.startswith("# "):
            out.append(("Title", line[2:]))
        elif line.startswith("#"):
            out.append(("Heading1", line.lstrip("#").strip()))
        else:
            out.append(("", line))
    return out


if __name__ == "__main__":
    for name in sys.argv[1:]:
        path = Path(name)
        target = path.with_suffix(".docx")
        target.write_bytes(docx(from_markdown(path.read_text(encoding="utf-8"))))
        print(f"wrote {target}")
