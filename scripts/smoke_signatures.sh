#!/usr/bin/env bash
set -euo pipefail
# Signature smoke tests for POST /objects in strict mode
# Usage: ./scripts/smoke_signatures.sh [HOST]
# Env:
#   KEYID     (default: sig1)      -> server key id
#   SEED_B64U (required for signed) -> client private seed (base64url)
#   NS        (default: ns)

HOST="${1:-http://127.0.0.1:8000}"
KEYID="${KEYID:-sig1}"
SEED_B64U="${SEED_B64U:-}"
NS="${NS:-ns}"
JSON_PAYLOAD='{"x":1}'

pass(){ echo -e "✅  $*"; }
fail(){ echo -e "❌  $*"; exit 1; }

post_unsigned() {
  local body code
  body="$(mktemp)"; trap 'rm -f "$body"' RETURN
  code="$(curl -sS -o "$body" -w "%{http_code}" \
    -H 'content-type: application/json' \
    -d "{\"namespace\":\"$NS\",\"content\":$JSON_PAYLOAD}" \
    -X POST "$HOST/objects")"
  python3 -m json.tool < "$body" || true
  echo "HTTP $code"
  [ "$code" = "401" ] && pass "Unsigned → 401 Missing required signature" || fail "Unsigned expected 401, got $code"
}

post_malformed() {
  local body code
  body="$(mktemp)"; trap 'rm -f "$body"' RETURN
  code="$(curl -sS -o "$body" -w "%{http_code}" \
    -H 'content-type: application/json' \
    -H 'Signature-Input: sig1=();created=1618884473;keyid=\"sig1\"' \
    -H 'Signature: sig1=abc' \
    -d "{\"namespace\":\"$NS\",\"content\":$JSON_PAYLOAD}" \
    -X POST "$HOST/objects")"
  python3 -m json.tool < "$body" || true
  echo "HTTP $code"
  [ "$code" = "400" ] && pass "Malformed → 400 Bad Request" || fail "Malformed expected 400, got $code"
}

post_bad_key() {
  [ -n "$SEED_B64U" ] || fail "SEED_B64U not set"
  local out status
  out="$(python3 scripts/sign_post_objects.py \
    --host "$HOST" \
    --seed-b64u "$SEED_B64U" \
    --keyid nope \
    --namespace "$NS" \
    --json "$JSON_PAYLOAD")"
  echo "$out"
  status="$(echo "$out" | sed -n 's/^Status: \([0-9]\{3\}\).*$/\1/p' | head -n1 || true)"
  [ "$status" = "401" ] && pass "Wrong keyid → 401 no valid signature" || fail "Wrong keyid expected 401, got ${status:-<none>}"
}

post_valid() {
  [ -n "$SEED_B64U" ] || fail "SEED_B64U not set"
  local out status
  out="$(python3 scripts/sign_post_objects.py \
    --host "$HOST" \
    --seed-b64u "$SEED_B64U" \
    --keyid "$KEYID" \
    --namespace "$NS" \
    --json "$JSON_PAYLOAD")"
  echo "$out"
  status="$(echo "$out" | sed -n 's/^Status: \([0-9]\{3\}\).*$/\1/p' | head -n1 || true)"
  [ "$status" = "201" ] && pass "Valid signed → 201 Created" || fail "Valid expected 201, got ${status:-<none>}"
}

echo "== Signature smoke tests against $HOST =="
echo "KEYID=$KEYID  NS=$NS"
echo

echo "-- 1/4 Unsigned --";  post_unsigned;  echo
echo "-- 2/4 Malformed --"; post_malformed; echo
echo "-- 3/4 Wrong keyid --"; post_bad_key; echo
echo "-- 4/4 Valid signed --"; post_valid; echo

pass "All checks passed 🎉"
