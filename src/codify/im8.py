"""Mapping control statements to Singapore's IM8 Reform catalog.

The catalog ships with Codify (data/im8-reform.json, built by scripts/make_im8.py
from GovTech's tech-standards repository, MIT-licensed). `suggest` ranks IM8
controls for a statement by shared wording, weighted so that rare, telling words
("backup", "MFA", "sanitise") count for more than common ones ("ensure",
"system"). Suggestions are only suggestions: a mapping counts once a person
confirms it, and `coverage` reports which IM8 controls the confirmed mappings
cover, by domain and by profile level.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from importlib import resources

RISKS = ("low", "medium")
LEVEL_LABELS = {0: "Level 0 (must-have)", 1: "Level 1 (should-have)", 2: "Level 2 (good-to-have)"}
MIN_SCORE = 0.12  # below this, a suggestion is noise
CATALOG_URL = "https://github.com/GovTechSG/tech-standards/blob/main/catalogs/im8-reform.json"

_STOP = set("""a an and any are as at be been by can for from has have if in into is it its least more must
not of on or other over shall should such than that the their them then there these they this those to under
upon use used using via user users was were when where which while who will with within without all each every ensure
including e g eg etc may only also per through prior after before against between both same new day days time times""".split())

# Words that mean the same thing for mapping, written the way IM8 writes them.
_SYNONYMS = {
    "back": "backup", "backups": "backup", "backed": "backup",
    "multi": "mfa", "factor": "mfa", "2fa": "mfa", "two": "mfa", "otp": "mfa",
    "antivirus": "malware", "virus": "malware", "viruses": "malware", "anti": "malware",
    "patching": "patch", "patches": "patch", "patched": "patch", "update": "patch", "updates": "patch",
    "logging": "log", "logs": "log", "logged": "log", "audit": "log",
    "encrypted": "encrypt", "encryption": "encrypt", "cryptographic": "crypto", "cryptography": "crypto",
    "admin": "privileged", "administrator": "privileged", "administrative": "privileged", "root": "privileged",
    "passwords": "password", "passphrase": "password", "credentials": "credential",
    "leaver": "inactive", "leavers": "inactive", "leave": "inactive", "dormant": "inactive", "expired": "inactive",
    "disposal": "sanitise", "dispose": "sanitise", "disposed": "sanitise", "wipe": "sanitise", "wiped": "sanitise",
    "erase": "sanitise", "shred": "sanitise", "destroy": "sanitise", "destruction": "sanitise",
    "sanitisation": "sanitise", "sanitization": "sanitise", "sanitize": "sanitise",
    "firewalls": "firewall", "vulnerabilities": "vulnerability", "scans": "scan", "scanning": "scan",
    "penetration": "testing", "pentest": "testing", "recovery": "recover", "restore": "recover", "restored": "recover",
    "incidents": "incident", "breach": "incident", "breaches": "incident",
    "vendor": "supplier", "vendors": "supplier", "suppliers": "supplier", "contractor": "supplier",
    "contractors": "supplier", "third": "supplier", "outsourced": "supplier",
    "confidential": "sensitive", "personal": "sensitive", "leakage": "loss", "exfiltration": "loss",
    "removable": "media", "usb": "media", "laptop": "endpoint", "laptops": "endpoint", "desktop": "endpoint",
    "desktops": "endpoint", "devices": "device", "workstation": "endpoint", "workstations": "endpoint",
    "review": "review", "reviewed": "review", "reviews": "review", "recertify": "review",
    "timeout": "session", "idle": "session", "screen": "session", "inactivity": "session",
    "failed": "brute", "attempts": "brute", "lockout": "brute", "brute": "brute", "guessing": "brute",
    "room": "physical", "rooms": "physical", "datacentre": "physical", "datacenter": "physical",
    "physical": "physical", "premises": "physical", "visitors": "physical", "visitor": "physical",
    "escort": "physical", "escorted": "physical", "badge": "physical",
}


def _stem(word: str) -> str:
    for suffix in ("ations", "ation", "ings", "ing", "ies", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return word


def tokens(text: str) -> list[str]:
    text = re.sub(r"\[[^\]]*\]", " ", text)  # parameters: "[time period (days)]", "[N]"
    words = re.findall(r"[a-z0-9]+", text.lower().replace("e.g.", " "))
    out = []
    for w in words:
        if w in _STOP or len(w) < 2 or w.isdigit():
            continue
        out.append(_SYNONYMS.get(w) or _SYNONYMS.get(_stem(w)) or _stem(w))
    return out


@lru_cache(maxsize=1)
def catalog() -> dict:
    data = json.loads(resources.files("codify").joinpath("data", "im8-reform.json").read_text(encoding="utf-8"))
    data["by_id"] = {c["id"]: c for c in data["controls"]}
    return data


@lru_cache(maxsize=1)
def _index():
    """Weighted word vectors for every IM8 control: the title counts twice, guidance half."""
    docs = {}
    for c in catalog()["controls"]:
        counts = Counter()
        for w in tokens(c["title"]):
            counts[w] += 2
        for w in tokens(c["statement"]):
            counts[w] += 1
        for w in tokens(c["guidance"]):
            counts[w] += 0.5
        docs[c["id"]] = counts
    n = len(docs)
    df = Counter(w for counts in docs.values() for w in counts)
    idf = {w: math.log((1 + n) / (1 + k)) + 1 for w, k in df.items()}
    vectors = {cid: _unit({w: v * idf[w] for w, v in counts.items()}) for cid, counts in docs.items()}
    return idf, vectors


def _unit(vec: dict[str, float]) -> dict[str, float]:
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {w: v / norm for w, v in vec.items()}


def suggest(text: str, context: str = "", limit: int = 3, exclude: tuple[str, ...] = ()) -> list[dict]:
    """IM8 controls that may match a statement (the legacy clause can be given as context), best first."""
    idf, vectors = _index()
    counts = Counter()
    for w in tokens(text):
        counts[w] += 1
    for w in tokens(context):
        counts[w] += 0.5
    query = _unit({w: v * idf[w] for w, v in counts.items() if w in idf})
    if not query:
        return []
    scored = []
    for cid, vec in vectors.items():
        if cid in exclude:
            continue
        score = sum(v * vec.get(w, 0.0) for w, v in query.items())
        if score >= MIN_SCORE:
            scored.append((score, cid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [{**brief(cid), "score": round(s, 3)} for s, cid in scored[:limit]]


def brief(cid: str) -> dict:
    c = catalog()["by_id"][cid]
    return {"id": cid, "title": c["title"], "domain": catalog()["domains"][c["domain"]],
            "statement": c["statement"], "levels": c["levels"]}


def known(cid: str) -> bool:
    return cid in catalog()["by_id"]


def coverage(project: dict) -> dict:
    """Which IM8 controls the project's confirmed mappings cover, and the gaps, by domain and profile level."""
    data = catalog()
    mapped: dict[str, list[str]] = {}
    for c in project.get("controls", []):
        for cid in c.get("im8") or []:
            if cid in data["by_id"]:
                mapped.setdefault(cid, []).append(c["id"])
    domains = []
    for did, title in data["domains"].items():
        rows = [{**brief(c["id"]), "controls": mapped.get(c["id"], [])} for c in data["controls"] if c["domain"] == did]
        domains.append({"id": did, "title": title, "controls": rows,
                        "covered": sum(1 for r in rows if r["controls"])})
    levels = {}
    for risk in RISKS:
        for level in LEVEL_LABELS:
            ids = [c["id"] for c in data["controls"] if c["levels"].get(risk) == level]
            levels[f"{risk}-{level}"] = {"total": len(ids), "covered": sum(1 for i in ids if i in mapped),
                                         "gaps": [i for i in ids if i not in mapped]}
    return {"title": data["title"], "version": data["version"], "total": len(data["controls"]),
            "covered": len(mapped), "domains": domains, "levels": levels}
