"""Draft IM8-style control statements from a legacy requirement clause, using rules only.

    "The IT Department shall back up all servers nightly using Veritas Backup Exec,
     and backup tapes shall be stored off-site."
        -> Back up all servers nightly.            guidance: e.g. Veritas Backup Exec
        -> Store backup tapes off-site.            who: The IT Department

The rules split bundled requirements, put the action first, turn passive voice
active, move an organisation's own role out of the statement (it is the "who"
of the implementation), turn people the requirement applies to into scope
("Require users to…", "Prohibit users from…"), replace vague timing with a
parameter ("regularly" -> "at least every [N] days"), keep legacy values as
parameter values ("[90] days"), move named tools to guidance, and drop hedges.
Each draft carries notes saying what was changed and what a person should
decide. The draft is a starting point to edit, not a finished control.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .control import VERBS as _CONTROL_VERBS


@dataclass
class Draft:
    text: str
    guidance: str = ""  # tool or "how" wording moved out of the statement
    who: str = ""  # the role the legacy clause named: the "who" for the implementation statement
    notes: list[str] = field(default_factory=list)


# --- Words ---------------------------------------------------------------------------------------

VERBS = _CONTROL_VERBS | set("""
    accept access acknowledge activate add adhere agree assign attend avoid back be carry change click comply
    complete connect contain copy cover deploy destroy disclose download enrol enroll erase follow forward give
    grant handle hold install keep leave limit lock log maintain obtain open pass permit print process provide
    read receive record reduce register remain renew report request reset return reuse rotate save send share
    sign store submit supervise take tamper transfer transmit update upload use verify view wear wipe write
