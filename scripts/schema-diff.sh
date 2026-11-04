#!/usr/bin/env bash
# Compares the Alembic-migrated schema with docs/architecture/schema.sql.
# Both are loaded into scratch databases and dumped with pg_dump, so the diff is
# structural (tables, columns, constraints, indexes, trigger, comments), not textual.
set -euo pipefail
cd "$(dirname "$0")/.."

DB_PORT="${DB_PORT:-55433}"
PSQL=(docker compose exec -T db psql -U intake -v ON_ERROR_STOP=1 -q)
DUMP=(docker compose exec -T db pg_dump -U intake --schema-only --no-owner --no-privileges
  -T alembic_version)
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"; "${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS schema_ref" -c "DROP DATABASE IF EXISTS schema_mig" >/dev/null 2>&1 || true' EXIT

docker compose up -d --wait db >/dev/null
for d in schema_ref schema_mig; do
  "${PSQL[@]}" -d postgres -c "DROP DATABASE IF EXISTS $d" -c "CREATE DATABASE $d"
done

"${PSQL[@]}" -d schema_ref <docs/architecture/schema.sql
(cd services/api && DATABASE_URL="postgresql://intake:intake@localhost:${DB_PORT}/schema_mig" \
  uv run alembic upgrade head)

# Drop pg_dump noise: comments, blank lines, SET/set_config and \restrict tokens.
norm() { grep -vE '^(--|SET |SELECT pg_catalog\.set_config|\\(un)?restrict)|^$' || true; }
"${DUMP[@]}" -d schema_ref | norm >"$TMP/ref.sql"
"${DUMP[@]}" -d schema_mig | norm >"$TMP/mig.sql"

if diff -u "$TMP/ref.sql" "$TMP/mig.sql"; then
  echo "schema-diff: migrated DB matches docs/architecture/schema.sql"
else
  echo "schema-diff: DIFFERENCES FOUND (- schema.sql, + migrated)" >&2
  exit 1
fi
