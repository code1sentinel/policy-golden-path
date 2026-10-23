"""Write every Rego starter template and run `opa check` (CI)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from codify.policy_as_code import EXAMPLE_STATEMENTS, generate_policy


def main() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        paths = []
        for pattern, statement in EXAMPLE_STATEMENTS.items():
            out = generate_policy(statement, "rego", control_id=pattern)
            path = root / f"{pattern}.rego"
            path.write_text(out["code"], encoding="utf-8")
            paths.append(path)
        proc = subprocess.run(["opa", "check", *[str(p) for p in paths]], capture_output=True, text=True)
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
