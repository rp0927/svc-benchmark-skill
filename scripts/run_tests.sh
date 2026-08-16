#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
for t in "$ROOT"/scripts/test_*.py; do
  case "$(basename "$t")" in
    test_skill_step12_gates.py)
      echo "skip $t (42workspace dual-tree)"
      continue
      ;;
  esac
  if python3 "$t"; then
    echo "OK $(basename "$t")"
  else
    echo "FAIL $(basename "$t")"
    fail=1
  fi
done
exit "$fail"
