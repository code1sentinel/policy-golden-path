"""Relative-link and structure checks for the GitBook-only docs folder."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "docs" / "book"
GITBOOK_YAML = ROOT / ".gitbook.yaml"

LINK_RE = re.compile(r"!?\[(?:[^\]]*)\]\(([^)]+)\)")
SUMMARY_ITEM_RE = re.compile(r"^\s*\*\s+\[(?:[^\]]+)\]\(([^)]+)\)\s*$", re.MULTILINE)
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#", "{{")

REQUIRED_SCREENSHOTS = (
    "welcome-splash.png",
    "paste-box.png",
    "drafted-step.png",
    "control-review.png",
    "export-dialog.png",
    "catalog.png",
    "library.png",
)


def _strip_title(target: str) -> str:
    target = target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    if " " in target:
        target = target.split(" ", 1)[0]
    return target


def _yaml_value(text: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*(\S+)\s*$", text, re.MULTILINE)
    assert match, f"missing {key} in .gitbook.yaml"
    return match.group(1).strip().strip("'\"")


def markdown_files() -> list[Path]:
    return sorted(p for p in BOOK.rglob("*.md") if p.is_file())


def test_gitbook_yaml_points_at_curated_book():
    text = GITBOOK_YAML.read_text(encoding="utf-8")
    root = _yaml_value(text, "root").rstrip("/")
    assert root in {"./docs/book", "docs/book", "./docs/book/"}
    readme = _yaml_value(text, "readme")
    summary = _yaml_value(text, "summary")
    book_root = (ROOT / root.lstrip("./")).resolve()
    assert book_root == BOOK.resolve()
    assert (book_root / readme).is_file()
    assert (book_root / summary).is_file()
    assert "docs/prd.md" not in text
    assert "docs/prds" not in text


def test_summary_lists_existing_pages_and_no_orphans():
    summary = (BOOK / "SUMMARY.md").read_text(encoding="utf-8")
    listed = [_strip_title(m.group(1)) for m in SUMMARY_ITEM_RE.finditer(summary)]
    assert listed, "SUMMARY.md has no page entries"
    listed_paths = []
    for rel in listed:
        path = (BOOK / rel).resolve()
        assert path.is_file(), f"SUMMARY entry missing: {rel}"
        listed_paths.append(path)
    pages = [p for p in markdown_files() if p.name != "SUMMARY.md"]
    orphans = [p.relative_to(BOOK).as_posix() for p in pages if p.resolve() not in {x.resolve() for x in listed_paths}]
    assert orphans == [], f"book pages not listed in SUMMARY.md: {orphans}"


def test_book_relative_links_and_images_resolve():
    missing: list[str] = []
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        for raw in LINK_RE.findall(text):
            target = _strip_title(raw)
            if not target or target.startswith(SKIP_PREFIXES):
                continue
            target = target.split("#", 1)[0]
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT).as_posix()} -> {target}")
    assert missing == [], "broken relative links in the GitBook folder:\n" + "\n".join(missing)


def test_required_screenshots_are_present_and_nonempty():
    for name in REQUIRED_SCREENSHOTS:
        path = BOOK / "assets" / name
        assert path.is_file(), f"missing screenshot {name}"
        assert path.stat().st_size > 1000, f"screenshot {name} looks empty"
