#!/usr/bin/env bash
# Unattended tight loop for one pytest node or file.
# Copy-adapt the TARGET, then run this script as the Phase 1 command.
#
# Usage:
#   bash .cursor/skills/diagnosing-bugs/scripts/pytest-loop.sh \
#     tests/test_acme.py::test_every_clause_is_sorted_as_the_key_says
#   CODIFY_SITE=site bash .cursor/skills/diagnosing-bugs/scripts/pytest-loop.sh \
#     tests/e2e/test_web.py
#
# Exit 0 is green; non-zero is red. Output is the loop artifact — redact
# secrets before quoting it.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <pytest-target> [pytest-args...]" >&2
  exit 2
fi

echo "+ pytest -q $*"
pytest -q "$@"
echo "GREEN $*"
