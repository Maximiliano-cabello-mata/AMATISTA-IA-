-- Prueba de la migración del canon (supabase/migrations/20261122000000_canon_rag.sql) en un Postgres local con pgvector.
--
--   psql -v ON_ERROR_STOP=1 -d prueba -f pruebas/canon_rag.sql
--
-- La base de prueba simula lo que Supabase ya trae (esquema extensions y roles anon, authenticated, service_role).
-- Vectores sintéticos de 1024 dimensiones: un «eje» por tema, para saber de antemano qué debe salir primero.

begin;

create function pg_temp.eje(i integer) returns extensions.vector language sql as $$
  select ('[' || array_to_string(array(select case when g = i then 1 else 0.01 end from generate_series(1, 1024) g), ',') || ']')::extensions.vector
$$;

insert into public.canon_documentos (id, repositorio, ruta, commit_fijado, tipo, titulo, idioma, sha256, version_canon) values
  ('g7b/estandar-telemetria', 'g7b', 'docs/ESTANDAR_TELEMETRIA.md', repeat('a', 40), 'estandar', 'G7B telemetry standard', 'en', repeat('1', 64), 1),
  ('g7b/ingesta', 'g7b', 'docs/INGESTA.md', repeat('a', 40), 'regla', 'Ingesta y embudo', 'es', repeat('2', 64), 1),
  ('g7b/vision', 'g7b', 'docs/VISION.md', repeat('a', 40), 'vision', 'Visión de G7B', 'es', repeat('3', 64), 1);

insert into public.canon_fragmentos (documento_id, orden, seccion, texto, sha256, modelo_embedding, embedding) values
  ('g7b/estandar-telemetria', 0, '2. Hardware records', 'The hardware block uses g7b.hardware/1 with gpus, vram_gb and nivel N0 to N4.', repeat('4', 64), 'bge-m3@prueba', pg_temp.eje(1)),
  ('g7b/ingesta', 0, '4. El embudo', 'Cinco etapas: entrada, calidad, duplicados, relevancia y valor. Lo genérico sin medidas se rechaza.', repeat('5', 64), 'bge-m3@prueba', pg_temp.eje(2)),
  ('g7b/ingesta', 1, '4. El embudo > revisión', 'Va a revisión lo que menciona versiones de Blender anteriores a 2.80 y benchmark_publico_no_reproducido_por_g7b.', repeat('6', 64), 'bge-m3@prueba', pg_temp.eje(3)),
  ('g7b/vision', 0, 'Visión', 'G7B mide y modela costos de rendimiento para que Amatista recomiende.', repeat('7', 64), 'bge-m3@prueba', pg_temp.eje(4));

do $$
declare
  primero text;
  n integer;
