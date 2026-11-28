-- [REVISION 2026-11-27] Migracion del canon RAG (tablas, indices HNSW/GIN, RLS de solo lectura y funcion buscar_canon con RRF).
-- Canon de Amatista IA: RAG con los estándares del proyecto (canon/canon.yml).
--
-- · canon_documentos: un renglón por documento del canon, con su repositorio, ruta, commit fijado y hash.
-- · canon_fragmentos: el texto partido por secciones, su vector (bge-m3, 1024 dimensiones) y su índice de texto.
-- · buscar_canon(): búsqueda híbrida (texto + significado) combinada por fusión de rangos recíprocos (RRF).
--
-- Seguridad: con la clave pública (publishable) solo se LEE; escribir exige la clave secreta (rol service_role,
-- que no pasa por RLS). El canon son documentos públicos del proyecto: no hay datos personales.

create extension if not exists vector with schema extensions;

-- Documentos ---------------------------------------------------------------------------------------------------
create table public.canon_documentos (
  id             text primary key,                       -- 'g7b/estandar-telemetria' (el id de canon.yml)
  repositorio    text not null,                          -- 'g7b' | 'amatista'
  ruta           text not null,                          -- 'docs/ESTANDAR_TELEMETRIA.md'
  commit_fijado  text not null check (commit_fijado ~ '^[0-9a-f]{40}$'),
  tipo           text not null check (tipo in ('vision', 'glosario', 'estandar', 'contrato', 'regla', 'politica', 'ejemplo')),
  titulo         text not null,
  idioma         text not null default 'es' check (idioma in ('es', 'en')),
  sha256         text not null check (sha256 ~ '^[0-9a-f]{64}$'),   -- del texto ya filtrado por secciones
  version_canon  integer not null check (version_canon > 0),
  actualizado    timestamptz not null default now()
);

comment on table public.canon_documentos is 'Documentos del canon de Amatista IA (canon/canon.yml), fijados a un commit.';

-- Fragmentos ---------------------------------------------------------------------------------------------------
create table public.canon_fragmentos (
  id                bigint generated always as identity primary key,
  documento_id      text not null references public.canon_documentos (id) on delete cascade,
  orden             integer not null check (orden >= 0),
  seccion           text,                                 -- ruta de títulos: '2. Hardware records > gpus'
  texto             text not null check (length(texto) > 0),
  tokens            integer check (tokens > 0),
  sha256            text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  modelo_embedding  text not null,                        -- 'bge-m3@<digest de Ollama>'
  embedding         extensions.vector(1024) not null,
  -- 'simple': sin raíces de idioma. El canon mezcla español e inglés (INVENTARIO.md, C2) y así los identificadores
  -- exactos (g7b.hardware/1, benchmark_publico_no_reproducido_por_g7b) se encuentran tal cual.
  busqueda          tsvector generated always as (to_tsvector('simple', coalesce(seccion, '') || ' ' || texto)) stored,
  creado            timestamptz not null default now(),
  unique (documento_id, orden, modelo_embedding)
);

comment on table public.canon_fragmentos is 'Fragmentos del canon con su vector (bge-m3, 1024) y su índice de texto.';

create index canon_fragmentos_embedding_idx on public.canon_fragmentos using hnsw (embedding extensions.vector_cosine_ops);
create index canon_fragmentos_busqueda_idx on public.canon_fragmentos using gin (busqueda);
create index canon_fragmentos_documento_idx on public.canon_fragmentos (documento_id);

-- Seguridad: lectura para todos, escritura solo con la clave secreta ----------------------------------------------
alter table public.canon_documentos enable row level security;
alter table public.canon_fragmentos enable row level security;

create policy "canon: lectura" on public.canon_documentos for select to anon, authenticated using (true);
create policy "canon: lectura" on public.canon_fragmentos for select to anon, authenticated using (true);
-- Sin políticas de insert/update/delete: solo service_role (que no pasa por RLS) puede escribir.

-- Búsqueda híbrida -----------------------------------------------------------------------------------------------
-- RRF: puntaje = peso_texto / (k + rango_texto) + peso_vector / (k + rango_vector). No hay que calibrar escalas
-- distintas (ts_rank frente a distancia coseno): solo cuenta el orden en cada lista.