""".split())
_IRREGULAR = {"kept": "keep", "sent": "send", "taken": "take", "written": "write", "held": "hold", "given": "give",
              "made": "make", "done": "do", "run": "run", "set": "set", "put": "put", "built": "build",
              "shut": "shut", "split": "split", "spent": "spend", "read": "read", "worn": "wear", "met": "meet",
              "bought": "buy", "known": "know", "shown": "show", "chosen": "choose", "withdrawn": "withdraw"}
_E_STEMS = ("ur", "at", "iz", "is", "ov", "iv", "ag", "ud", "ib", "ok", "id", "ac", "uc", "ar", "ys", "yz", "ad")
_DOUBLE = {"log", "stop", "plan", "ship", "scan", "tag", "drop", "set", "put", "run", "get", "shut", "swap", "map",
           "chat", "hit", "admit", "commit", "permit", "submit", "transfer", "control", "patrol", "refer", "prefer"}


def base_form(participle: str) -> str:
    """'granted' -> 'grant', 'changed' -> 'change', 'applied' -> 'apply', 'kept' -> 'keep'."""
    w = participle.lower()
    if w in _IRREGULAR:
        return _IRREGULAR[w]
    if w.endswith("ied"):
        return w[:-3] + "y"
    if not w.endswith("ed"):
        return w
    for candidate in (w[:-2], w[:-1]):
        if candidate in VERBS:
            return candidate
    if len(w) > 5 and w[-3] == w[-4] and w[-3] not in "lsz":
        return w[:-3]  # logged -> log
    return w[:-1] if w[:-2].endswith(_E_STEMS) else w[:-2]


def gerund(verb: str) -> str:
    """'share' -> 'sharing', 'log' -> 'logging', 'back up' -> 'backing up'."""
    if " " in verb:
        first, rest = verb.split(" ", 1)
        return f"{gerund(first)} {rest}"
    v = verb.lower()
    if v in _DOUBLE:
        return v + v[-1] + "ing"
    if v.endswith("ie"):
        return v[:-2] + "ying"
    if v.endswith("e") and not v.endswith(("ee", "ye", "oe")) and v != "be":
        return v[:-1] + "ing"
    return v + "ing"


def _is_participle(word: str) -> bool:
    w = word.lower()
    return w in _IRREGULAR or (w.endswith("ed") and len(w) >= 4 and not w.endswith("eed"))


def _is_verb(word: str) -> bool:
    w = word.lower().strip(",;:")
    return w in VERBS or w in ("be", "not", "only", "also") or _is_participle(w)


# --- Who the clause talks about ------------------------------------------------------------------

# People the requirement applies to: they stay in the statement as its scope.
_POPULATION = re.compile(
    r"^(all |any |each |every )?(users?|staff|employees?|personnel|contractors?|interns?|consultants?|"
    r"third[- ]part(y|ies)|vendors?|suppliers?|service providers?|visitors?|guests?|everyone|individuals?|"
    r"members of staff|account holders?)\b",
    re.I,
)
# The organisation's own roles: they are the "who" of the implementation, not part of the requirement.
_ORG_ROLE = re.compile(
    r"\b(department|team|unit|division|officer|cio|ciso|cto|dpo|management|managers?|director|head of|"
    r"administrators?|admins?|owners?|custodians?|helpdesk|help desk|service desk|hr|human resources|"
    r"committee|board|agency|organi[sz]ation|company|we)\b",
    re.I,
)
_RELATIVE = re.compile(r"\b(who|that|which|whose|where)\b", re.I)
_PRONOUN = re.compile(r"\b(them|it|they|these|those)\b", re.I)

_MODAL = re.compile(
    r"^(?P<subj>.*?)\s+(?P<modal>shall|must|should|will|is required to|are required to|needs? to|is to|are to)"
    r"\s+(?P<neg>not\s+|never\s+)?(?P<pred>.+)$",
    re.I,
)
_PRESENT = re.compile(r"^(?P<subj>.*?)\s+(is|are)\s+(?P<pred>(\w+ly\s+)?\w+(ed|en)\b.*)$", re.I)
_PHRASAL = {"back", "carry", "log", "sign", "shut", "lock", "set", "wipe", "clean", "write", "lay", "check", "switch",
            "turn", "roll", "patch", "close", "lock"}
_APPROVAL = {"approve", "authorise", "authorize", "sign", "endorse", "accept", "sign off"}

# --- Tools ---------------------------------------------------------------------------------------

# Product names, and the generic thing each one is, for the statement.
_PRODUCTS = [
    (r"symantec( endpoint protection)?|mcafee( endpoint security)?|trend micro( apex one)?|sophos( endpoint)?|"
     r"kaspersky|windows defender|microsoft defender( antivirus)?", "anti-malware software"),
    (r"crowdstrike( falcon)?|sentinelone|carbon black", "endpoint detection and response software"),
    (r"veritas( backup exec| netbackup)?|backup exec|veeam( backup)?|commvault|acronis", "backup software"),
    (r"okta|active directory|azure ad|entra id|ping ?identity", "the identity provider"),
    (r"splunk|qradar|arcsight|microsoft sentinel|elastic siem", "the log management system"),
    (r"servicenow|jira( service management)?|remedy", "the ticketing system"),
    (r"nessus|tenable|qualys|rapid7", "a vulnerability scanner"),
    (r"bitlocker|filevault|veracrypt", "full-disk encryption"),
    (r"cisco anyconnect|globalprotect|fortinet( vpn)?|forticlient", "the VPN"),
    (r"lastpass|1password|bitwarden|cyberark", "a password vault"),
    (r"intune|jamf|airwatch|workspace one", "mobile device management"),
]
_PRODUCT_RES = [(re.compile(r"\b(" + p + r")\b", re.I), generic) for p, generic in _PRODUCTS]
_USING = re.compile(r"\s*,?\s*\b(using|with|via|through|in|on)\s+(the\s+)?(?P<tool>[^,.;]+)$", re.I)

# --- Timing --------------------------------------------------------------------------------------

_RECURRING = re.compile(r"^(review|test|check|scan|back up|backup|audit|assess|reconcile|recertify|rotate|"
                        r"update|monitor|inspect|verify|train|change)\b", re.I)
_VAGUE_TIMING = [
    (re.compile(r"\b(on a regular basis|regularly|periodically|from time to time|routinely)\b", re.I),
     "at least every [N] days", None),
    (re.compile(r"\b(in a timely manner|in a timely fashion|promptly|as soon as possible|as soon as practicable|"
                r"without undue delay|timely)\b", re.I), "within [N] days", None),
    (re.compile(r"\bfor an? (appropriate|suitable|reasonable|adequate|sufficient) (period|duration|time)"
                r"( of time)?\b", re.I), "for at least [N] days", None),
    (re.compile(r"\b(as needed|as required|when necessary|if necessary|as necessary)\b", re.I),
     "at least every [N] days", "recurring"),
    (re.compile(r"\bas appropriate\b", re.I), "within [N] days", "event"),
]
_EVENT = re.compile(r"^(remove|disable|revoke|delete|apply|patch|report|notify|investigate|respond|contain|"
                    r"deactivate|terminate|update|reset|close)\b", re.I)
_HEDGES = re.compile(r"\s*,?\s*\b(where (possible|practical|practicable|feasible|appropriate)|if possible|"
                     r"if practical|as far as (possible|practicable)|wherever possible)\b,?", re.I)
_OPEN_LIST = re.compile(r"\b(such as|for example|e\.g\.|including but not limited to|etc\.?)", re.I)
_VALUE = re.compile(r"\b(\d+(?:\.\d+)?)\s+(?=(business days?|working days?|calendar days?|days?|hours?|minutes?|"
                    r"weeks?|months?|years?|characters?|(consecutive |failed |unsuccessful )*(login |logon )?"
                    r"attempts?|passwords?|times|versions?|generations?)\b)", re.I)
_EVERY_N = re.compile(r"(?<!at least )\bevery (?=\[)", re.I)


# --- Splitting ----------------------------------------------------------------------------------

def _clauses(sentence: str) -> list[str]:
    """Independent clauses, each with its own subject and modal: '…, and backup tapes shall be stored…'."""
    parts = re.split(r"\s*(?:;\s*(?:and\s+)?|,?\s+and\s+(?=(?:(?!\b(?:shall|must|should|will)\b)[^,;]){0,60}?"
                     r"\b(?:shall|must|should|will)\b))", sentence)
    return [p.strip(" ,;") for p in parts if p and p.strip(" ,;")]


_SEPARATOR = re.compile(r"\s*,\s*(?:and|or)\s+|\s*,\s+|\s+(?:and|or)\s+", re.I)


def _predicates(pred: str) -> list[list[tuple[str, str]]]:
    """Split a predicate into separate requirements; each is a list of (separator, piece) chained by and/or.

    'not share their passwords, write them down, or reuse their last 5 passwords'
        -> [[('', 'share their passwords'), (', ', 'write them down')], [('', 'reuse their last 5 passwords')]]
    A piece joins the one before it when it is a single word ('disable or tamper with'), refers back with a
    pronoun ('write them down'), or the one before it opens a relative clause ('staff who leave, transfer…').
    """
    pieces: list[tuple[str, str]] = []
    pos = 0
    for m in _SEPARATOR.finditer(pred):
        after = pred[m.end():].split(" ", 1)[0]
        if not _is_verb(after):
            continue
        pieces.append((pred[pos:m.start()], m.group(0)))
        pos = m.end()
    pieces.append((pred[pos:], ""))

    groups: list[list[tuple[str, str]]] = []
    sep_before = ""
    for text, sep in pieces:
        joins = groups and (
            len(groups[-1][-1][1].split()) < 2 or _PRONOUN.search(text) or _RELATIVE.search(groups[-1][-1][1]))
        if joins:
            groups[-1].append((sep_before, text))
        else:
            groups.append([("", text)])
        sep_before = sep
    return groups


def _join(group: list[tuple[str, str]], verb_form=lambda v: v, last: str = "and") -> str:
    """Join chained pieces, putting each piece's verb in `verb_form`; a list ends '…, and x' (or '…, or x')."""
    out = ""
    for i, (sep, text) in enumerate(group):
        first, _, rest = text.strip().partition(" ")
        if i and i == len(group) - 1 and sep.strip() == "," and not re.search(r"\b(and|or)\b", text):
            sep = f", {last} " if len(group) > 2 else f" {last} "
        out += (sep if out else "") + verb_form(first) + (" " + rest if rest else "")
    return out


