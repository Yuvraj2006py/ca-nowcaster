#!/usr/bin/env bash
# Fail if tracked files look like secrets / credential material.
# Complements TruffleHog --only-verified (does not replace it).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

mapfile -t tracked < <(git ls-files)

offenders=()
for path in "${tracked[@]}"; do
  # Allow the documented example env file only.
  if [[ "$path" == ".env.example" ]]; then
    continue
  fi

  base="$(basename "$path")"
  suspicious=0

  if [[ "$base" == ".env" || "$base" == .env.* ]]; then
    suspicious=1
  fi
  if [[ "$base" == *.pem || "$base" == *.key || "$base" == *.p12 || "$base" == *.pfx ]]; then
    suspicious=1
  fi
  if [[ "$base" == id_rsa || "$base" == id_rsa.* || "$base" == id_ed25519 || "$base" == id_ed25519.* ]]; then
    suspicious=1
  fi
  if [[ "$path" == ".streamlit/secrets.toml" ]]; then
    suspicious=1
  fi
  if [[ "$base" == "credentials.json" || "$base" == "service-account.json" || "$base" == "serviceAccount.json" ]]; then
    suspicious=1
  fi
  if [[ "$base" == *service-account*.json ]]; then
    suspicious=1
  fi

  if [[ "$suspicious" -eq 1 ]]; then
    offenders+=("$path")
  fi
done

if ((${#offenders[@]})); then
  echo "secret_path_hygiene: REFUSED — secret-ish paths are tracked:" >&2
  printf '  %s\n' "${offenders[@]}" >&2
  echo "Remove them from git, rotate if real, keep .gitignore strict." >&2
  exit 1
fi

echo "secret_path_hygiene: ok (${#tracked[@]} tracked files checked)."
