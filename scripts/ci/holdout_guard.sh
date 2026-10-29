#!/usr/bin/env bash
# Fail CI when holdout paths change on a non–Evaluation-Skeptic branch.
# Allowed head refs (case-insensitive substring match via regex):
#   evaluation | skeptic | holdout
# Bootstrap / CI ownership of the guard itself:
#   phase-0-setup | devops
set -euo pipefail

HEAD_REF="${HEAD_REF:-${GITHUB_HEAD_REF:-}}"
if [[ -z "${HEAD_REF}" ]]; then
  HEAD_REF="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
fi

if [[ -z "${HEAD_REF}" ]]; then
  echo "holdout-guard: unable to determine branch name" >&2
  exit 1
fi

# Normalize for matching (lowercase).
ref_lc="$(printf '%s' "${HEAD_REF}" | tr '[:upper:]' '[:lower:]')"

ALLOWED_REGEX='(evaluation|skeptic|holdout|phase-0-setup|devops)'

if [[ "${ref_lc}" =~ ${ALLOWED_REGEX} ]]; then
  echo "holdout-guard: branch '${HEAD_REF}' is allowed to touch holdout paths."
  exit 0
fi

cat >&2 <<EOF
holdout-guard: REFUSED

Branch '${HEAD_REF}' modified locked holdout paths.
Only Evaluation Skeptic branches (name containing evaluation, skeptic, or holdout)
may change:
  - docs/holdout_log.md
  - src/nowcaster/evaluation/holdout/**
  - tests/**/holdout*
  - **/holdout_eval*

Open a docs/requests/ note for the Evaluation Skeptic instead of editing these files.
Do not loosen this check.
EOF
exit 1