# --- Building one statement -----------------------------------------------------------------------

def _lower_first(phrase: str) -> str:
    """'User accounts' -> 'user accounts'; acronyms and names ('IT staff', 'Symantec Endpoint') keep capitals."""
    words = phrase.split(" ")
    first = words[0]
    acronym = len(first) > 1 and first.isupper()
    name = len(words) > 1 and words[1][:1].isupper()
    if acronym or name:
        return phrase
    return first[:1].lower() + phrase[1:]


def _strip_article(phrase: str) -> str:
    return re.sub(r"^(all |any |each |every )", "", phrase, flags=re.I)


def _statement(subject: str, negative: bool, group: list[tuple[str, str]], passive_group: bool,
               draft: Draft) -> str:
    subject = subject.strip()
    population = _POPULATION.match(subject)
    org = not population and _ORG_ROLE.search(subject) and not passive_group
    head = group[0][1].strip()

    if passive_group:
        # "be granted on a need-to-know basis" / "only be used for…" / "be at least 8 characters long"
        words = head.split()
        only = words[0].lower() == "only"
        if only:
            words = words[1:]
        if words and words[0].lower() == "be":
            words = words[1:]
        if words and words[0].lower() == "only":
            only, words = True, words[1:]
        obj = _lower_first(subject)
        if not words or not _is_participle(words[0]):
            return f"Require {obj} to be {' '.join(words)}".strip()
        verb = base_form(words[0])
        rest_words = words[1:]
        # phrasal verbs keep their particle: "backed up daily" -> "Back up … daily"
        if rest_words and rest_words[0].lower() in ("up", "out", "off", "down", "in") and verb in _PHRASAL:
            verb, rest_words = f"{verb} {rest_words[0].lower()}", rest_words[1:]
        rest = " ".join(rest_words)
        tail = _join(group[1:]) if len(group) > 1 else ""
        rest = (rest + (", " + tail if tail else "")).strip()
        agent = re.search(r"\s*\bby (?P<agent>(the |a |an )?[^,;]+?)(?=$|,|;|\s+(before|after|within|when|at)\b)",
                          rest)
        if agent and _ORG_ROLE.search(agent.group("agent")):
            rest = (rest[:agent.start()] + rest[agent.end():]).strip()
            if verb in _APPROVAL:
                return f"Require {agent.group('agent').strip()} to {verb} {obj} {rest}".strip()
            draft.who = draft.who or agent.group("agent").strip()
        if negative:
            return f"Prohibit {gerund(verb)} {obj} {rest}".strip()
        if verb in ("avoid", "discourage"):
            draft.notes.append(f"Turned '{verb}' into 'prohibit': confirm, or name the allowed exceptions.")
            return f"Prohibit {obj} {rest}".strip()
        if only:
            return f"{verb.capitalize()} {obj} only {rest}".strip()
        return f"{verb.capitalize()} {obj} {rest}".strip()

    if population:
        who = _lower_first(subject)
        if negative:
            return f"Prohibit {who} from {_join(group, gerund, last='or')}"
        return f"Require {who} to {_join(group)}"
    if org:
        draft.who = draft.who or subject
        text = _join(group)
        return ("Do not " + text) if negative else text[:1].upper() + text[1:]
    # A thing as the subject: "Passwords shall contain a mix of letters and numbers."
    obj = _lower_first(subject)
    if negative:
        return f"Prohibit {obj} from {_join(group, gerund, last='or')}"
    return f"Require {obj} to {_join(group)}"