begin
  -- 1. Por significado: el vector del eje 2 debe traer el fragmento del embudo primero, aunque el texto no coincida.
  select documento_id || '#' || seccion into primero from public.buscar_canon('zzz', pg_temp.eje(2), 3) limit 1;
  assert primero = 'g7b/ingesta#4. El embudo', 'por significado: salió ' || coalesce(primero, 'nada');

  -- 2. Por texto exacto de un identificador (búsqueda simple, sin raíces): el motivo exacto gana aunque el vector apunte a otro lado.
  select documento_id || '#' || seccion into primero
  from public.buscar_canon('benchmark_publico_no_reproducido_por_g7b', pg_temp.eje(4), 3, peso_texto => 3.0) limit 1;
  assert primero = 'g7b/ingesta#4. El embudo > revisión', 'por identificador: salió ' || coalesce(primero, 'nada');

  -- 3. Híbrido: texto y vector de acuerdo, el mismo fragmento suma por las dos listas y queda primero.
  select documento_id into primero from public.buscar_canon('g7b.hardware/1 vram', pg_temp.eje(1), 3) limit 1;
  assert primero = 'g7b/estandar-telemetria', 'híbrido: salió ' || coalesce(primero, 'nada');

  -- 3b. Pregunta normal por texto (con «de», «qué», «las»): el OR encuentra el embudo; un AND de todas las palabras no
  --     encontraría nada. Con peso_vector 0 solo cuenta el texto.
  select documento_id || '#' || seccion into primero
  from public.buscar_canon('¿Cuáles son las cinco etapas del embudo?', pg_temp.eje(4), 3, peso_vector => 0.0) limit 1;
  assert primero = 'g7b/ingesta#4. El embudo', 'pregunta normal por texto: salió ' || coalesce(primero, 'nada');
  assert public.consulta_canon_texto('¿de qué es la?') is null, 'solo palabras cortas: la consulta de texto debe ser nula';
  -- «g7b.hardware/1» se conserva entero; «v_exploracion» se parte en «v» y «exploracion», igual que en el texto guardado.
  assert public.consulta_canon_texto('v_exploracion de g7b.hardware/1')::text like '%''g7b.hardware/1''%'
     and public.consulta_canon_texto('v_exploracion de g7b.hardware/1')::text like '%''exploracion''%'
     and public.consulta_canon_texto('v_exploracion de g7b.hardware/1')::text not like '%''de''%',
         'identificadores: ' || public.consulta_canon_texto('v_exploracion de g7b.hardware/1')::text;

  -- 4. Filtros: por tipo y por modelo de embedding.
  select count(*) into n from public.buscar_canon('etapas', pg_temp.eje(2), 10, tipos => array['vision']);
  assert n = 1, 'filtro por tipo: ' || n;
  select count(*) into n from public.buscar_canon('etapas', pg_temp.eje(2), 10, modelo => 'otro-modelo');
  assert n = 0, 'filtro por modelo: ' || n;

  -- 5. cuantos limita el resultado.
  select count(*) into n from public.buscar_canon('etapas', pg_temp.eje(2), 2);
  assert n = 2, 'cuantos: ' || n;
end $$;

-- 6. Seguridad: la clave pública (anon) lee y busca, pero no escribe.
grant usage on schema public, extensions to anon;
grant select on public.canon_documentos, public.canon_fragmentos to anon;
grant insert on public.canon_documentos to anon;      -- aun con el permiso de tabla, RLS debe impedirlo
set local role anon;
do $$
declare n integer;
begin
  select count(*) into n from public.canon_fragmentos;
  assert n = 4, 'anon debe leer los 4 fragmentos: ' || n;
  select count(*) into n from public.buscar_canon('embudo', pg_temp.eje(2), 3);
  assert n > 0, 'anon debe poder buscar';
  begin
    insert into public.canon_documentos (id, repositorio, ruta, commit_fijado, tipo, titulo, sha256, version_canon)
    values ('intruso', 'g7b', 'x', repeat('b', 40), 'regla', 'x', repeat('8', 64), 1);
    raise exception 'anon pudo escribir: la RLS no protege';
  exception when insufficient_privilege then
    null;  -- esperado: new row violates row-level security policy
  end;
end $$;
reset role;

-- 7. Integridad: tipos y hashes inválidos se rechazan.
do $$
begin
  begin
    insert into public.canon_documentos (id, repositorio, ruta, commit_fijado, tipo, titulo, sha256, version_canon)
    values ('malo', 'g7b', 'x', 'no-es-un-commit', 'regla', 'x', repeat('9', 64), 1);
    raise exception 'aceptó un commit inválido';
  exception when check_violation then null;
  end;
  begin
    insert into public.canon_documentos (id, repositorio, ruta, commit_fijado, tipo, titulo, sha256, version_canon)
    values ('malo2', 'g7b', 'x', repeat('c', 40), 'opinion', 'x', repeat('9', 64), 1);
    raise exception 'aceptó un tipo fuera de la lista';
  exception when check_violation then null;
  end;
end $$;

select 'PRUEBAS_CANON_OK' as resultado;
rollback;
