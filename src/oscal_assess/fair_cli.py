"""oscal-fair: enter FAIR risks interactively, or compute exposure for a risk register."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import report
from .fair import DEFAULT_SIMULATIONS, Estimate, FairError, FairModel
from .risk import FACTORS, RiskRegister, parse_controls, quantify

MODES = {
    "1": ("Annualized loss exposure (ALE) directly", [("ale", "Annualized loss exposure")]),
    "2": ("Loss event frequency x loss magnitude", [
        ("lef", "Loss events per year"),
        ("lm", "Loss per event"),
    ]),
    "3": ("Full FAIR factors", None),
}


class Prompter:
    def __init__(self, ask=input, say=print):
        self.ask = ask
        self.say = say

    def text(self, label: str, default: str = "", required: bool = False) -> str:
        suffix = f" [{default}]" if default else ""
        while True:
            value = self.ask(f"{label}{suffix}: ").strip() or default
            if value or not required:
                return value
            self.say("  A value is required.")

    def yes(self, label: str, default: bool = False) -> bool:
        value = self.ask(f"{label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
        return default if not value else value.startswith("y")

    def choice(self, label: str, options: dict[str, str], default: str) -> str:
        for key, desc in options.items():
            self.say(f"  {key}) {desc}")
        while True:
            value = self.ask(f"{label} [{default}]: ").strip() or default
            if value in options:
                return value
            self.say(f"  Choose one of {', '.join(options)}.")

    def estimate(self, label: str, hint: str = "", optional: bool = False):
        prompt = f"{label}{f' ({hint})' if hint else ''}: min, most likely, max or one number"
        if optional:
            prompt += " (blank to skip)"
        while True:
            raw = self.ask(prompt + ": ").strip()
            if not raw and optional:
                return None
            try:
                parts = [float(p.replace("_", "").replace(",", "")) for p in raw.replace(";", " ").split()]
            except ValueError:
                parts = []
            if len(parts) == 1:
                return parts[0]
            if len(parts) == 3:
                value = {"min": parts[0], "most_likely": parts[1], "max": parts[2]}
                try:
                    Estimate.parse(value, label)
                    return value
                except FairError as exc:
                    self.say(f"  {exc}")
                    continue
            self.say("  Enter one number, or three separated by spaces: min most-likely max.")


def ask_fair(p: Prompter, heading: str) -> dict:
    p.say(f"\n{heading}")
    mode = p.choice("How do you want to estimate it", {k: v[0] for k, v in MODES.items()}, "3")
    data: dict = {}
    if MODES[mode][1] is not None:
        for key, label in MODES[mode][1]:
            data[key] = p.estimate(label)
    else:
        p.say("Threat event frequency")
        tef = p.estimate("Threat events per year", "leave blank to derive from contact x action", optional=True)
        if tef is not None:
            data["tef"] = tef
        else:
            data["contact_frequency"] = p.estimate("Contacts with the asset per year")
            data["probability_of_action"] = p.estimate("Probability of action once in contact", "0-1")
        p.say("Vulnerability")
        vuln = p.estimate("Vulnerability", "0-1; blank to derive from capability vs resistance", optional=True)
        if vuln is not None:
            data["vulnerability"] = vuln
        else:
            data["threat_capability"] = p.estimate("Threat capability", "0-100 percentile")
            data["resistance_strength"] = p.estimate("Resistance strength", "0-100 percentile")
        p.say("Loss magnitude")
        data["primary_loss"] = p.estimate("Primary loss per event")
        secondary = p.estimate("Secondary loss per event", "fines, reputation, litigation", optional=True)
        if secondary is not None:
            data["secondary_loss"] = secondary
            data["secondary_lef"] = p.estimate("Share of events with secondary loss", "0-1")
    FairModel.parse(data, heading)
    return data


def ask_risk(p: Prompter, index: int) -> dict:
    p.say("\nDescribe the loss scenario")
    risk = {
        "id": p.text("Risk id", f"R-{index:03d}"),
        "title": p.text("Title", required=True),
        "asset": p.text("Asset at risk"),
        "threat_community": p.text("Threat community (who)"),
        "threat_event": p.text("Threat event (what they do)"),
        "effect": p.text("Effect (confidentiality, integrity, availability)"),
        "description": p.text("Description"),
    }
    risk = {k: v for k, v in risk.items() if v}
    p.say("\nControls that treat it, e.g. ia-2=vulnerability, au-6=loss_magnitude")
    p.say("  Factors: " + "; ".join(f"{k} = {v}" for k, v in FACTORS.items()))
    raw = p.text("Controls (comma separated, '=factor' optional)")
    controls = {}
    for item in filter(None, (c.strip() for c in raw.split(","))):
        cid, _, factor = item.partition("=")
        controls[cid.strip().lower()] = factor.strip() or None
    risk["controls"] = {c: f for c, f in parse_controls(controls).items()}
    appetite = p.text("Risk appetite for this risk (ALE, blank to use the register's)")
    if appetite:
        risk["appetite"] = float(appetite.replace(",", ""))
    risk["inherent"] = ask_fair(p, "Inherent risk (before these controls)")
    if p.yes("\nEstimate residual risk (with the controls operating)?", True):
        risk["residual"] = ask_fair(p, "Residual risk (with the controls operating)")
    return risk


def cmd_new(args, p: Prompter) -> int:
    path = Path(args.register)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        RiskRegister.parse(data)
    else:
        p.say(f"Creating {path}")
        data = {"currency": p.text("Currency", "USD"), "risks": []}
        appetite = p.text("Risk appetite: the most annualized loss you will accept per risk (blank for none)")
        if appetite:
            data["appetite"] = float(appetite.replace(",", ""))
    while True:
        risk = ask_risk(p, len(data["risks"]) + 1)
        data["risks"].append(risk)
        register = RiskRegister.parse(data)
        added = register.risks[-1]
        inherent, residual = quantify(added, args.simulations, args.seed)
        p.say(f"\n{added.id} inherent  {report.fair_line(inherent, register.currency)}")
        if residual:
            p.say(f"{added.id} residual  {report.fair_line(residual, register.currency)}")
        if not p.yes("\nAdd another risk?"):
            break
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    p.say(f"\nSaved {len(data['risks'])} risk(s) to {path}")
    return 0


def cmd_compute(args, p: Prompter) -> int:
    register = RiskRegister.load(args.register)
    rows = []
    for risk in register.risks:
        inherent, residual = quantify(risk, args.simulations, args.seed)
        appetite = risk.appetite if risk.appetite is not None else register.appetite
        exposure = residual or inherent
        value = exposure.ale_p90 if register.appetite_metric == "p90" else exposure.ale_mean
        rows.append({
            "id": risk.id,
            "title": risk.title,
            "inherent": inherent.to_dict(),
            "residual": residual.to_dict() if residual else None,
            "reduction": round(inherent.ale_mean - residual.ale_mean, 2) if residual else None,
            "appetite": appetite,
            "within_appetite": None if appetite is None else value <= appetite,
            "_results": (inherent, residual),
        })
    if args.format == "json":
        p.say(json.dumps({"currency": register.currency, "appetite_metric": register.appetite_metric,
                          "risks": [{k: v for k, v in r.items() if k != "_results"} for r in rows]}, indent=2))
        return 0
    cur = register.currency
    for r in rows:
        inherent, residual = r["_results"]
        p.say(f"{r['id']}  {r['title']}")
        p.say(f"  inherent  {report.fair_line(inherent, cur)}")
        for note in inherent.derived:
            p.say(f"            {note}")
        if residual:
            p.say(f"  residual  {report.fair_line(residual, cur)}  "
                  f"(reduced by {report.money(r['reduction'], cur)})")
        if r["appetite"] is not None:
            state = "within" if r["within_appetite"] else "EXCEEDS"
            p.say(f"  {state} appetite of {report.money(r['appetite'], cur)} ({register.appetite_metric})")
        p.say("")
    total = sum((r["_results"][1] or r["_results"][0]).ale_mean for r in rows)
    p.say(f"Total exposure (mean, residual where estimated): {report.money(total, cur)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="oscal-fair", description="Enter and quantify FAIR risks.")
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="add risks to a register by answering questions")
    new.add_argument("register", help="risk register JSON (created if missing)")
    compute = sub.add_parser("compute", help="compute inherent and residual exposure for a register")
    compute.add_argument("register", help="risk register JSON")
    compute.add_argument("-f", "--format", choices=["table", "json"], default="table")
    for p in (new, compute):
        p.add_argument("--simulations", type=int, default=DEFAULT_SIMULATIONS)
        p.add_argument("--seed", type=int, default=0)
    return parser


def main(argv: list[str] | None = None, prompter: Prompter | None = None) -> int:
    args = build_parser().parse_args(argv)
    p = prompter or Prompter()
    try:
        return {"new": cmd_new, "compute": cmd_compute}[args.command](args, p)
    except (OSError, ValueError, KeyError) as exc:
        print(f"oscal-fair: {exc}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("\noscal-fair: cancelled, nothing saved", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
