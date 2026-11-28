#!/usr/bin/env bash
# [REVISION 2026-11-27] Aplica las migraciones de supabase/migrations y pruebas/canon_rag.sql en un Postgres local (pgvector).
# Aplica la migración del canon en un Postgres local con pgvector, simulando lo que Supabase ya trae, y corre las
# pruebas. Uso (como root, con PostgreSQL 16+ y postgresql-<versión>-pgvector instalados):
#
#   bash pruebas/probar_migracion.sh
#
# Crea y borra la base «prueba_canon». No toca Supabase.
# [REVISION-BUG] Sin 'trap': si una migracion falla (set -e), la base prueba_canon queda creada sin borrar.
set -euo pipefail
cd "$(dirname "$0")/.."
psql_pg() { su postgres -c "psql -v ON_ERROR_STOP=1 -q $*"; }

psql_pg "-c 'drop database if exists prueba_canon' -c 'create database prueba_canon'"
psql_pg "-d prueba_canon" <<'SQL'
create schema if not exists extensions;
do $$ begin
  if not exists (select from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
end $$;
SQL
for m in supabase/migrations/*.sql; do
  echo "migración: $m"
  psql_pg "-d prueba_canon" < "$m"
done
psql_pg "-d prueba_canon" < pruebas/canon_rag.sql
psql_pg "-c 'drop database prueba_canon'"