def _tools(text: str, draft: Draft) -> str:
    found = []
    for pattern, generic in _PRODUCT_RES:
        for m in pattern.finditer(text):
            found.append((m, generic))
    if not found:
        return text
    names = []
    for m, generic in sorted(found, key=lambda f: -f[0].start()):
        name = m.group(0)
        # "… using Veritas Backup Exec": drop the phrase; otherwise put the generic thing in its place
        using = re.search(r"\s*,?\s*\b(using|with|via|through)\s+(the\s+)?" + re.escape(name) + r"\b", text, re.I)
        if using:
            text = text[:using.start()] + text[using.end():]
        else:
            text = text[:m.start()] + generic + text[m.end():]
        names.append(name)
    draft.guidance = "e.g. " + ", ".join(reversed(names))
    draft.notes.append(f"Moved {', '.join(reversed(names))} to guidance: the statement says what, not which tool.")
    return text


def _timing(text: str, draft: Draft) -> str:
    action = text.split(" ", 1)[0]
    for pattern, replacement, kind in _VAGUE_TIMING:
        m = pattern.search(text)
        if not m:
            continue
        if kind == "recurring" and not _RECURRING.match(text) and not _RECURRING.match(_after_require(text)):
            continue
        if kind == "event" and not (_EVENT.match(text) or _EVENT.match(_after_require(text))):
            text = (text[:m.start()] + text[m.end():]).strip()
            draft.notes.append(f"Removed '{m.group(0)}': say exactly what is required instead.")
            continue
        text = text[:m.start()] + replacement + text[m.end():]
        draft.notes.append(f"Replaced '{m.group(0)}' with '{replacement}': set the value.")
    if _EVENT.match(action) and not re.search(r"\bwithin\b|\bimmediately\b|\bbefore\b", text, re.I):
        draft.notes.append("Consider a time limit (within [N] days).")
    return text


