"""Local policy-as-code starters from a control statement.

Adapted from the MIT-licensed policy-as-code generator in
https://github.com/GRCEngClub/claude-grc-engineering
(plugins/grc-engineer/src/policy-generator.js). Keyword matching against a
small template library; no AI and no network.

Copyright (c) 2025-2026 GRC Engineering Club contributors
Copyright (c) Codify contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import base64
import re
import uuid

STARTER_DISCLAIMER = "Starter — review before use. Not a finished policy."
POLICY_REL = "policy-as-code"
FORMATS = ("rego", "sentinel", "checkov")
EXTENSIONS = {"rego": ".rego", "sentinel": ".sentinel", "checkov": ".yaml"}
MEDIA_TYPES = {"rego": "text/x-rego", "sentinel": "text/plain", "checkov": "text/yaml"}
MAX_CODE = 100_000

# First match wins. More specific families (CIDR, TLS, public access) before
# broader tokens (encrypt, tag).
PATTERNS: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ("network_ingress", (
        ("0.0.0.0/0",), ("0.0.0.0",), ("unrestricted ingress",),
        ("open to the world",), ("security group", "open"),
    )),
    ("backup_retention", (
        ("backup",), ("retention",), ("snapshot",),
    )),
    ("encryption_transit", (
        ("in transit",), ("tls",), ("ssl",), ("https",),
    )),
    ("encryption_rest", (
        ("at rest",), ("encrypt",), ("encryption",), ("kms",), ("encrypted",),
    )),
    ("storage_public", (
        ("public access",), ("public bucket",), ("s3", "public"),
        ("block public",), ("publicly accessible",), ("object-storage", "public"),
        ("object storage", "public"),
    )),
    ("iam_wildcard", (
        ("wildcard",), ("least privilege",), ("iam", "*"), ("action *",),
    )),
    ("required_tags", (
        ("tagging",), ("required tag",), ("must have a", "tag"), ("department tag",),
        ("tags",), ("tag",),
    )),
    ("mfa", (
        ("mfa",), ("2fa",), ("multi-factor",), ("multifactor",), ("two-factor",),
    )),
    ("logging", (
        ("logging",), ("cloudtrail",), ("audit log",), ("audit logging",),
        ("log enabled",),
    )),
)

_WORD = re.compile(r"^[a-z0-9]+$")

EXAMPLE_STATEMENTS = {
    "storage_public": "Block public access on all object-storage buckets.",
    "encryption_rest": "Encrypt all database volumes at rest.",
    "encryption_transit": "Require TLS 1.2 for data in transit.",
    "required_tags": "Require a Department tag on every cloud resource.",
    "mfa": "Require MFA for all privileged accounts.",
    "logging": "Enable audit logging on every production account.",
    "iam_wildcard": "Prohibit IAM policies that use a wildcard action.",
    "backup_retention": "Retain encrypted backups for at least [90] days.",
    "network_ingress": "Deny security-group ingress from 0.0.0.0/0.",
    "generic": "Require users to lock screens when they leave their desk.",
}


def match_pattern(statement: str) -> str:
    """Return the first matching family id, or 'generic'."""
    hay = " ".join(str(statement or "").lower().split())
    for pattern_id, groups in PATTERNS:
        if any(all(_contains(hay, token) for token in group) for group in groups):
            return pattern_id
    return "generic"


def _contains(hay: str, needle: str) -> bool:
    if _WORD.match(needle):
        # Start-of-word so "backup" matches "backups" and "encrypt" matches "encrypted".
        return re.search(rf"(?<![a-z0-9]){re.escape(needle)}", hay) is not None
    return needle in hay


def generate_policy(
    statement: str,
    format: str = "rego",
    *,
    control_id: str = "",
    oscal_id: str = "",
    risk: str = "",
    clause: str = "",
) -> dict:
    """A starter policy for one statement. Deterministic. No I/O."""
    fmt = str(format or "rego").strip().lower()
    if fmt not in FORMATS:
        raise ValueError(f"Unsupported format: {format}. Supported: {', '.join(FORMATS)}")
    text = " ".join(str(statement or "").split())
    pattern = match_pattern(text)
    oscal = " ".join(str(oscal_id or "").split()) or _oscal_id(control_id)
    linked = " ".join(str(risk or clause or "").split()) or "(none)"
    package = _package_name(oscal or control_id)
    header = _header(text, linked, oscal)
    code = _render(fmt, pattern, header, package)
    filename = _filename(oscal or control_id or "starter", fmt)
    return {
        "format": fmt,
        "pattern": pattern,
        "code": code,
        "filename": filename,
        "starter": True,
        "oscal_id": oscal,
        "media_type": MEDIA_TYPES[fmt],
    }


def clean_policy_as_code(value) -> dict | None:
    """Keep a stored starter; drop anything that is not a known format with code."""
    if not isinstance(value, dict):
        return None
    fmt = str(value.get("format") or "").strip().lower()
    if fmt not in FORMATS:
        return None
    code = str(value.get("code") or "")
    if not code or len(code) > MAX_CODE:
        return None
    pattern = str(value.get("pattern") or "generic").strip() or "generic"
    filename = str(value.get("filename") or "").replace("/", "_").replace("\\", "_").strip()
    filename = (filename or f"starter{EXTENSIONS[fmt]}")[:120]
    return {"format": fmt, "pattern": pattern, "code": code, "filename": filename}


def policy_resource_uuid(project_uuid: str, control_id: str, fmt: str) -> str:
    return str(uuid.uuid5(uuid.UUID(project_uuid), f"policy-as-code:{control_id}:{fmt}"))


def decode_policy_code(resource: dict) -> str:
    blob = resource.get("base64") if isinstance(resource, dict) else None
    if not isinstance(blob, dict):
        return ""
    raw = blob.get("value") or ""
    try:
        return base64.b64decode(raw).decode("utf-8")
    except (ValueError, TypeError):
        return ""


def encode_policy_file(code: str, filename: str, fmt: str) -> dict:
    return {
        "filename": filename,
        "media-type": MEDIA_TYPES[fmt],
        "value": base64.b64encode(code.encode("utf-8")).decode("ascii"),
    }


def _oscal_id(control_id: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9._-]+", "-", str(control_id or "")).strip("-") or "control"
    if re.match(r"^[A-Za-z]", raw):
        return raw if raw.startswith("c-") else f"c-{raw}"
    return f"c-{raw}"


def _package_name(control_id: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", str(control_id or "")).strip("_").lower() or "control"
    if token[0].isdigit():
        token = "c_" + token
    return f"codify.starter.{token}"


def _filename(control_id: str, fmt: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", str(control_id or "starter")).strip("-") or "starter"
    return stem + EXTENSIONS[fmt]


def _header(statement: str, linked: str, oscal_id: str) -> str:
    return "\n".join((
        f"# {STARTER_DISCLAIMER}",
        f"# Control statement: {statement or '(none)'}",
        f"# Linked risk or clause: {linked}",
        f"# OSCAL control id: {oscal_id or '(none)'}",
    ))


def _render(fmt: str, pattern: str, header: str, package: str) -> str:
    if fmt == "rego":
        return _rego(pattern, header, package)
    if fmt == "sentinel":
        return _sentinel(pattern, header)
    return _checkov(pattern, header)


def _rego(pattern: str, header: str, package: str) -> str:
    body = REGO_BODIES[pattern]
    return (
        f"{header}\n"
        f"# Enact evaluates result.passed and result.message against input.payload.\n"
        f"# TODO: bind the payload fields below to the evidence this control will test.\n\n"
        f"package {package}\n\n"
        f"import rego.v1\n\n"
        f"{body.rstrip()}\n\n"
        "result := {\n"
        '  "passed": count(deny) == 0,\n'
        '  "message": concat("; ", [msg | some msg in deny]),\n'
        "}\n"
    )


def _sentinel(pattern: str, header: str) -> str:
    return f"{header}\n\nimport \"tfplan/v2\" as tfplan\n\n{SENTINEL_BODIES[pattern].rstrip()}\n"


def _checkov(pattern: str, header: str) -> str:
    return f"{header}\n{CHECKOV_BODIES[pattern].rstrip()}\n"


REGO_BODIES = {
    "storage_public": '''deny contains msg if {
  some bucket in object.get(input.payload, "buckets", [])
  object.get(bucket, "public", false) == true
  msg := "object storage must not be public"
}

deny contains msg if {
  some bucket in object.get(input.payload, "buckets", [])
  not object.get(bucket, "public_access_block", false)
  msg := "object storage must have public access blocked"
}''',
    "encryption_rest": '''deny contains msg if {
  some volume in object.get(input.payload, "volumes", [])
  object.get(volume, "encrypted", false) != true
  msg := "volume must be encrypted at rest"
}''',
    "encryption_transit": '''deny contains msg if {
  some listener in object.get(input.payload, "listeners", [])
  object.get(listener, "tls", false) != true
  msg := "listener must use TLS in transit"
}''',
    "required_tags": '''# TODO: replace Department with the tag keys this control requires.
required := {"Department"}

deny contains msg if {
  some resource in object.get(input.payload, "resources", [])
  tags := object.get(resource, "tags", {})
  some key in required
  not object.get(tags, key, false)
  msg := sprintf("resource missing required tag %s", [key])
}''',
    "mfa": '''deny contains msg if {
  some user in object.get(input.payload, "users", [])
  object.get(user, "mfa_enabled", false) != true
  msg := "account must have MFA enabled"
}''',
    "logging": '''deny contains msg if {
  some account in object.get(input.payload, "accounts", [])
  object.get(account, "logging_enabled", false) != true
  msg := "account logging must be enabled"
}''',
    "iam_wildcard": '''deny contains msg if {
  some statement in object.get(input.payload, "policy_statements", [])
  object.get(statement, "action", "") == "*"
  msg := "IAM policy must not allow action *"
}''',
    "backup_retention": '''deny contains msg if {
  some backup in object.get(input.payload, "backups", [])
  object.get(backup, "enabled", false) != true
  msg := "backup must be enabled"
}''',
    "network_ingress": '''deny contains msg if {
  some rule in object.get(input.payload, "ingress_rules", [])
  object.get(rule, "cidr", "") == "0.0.0.0/0"
  msg := "ingress must not allow 0.0.0.0/0"
}''',
    "generic": '''# TODO: replace this placeholder with a real condition for the control.
deny contains msg if {
  input.todo_unbound_check
  msg := "TODO: replace this placeholder with a real policy condition"
}''',
}

SENTINEL_BODIES = {
    "storage_public": '''# TODO: confirm the Terraform resource type for this control.
main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_s3_bucket" or
    rc.change.after.public_access_block is not null
  }
}''',
    "encryption_rest": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_instance" or
    rc.change.after.root_block_device[0].encrypted is true
  }
}''',
    "encryption_transit": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_lb_listener" or
    rc.change.after.protocol is "HTTPS"
  }
}''',
    "required_tags": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.change.after.tags.Department is not null
  }
}''',
    "mfa": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_iam_user" or
    rc.change.after.mfa_enabled is true
  }
}''',
    "logging": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_cloudtrail" or
    rc.change.after.is_logging is true
  }
}''',
    "iam_wildcard": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_iam_policy" or
    rc.change.after.policy not contains "*"
  }
}''',
    "backup_retention": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_backup_plan" or
    rc.change.after.rule is not null
  }
}''',
    "network_ingress": '''main = rule {
  all tfplan.resource_changes as _, rc {
    rc.type is not "aws_security_group" or
    rc.change.after.ingress none cidr_blocks contains "0.0.0.0/0"
  }
}''',
    "generic": '''main = rule {
  # TODO: replace this placeholder with a real Sentinel condition.
  true
}''',
}

CHECKOV_BODIES = {
    "storage_public": '''metadata:
  name: "Block public object storage"
  id: "CKV2_CODIFY_STORAGE_PUBLIC"
  category: "GENERAL_SECURITY"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_s3_bucket
  attribute: acl
  operator: not_equals
  value: "public-read"
''',
    "encryption_rest": '''metadata:
  name: "Encryption at rest"
  id: "CKV2_CODIFY_ENCRYPTION_REST"
  category: "ENCRYPTION"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_ebs_volume
  attribute: encrypted
  operator: equals
  value: true
''',
    "encryption_transit": '''metadata:
  name: "TLS in transit"
  id: "CKV2_CODIFY_ENCRYPTION_TRANSIT"
  category: "ENCRYPTION"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_lb_listener
  attribute: protocol
  operator: equals
  value: "HTTPS"
''',
    "required_tags": '''metadata:
  name: "Required tags"
  id: "CKV2_CODIFY_REQUIRED_TAGS"
  category: "CONVENTION"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_s3_bucket
  attribute: tags.Department
  operator: exists
''',
    "mfa": '''metadata:
  name: "MFA enabled"
  id: "CKV2_CODIFY_MFA"
  category: "IAM"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_iam_user
  attribute: mfa_enabled
  operator: equals
  value: true
''',
    "logging": '''metadata:
  name: "Logging enabled"
  id: "CKV2_CODIFY_LOGGING"
  category: "LOGGING"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_cloudtrail
  attribute: is_logging
  operator: equals
  value: true
''',
    "iam_wildcard": '''metadata:
  name: "No IAM wildcard actions"
  id: "CKV2_CODIFY_IAM_WILDCARD"
  category: "IAM"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_iam_policy
  attribute: policy
  operator: not_contains
  value: '"Action":"*"'
''',
    "backup_retention": '''metadata:
  name: "Backup enabled"
  id: "CKV2_CODIFY_BACKUP"
  category: "BACKUP"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_backup_vault
  attribute: name
  operator: exists
''',
    "network_ingress": '''metadata:
  name: "No open ingress"
  id: "CKV2_CODIFY_NETWORK_INGRESS"
  category: "NETWORKING"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  cond_type: attribute
  resource_types:
    - aws_security_group
  attribute: ingress.cidr_blocks
  operator: not_contains
  value: "0.0.0.0/0"
''',
    "generic": '''metadata:
  name: "Generic starter"
  id: "CKV2_CODIFY_GENERIC"
  category: "GENERAL_SECURITY"
  guideline: "Starter — review before use. Not a finished policy."
definition:
  # TODO: replace this placeholder with a real Checkov condition.
  cond_type: attribute
  resource_types:
    - aws_instance
  attribute: tags.Name
  operator: exists
''',
}