-- La consulta de texto es un OR de las palabras de 4 letras o más y de los identificadores con dígitos, «.» o «/»
-- (g7b.hardware/1, n0). El analizador «simple» parte «v_exploracion» en «v» y «exploracion», igual en el texto guardado. Un AND de todas las palabras casi nunca encuentra nada con una pregunta
-- normal: en la prueba de 46 preguntas, AND dio recall@3 de 0.17 y este OR, 0.89. Las palabras cortas («de», «qué»,
-- «los») se quitan porque la configuración «simple» no tiene palabras vacías y ts_rank no pondera por rareza.
-- [REVISION-BUG] (baja) Si ninguna palabra pasa el filtro, string_agg da NULL y to_tsquery(NULL) anula toda la
-- rama de texto (solo queda la vectorial). Funciona, pero conviene documentarlo o devolver una tsquery vacia.
create or replace function public.consulta_canon_texto(consulta text)
returns tsquery
language sql
immutable
set search_path = public
as $$
  select to_tsquery('simple', string_agg(quote_literal(t), ' | '))
  from unnest(tsvector_to_array(to_tsvector('simple', consulta))) as t
  where length(t) >= 4 or t ~ '[0-9_./]';
$$;

create or replace function public.buscar_canon(
  consulta           text,
  consulta_embedding extensions.vector(1024),
  cuantos            integer default 5,
  modelo             text default null,           -- filtrar por modelo de embedding (null = cualquiera)
  tipos              text[] default null,         -- filtrar por tipo de documento (null = todos)
  peso_texto         double precision default 1.0,
  peso_vector        double precision default 1.0,
  k_rrf              integer default 50
)
returns table (
  fragmento_id  bigint,
  documento_id  text,
  tipo          text,
  ruta          text,
  commit_fijado text,
  seccion       text,
  texto         text,
  puntaje       double precision
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
  with candidatos as (
    select f.id, f.documento_id, f.seccion, f.texto, f.busqueda, f.embedding, d.tipo, d.ruta, d.commit_fijado
    from public.canon_fragmentos f
    join public.canon_documentos d on d.id = f.documento_id
    where (modelo is null or f.modelo_embedding = modelo)
      and (tipos is null or d.tipo = any (tipos))
  ),
  por_texto as (
    select id, row_number() over (order by ts_rank(busqueda, public.consulta_canon_texto(consulta)) desc) as rango
    from candidatos
    where busqueda @@ public.consulta_canon_texto(consulta)
    order by rango
    limit greatest(cuantos, 1) * 4
  ),
  por_vector as (
    select id, row_number() over (order by embedding <=> consulta_embedding) as rango
    from candidatos
    order by embedding <=> consulta_embedding
    limit greatest(cuantos, 1) * 4
  ),
  fusion as (
    select coalesce(t.id, v.id) as id,
           coalesce(peso_texto / (k_rrf + t.rango), 0.0) + coalesce(peso_vector / (k_rrf + v.rango), 0.0) as puntaje
    from por_texto t
    full outer join por_vector v on v.id = t.id
  )
  select c.id, c.documento_id, c.tipo, c.ruta, c.commit_fijado, c.seccion, c.texto, f.puntaje
  from fusion f
  join candidatos c on c.id = f.id
  order by f.puntaje desc
  limit cuantos;
$$;

comment on function public.buscar_canon is 'Búsqueda híbrida en el canon (texto simple + coseno), combinada por RRF.';

-- Permisos explícitos: no dependen de que el proyecto exponga las tablas nuevas por omisión (auto_expose_new_tables).
grant usage on schema public to anon, authenticated, service_role;
grant select on public.canon_documentos, public.canon_fragmentos to anon, authenticated;
grant select, insert, update, delete on public.canon_documentos, public.canon_fragmentos to service_role;
grant usage, select on sequence public.canon_fragmentos_id_seq to service_role;
grant execute on function public.buscar_canon, public.consulta_canon_texto to anon, authenticated, service_role;