def _after_require(text: str) -> str:
    m = re.match(r"^(require|prohibit) .*? (to|from) (?P<rest>.*)$", text, re.I)
    return m.group("rest") if m else ""


def _values(text: str, draft: Draft) -> str:
    new = _VALUE.sub(r"[\1] ", text)
    new = re.sub(r"\] {2,}", "] ", new)
    new = _EVERY_N.sub("at least every ", new)
    if new != text:
        draft.notes.append("Kept the legacy values as parameters in [brackets]: confirm or change them.")
    return new


def _tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" ,;.")
    text = re.sub(r"\s+,", ",", text)
    return (text[:1].upper() + text[1:] + ".") if text else ""


# --- Public --------------------------------------------------------------------------------------

def draft(clause_text: str) -> list[Draft]:
    """Control statements drafted from one legacy requirement clause."""
    out: list[Draft] = []
    for sentence in re.split(r"(?<=[.;])\s+(?=[A-Z])", clause_text.strip()):
        sentence = sentence.strip().rstrip(".;:")
        last_subject = ""
        for clause in _clauses(sentence):
            if re.match(r"(shall|must|should|will)\b", clause, re.I) and last_subject:
                clause = f"{last_subject} {clause}"  # "… and shall not be used for email"
            m = _MODAL.match(clause)
            passive_present = False
            if not m:
                p = _PRESENT.match(clause)
                if not p:
                    out.append(Draft(_tidy(clause), notes=["No requirement wording found: rewrite it as an action."]))
                    continue
                subject, negative, modal, pred = p.group("subj"), False, "", "be " + p.group("pred")
                passive_present = True
            else:
                subject, negative = m.group("subj"), bool(m.group("neg"))
                modal, pred = m.group("modal").lower(), m.group("pred")
            last_subject = subject
            hedges = [h.group(0).strip(" ,") for h in _HEDGES.finditer(pred)]
            pred = _HEDGES.sub("", pred)
            groups = _predicates(pred)
            passive = False
            for group in groups:
                lead = group[0][1].strip().split(" ", 1)[0].lower()
                # a participle after a passive piece stays passive: "be granted … and approved by …"
                passive = lead in ("be", "only") or (passive and _is_participle(lead)) or passive_present
                d = Draft("")
                text = _statement(subject, negative, group, passive, d)
                text = _tools(text, d)
                text = _timing(text, d)
                text = _values(text, d)
                if modal == "should" or hedges:
                    said = "', '".join(([modal] if modal == "should" else []) + hedges)
                    d.notes.insert(0, f"The legacy clause says '{said}', which makes it optional: confirm it is "
                                      "required.")
                if soft := re.match(r"(discourage|encourage|consider|endeavour|endeavor|strive|aim)\b", d.text or text,
                                    re.I):
                    d.notes.append(f"'{soft.group(1).capitalize()}' is not a requirement: restrict, prohibit or "
                                   "require something instead.")
                if vague := re.search(r"\b(appropriate|necessary|suitable|adequate|reasonable) "
                                      r"(action|actions|measures|steps|controls|safeguards)\b", text, re.I):
                    d.notes.append(f"'{vague.group(0)}' is not testable: say what has to be done.")
                if _OPEN_LIST.search(text):
                    d.notes.append("Open-ended list: name the full set, or say where it is defined.")
                if d.who:
                    d.notes.append(f"'{d.who}' is who does it: that belongs in the implementation statement.")
                d.text = _tidy(text)
                out.append(d)
    return out
