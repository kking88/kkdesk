#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "usage: customize.sh KEY=VALUE [KEY=VALUE ...]"
  exit 1
fi

pairs=()
for arg in "$@"; do
  if [[ "$arg" != *=* ]]; then
    echo "invalid pair: $arg"
    exit 1
  fi
  pairs+=("$arg")
done

while IFS= read -r -d '' file_path; do
  if file --mime "$file_path" | grep -q 'charset=binary'; then
    continue
  fi

  for pair in "${pairs[@]}"; do
    key="${pair%%=*}"
    value="${pair#*=}"
    KEY="$key" VALUE="$value" LC_ALL=C perl -i.bak -pe 's/\Q$ENV{KEY}\E/$ENV{VALUE}/g' "$file_path"
  done
done < <(git ls-files -z)

find . -name "*.bak" -delete
