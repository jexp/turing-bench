#!/usr/bin/env bash
set -euo pipefail

URL="http://localhost:7474/db/neo4j/tx/commit"
PAYLOAD='{"statements":[{"statement":"MATCH (n) RETURN collect(id(n)) AS ids"}]}'

# Warmup (discard output)
for _ in {1..50}; do
  curl -sS -o /dev/null \
    -H 'accept:application/json' \
    -H 'content-type:application/json' \
    -d "$PAYLOAD" \
    "$URL"
done

# Timed runs (report ms)
for i in {1..5}; do
  start_ns=$(date +%s%N)
  curl -sS -o /dev/null \
    -H 'accept:application/json' \
    -H 'content-type:application/json' \
    -d "$PAYLOAD" \
    "$URL"
  end_ns=$(date +%s%N)
  elapsed_ms=$(( (end_ns - start_ns) / 1000000 ))
  printf "run %d: %d ms\n" "$i" "$elapsed_ms"
done