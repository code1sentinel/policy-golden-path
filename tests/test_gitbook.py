"""Relative-link and structure checks for the GitBook-only docs folder."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "docs" / "book"
GITBOOK_YAML = ROOT / ".gitbook.yaml"
GITBOOK_DOCS_YAML = BOOK / "gitbook-docs.yaml"
# Official schema URL from GitBook's gitbook-docs.yaml examples.
# https://gitbook.com/docs/docs-as-code/git-sync/content-configuration
GITBOOK_DOCS_SCHEMA = "https://api.gitbook.com/gitbook-docs.yaml"

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


def _walk_nodes(node: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(node, dict):
        found.append(node)
        for value in node.values():
            found.extend(_walk_nodes(value))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_nodes(item))
    return found


def _content_directories(node: object) -> list[object]:
    found: list[object] = []
    for item in _walk_nodes(node):
        content = item.get("content")
        if isinstance(content, dict) and "directory" in content:
            found.append(content["directory"])
    return found


def _resolve_git_sync_directory(spec: str) -> Path:
    """Resolve content.directory the way GitBook documents.

    Paths are relative to the Git Sync project directory (`docs/book/`) unless
    they start with `/`, which is the repository root.
    https://gitbook.com/docs/docs-as-code/git-sync/monorepos
    """
    if spec.startswith("/"):
        return (ROOT / spec.lstrip("/")).resolve()
    return (BOOK / spec).resolve()


def test_site_gitbook_docs_yaml_exists_parses_and_paths_resolve():
    assert GITBOOK_DOCS_YAML.is_file(), "docs/book/gitbook-docs.yaml is required for site Git Sync"
    data = yaml.safe_load(GITBOOK_DOCS_YAML.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "gitbook-docs.yaml must parse as a mapping"
    assert data.get("$schema") == GITBOOK_DOCS_SCHEMA
    site = data.get("site")
    assert isinstance(site, dict), "gitbook-docs.yaml must have a site mapping"
    assert site.get("title") == "Codify"
    structure = site.get("structure")
    assert isinstance(structure, list) and structure, "site.structure must list at least one node"
    spaces = [item for item in _walk_nodes(data) if item.get("type") == "space"]
    assert len(spaces) == 1, "site Git Sync maps the curated book as a single space"
    directories = _content_directories(data)
    assert directories, "gitbook-docs.yaml must map at least one space content.directory"
    for spec in directories:
        if spec is None:
            continue
        assert isinstance(spec, str) and spec, f"empty content.directory: {spec!r}"
        mapped = _resolve_git_sync_directory(spec)
        assert mapped.is_dir(), f"content.directory does not exist: {spec} -> {mapped}"
        assert (mapped / "README.md").is_file(), f"README.md missing in {mapped}"
        assert (mapped / "SUMMARY.md").is_file(), f"SUMMARY.md missing in {mapped}"


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


def _relative_link_targets(path: Path) -> list[tuple[str, Path]]:
    found: list[tuple[str, Path]] = []
    text = path.read_text(encoding="utf-8")
    for raw in LINK_RE.findall(text):
        target = _strip_title(raw)
        if not target or target.startswith(SKIP_PREFIXES):
            continue
        target = target.split("#", 1)[0]
        if not target:
            continue
        found.append((target, (path.parent / target).resolve()))
    return found


def test_book_relative_links_and_images_resolve():
    missing: list[str] = []
    for path in markdown_files():
        for target, resolved in _relative_link_targets(path):
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT).as_posix()} -> {target}")
    assert missing == [], "broken relative links in the GitBook folder:\n" + "\n".join(missing)


def test_book_relative_links_do_not_escape_book():
    # Git Sync publishes only docs/book/. A ../ path that leaves that folder
    # works in the repo checkout and 404s on the published site.
    escaped: list[str] = []
    book_root = BOOK.resolve()
    for path in markdown_files():
        for target, resolved in _relative_link_targets(path):
            try:
                resolved.relative_to(book_root)
            except ValueError:
                escaped.append(f"{path.relative_to(ROOT).as_posix()} -> {target}")
    assert escaped == [], (
        "relative links escaping docs/book/ (use GitHub blob/tree URLs):\n"
        + "\n".join(escaped)
    )


def test_required_screenshots_are_present_and_nonempty():
    for name in REQUIRED_SCREENSHOTS:
        path = BOOK / "assets" / name
        assert path.is_file(), f"missing screenshot {name}"
        assert path.stat().st_size > 1000, f"screenshot {name} looks empty"
