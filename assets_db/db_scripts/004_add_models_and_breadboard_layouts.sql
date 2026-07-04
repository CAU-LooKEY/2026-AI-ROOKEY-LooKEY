insert into storage.buckets (
  id,
  name,
  public,
  file_size_limit,
  allowed_mime_types
)
values (
  'circuit-assets',
  'circuit-assets',
  true,
  52428800,
  array[
    'image/png',
    'image/jpeg',
    'image/svg+xml',
    'model/gltf-binary'
  ]::text[]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create table if not exists public.circuit_component_asset_models (
  id uuid primary key default gen_random_uuid(),
  component_id uuid not null references public.circuit_component_assets(id) on delete cascade,
  model_kind text not null check (model_kind in ('production_3d', 'candidate_3d', 'source_3d')),
  storage_path text not null,
  mime_type text not null default 'model/gltf-binary' check (mime_type in ('model/gltf-binary')),
  format text not null default 'glb' check (format in ('glb')),
  source_filename text,
  file_size_bytes bigint check (file_size_bytes is null or file_size_bytes > 0),
  sha256 text,
  bounds jsonb not null default '{}'::jsonb,
  dimensions jsonb not null default '{}'::jsonb,
  unit text not null default 'model-unit',
  audit_status text not null default 'needs_scale_review' check (audit_status in ('ready', 'needs_scale_review', 'needs_optimization', 'rejected')),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint circuit_component_asset_models_unique_kind unique (component_id, model_kind)
);

create table if not exists public.circuit_breadboard_layouts (
  id uuid primary key default gen_random_uuid(),
  component_id uuid not null references public.circuit_component_assets(id) on delete cascade,
  layout_kind text not null default 'breadboard' check (layout_kind = 'breadboard'),
  hole_coordinate_system text not null default 'image-pixel-procedural' check (hole_coordinate_system = 'image-pixel-procedural'),
  column_indexing text not null default 'left-to-right' check (column_indexing in ('left-to-right')),
  columns integer not null check (columns > 0),
  terminal_rows text[] not null default array['A','B','C','D','E','F','G','H','I','J'],
  terminal jsonb not null,
  rails jsonb not null,
  notes text[] not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint circuit_breadboard_layouts_unique_component unique (component_id)
);

create index if not exists circuit_component_asset_models_component_idx
  on public.circuit_component_asset_models(component_id);
create index if not exists circuit_breadboard_layouts_component_idx
  on public.circuit_breadboard_layouts(component_id);

alter table public.circuit_component_asset_models enable row level security;
alter table public.circuit_breadboard_layouts enable row level security;

grant select on public.circuit_component_asset_models to anon, authenticated;
grant select on public.circuit_breadboard_layouts to anon, authenticated;

grant select, insert, update, delete on public.circuit_component_asset_models to service_role;
grant select, insert, update, delete on public.circuit_breadboard_layouts to service_role;

drop policy if exists "Public read models for ready circuit assets" on public.circuit_component_asset_models;
create policy "Public read models for ready circuit assets"
on public.circuit_component_asset_models
for select
to anon, authenticated
using (
  exists (
    select 1
    from public.circuit_component_assets assets
    where assets.id = component_id
      and assets.status = 'ready'
  )
);

drop policy if exists "Public read breadboard layouts for ready circuit assets" on public.circuit_breadboard_layouts;
create policy "Public read breadboard layouts for ready circuit assets"
on public.circuit_breadboard_layouts
for select
to anon, authenticated
using (
  exists (
    select 1
    from public.circuit_component_assets assets
    where assets.id = component_id
      and assets.status = 'ready'
  )
);
