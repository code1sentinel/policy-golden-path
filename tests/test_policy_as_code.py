"""Local policy-as-code starters: keyword matching, headers, formats, no AI."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from codify.policy_as_code import (
    EXAMPLE_STATEMENTS,
    FORMATS,
    STARTER_DISCLAIMER,
    generate_policy,
    match_pattern,
)

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "src/codify/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "src/codify/static/app.css").read_text(encoding="utf-8")
INDEX = (ROOT / "src/codify/static/index.html").read_text(encoding="utf-8")

MATCH_CASES = [
    *EXAMPLE_STATEMENTS.items(),
    ("storage_public", "Ensure no S3 buckets are public."),
    ("encryption_rest", "All EC2 instances must have encryption enabled."),
]


@pytest.mark.parametrize("pattern, statement", MATCH_CASES)
def test_match_pattern_covers_each_family_and_fallback(pattern, statement):
    assert match_pattern(statement) == pattern


def test_transit_wins_over_generic_encrypt_and_public_wins_over_tags():
    assert match_pattern("Encrypt data in transit with TLS.") == "encryption_transit"
    assert match_pattern(
        "Ensure no S3 buckets are public and all must have a Department tag."
    ) == "storage_public"


def test_generate_rego_header_and_opa_v1_shape():
    out = generate_policy(
        "Block public access on all object-storage buckets.",
        "rego",
        control_id="c1",
        oscal_id="c-c1",
        risk="Public buckets expose customer data.",
        clause="S3 buckets shall not be public.",
    )
    assert out["format"] == "rego"
    assert out["pattern"] == "storage_public"
    assert out["starter"] is True
    assert out["filename"].endswith(".rego")
    code = out["code"]
    assert STARTER_DISCLAIMER in code
    assert "Control statement: Block public access on all object-storage buckets." in code
    assert "Linked risk or clause: Public buckets expose customer data." in code
    assert "OSCAL control id: c-c1" in code
    assert "import rego.v1" in code
    assert "deny contains msg if" in code
    assert '"passed"' in code
    assert "GRC Engineering Club" not in code
    assert "GRCEngClub" not in code


def test_generic_skeleton_has_todos():
    out = generate_policy("Require users to lock screens when they leave their desk.", "rego", control_id="lock")
    assert out["pattern"] == "generic"
    assert "TODO" in out["code"]
    assert STARTER_DISCLAIMER in out["code"]


@pytest.mark.parametrize("fmt, ext", [("rego", ".rego"), ("sentinel", ".sentinel"), ("checkov", ".yaml")])
def test_optional_formats_default_rego(fmt, ext):
    out = generate_policy("Require MFA for all privileged accounts.", fmt, control_id="mfa-1")
    assert out["format"] == fmt
    assert out["pattern"] == "mfa"
    assert out["filename"].endswith(ext)
    assert STARTER_DISCLAIMER.split("—")[0].strip() in out["code"] or STARTER_DISCLAIMER in out["code"]


def test_unsupported_format_is_an_error():
    with pytest.raises(ValueError, match="Unsupported format"):
        generate_policy("Require MFA.", "aws-config")


def test_same_statement_is_deterministic():
    a = generate_policy("Enable audit logging on every production account.", "rego", control_id="log")
    b = generate_policy("Enable audit logging on every production account.", "rego", control_id="log")
    assert a == b


def test_every_pattern_has_rego_sentinel_and_checkov_bodies():
    assert set(FORMATS) == {"rego", "sentinel", "checkov"}
    for pattern, statement in MATCH_CASES:
        for fmt in FORMATS:
            out = generate_policy(statement, fmt, control_id="x")
            assert out["pattern"] == pattern
            assert out["code"].strip()


def test_ui_copy_names_a_starter_not_a_club():
    assert "Generate Rego starter" in JS
    assert "starter to review" in JS.lower() or "Starter to review" in JS
    assert "not a finished policy" in JS.lower() or "Not a finished policy" in JS
    assert "GRC Engineering Club" not in JS
    assert "GRC Engineering Club" not in INDEX
    assert "rego-starter" in CSS


@pytest.mark.skipif(shutil.which("opa") is None, reason="opa binary not on PATH")
def test_generated_rego_passes_opa_check(tmp_path):
    for pattern, statement in MATCH_CASES:
        out = generate_policy(statement, "rego", control_id=pattern)
        path = tmp_path / f"{pattern}.rego"
        path.write_text(out["code"], encoding="utf-8")
        proc = subprocess.run(["opa", "check", str(path)], capture_output=True, text=True)
        assert proc.returncode == 0, f"{pattern}: {proc.stderr or proc.stdout}"
