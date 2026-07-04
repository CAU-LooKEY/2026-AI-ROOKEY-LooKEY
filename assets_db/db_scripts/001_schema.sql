create extension if not exists pgcrypto;

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
  10485760,
  array[
    'image/png',
    'image/jpeg',
    'image/svg+xml'
  ]::text[]
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create table if not exists public.circuit_component_assets (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  display_name text not null,
  category text not null,
  board_family text,
  description text,
  grid_width integer not null check (grid_width > 0),
  grid_height integer not null check (grid_height > 0),
  pixel_width integer not null check (pixel_width > 0),
  pixel_height integer not null check (pixel_height > 0),
  origin_x numeric not null default 0,
  origin_y numeric not null default 0,
  pin_coordinate_system text not null default 'image-pixel' check (pin_coordinate_system = 'image-pixel'),
  recommended_image_kind text not null default 'isometric_2d' check (recommended_image_kind in ('isometric_2d', 'preview_3d', 'schematic_2d')),
  license_status text not null default 'needs_review' check (license_status in ('needs_review', 'approved', 'restricted')),
  trademark_notes text,
  status text not null default 'draft' check (status in ('draft', 'ready', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.circuit_component_asset_images (
  id uuid primary key default gen_random_uuid(),
  component_id uuid not null references public.circuit_component_assets(id) on delete cascade,
  image_kind text not null check (image_kind in ('isometric_2d', 'preview_3d', 'schematic_2d')),
  storage_path text,
  external_url text,
  mime_type text check (mime_type is null or mime_type in ('image/png', 'image/jpeg', 'image/svg+xml')),
  width_px integer check (width_px is null or width_px > 0),
  height_px integer check (height_px is null or height_px > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint circuit_component_asset_images_source_check check (storage_path is not null or external_url is not null),
  constraint circuit_component_asset_images_unique_kind unique (component_id, image_kind)
);

create table if not exists public.circuit_component_pins (
  id uuid primary key default gen_random_uuid(),
  component_id uuid not null references public.circuit_component_assets(id) on delete cascade,
  pin_key text not null,
  label text not null,
  signal_type text not null check (signal_type in ('analog', 'component', 'digital', 'ground', 'gpio', 'i2c', 'power', 'pwm', 'spi', 'uart')),
  side text not null check (side in ('top', 'right', 'bottom', 'left', 'center')),
  x_px numeric not null check (x_px >= 0),
  y_px numeric not null check (y_px >= 0),
  x_3d numeric,
  y_3d numeric,
  z_3d numeric,
  model_anchor_name text,
  aliases text[] not null default '{}',
  notes text,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint circuit_component_pins_3d_complete_check check (
    (x_3d is null and y_3d is null and z_3d is null)
    or
    (x_3d is not null and y_3d is not null and z_3d is not null)
  ),
  constraint circuit_component_pins_unique_key unique (component_id, pin_key)
);

create index if not exists circuit_component_assets_category_idx on public.circuit_component_assets(category);
create index if not exists circuit_component_pins_component_order_idx on public.circuit_component_pins(component_id, sort_order);

alter table public.circuit_component_assets enable row level security;
alter table public.circuit_component_asset_images enable row level security;
alter table public.circuit_component_pins enable row level security;

grant select on public.circuit_component_assets to anon, authenticated;
grant select on public.circuit_component_asset_images to anon, authenticated;
grant select on public.circuit_component_pins to anon, authenticated;

grant select, insert, update, delete on public.circuit_component_assets to service_role;
grant select, insert, update, delete on public.circuit_component_asset_images to service_role;
grant select, insert, update, delete on public.circuit_component_pins to service_role;

drop policy if exists "Public read ready circuit assets" on public.circuit_component_assets;
create policy "Public read ready circuit assets" on public.circuit_component_assets for select to anon, authenticated using (status = 'ready');

drop policy if exists "Public read images for ready circuit assets" on public.circuit_component_asset_images;
create policy "Public read images for ready circuit assets" on public.circuit_component_asset_images for select to anon, authenticated using (
  exists (select 1 from public.circuit_component_assets assets where assets.id = component_id and assets.status = 'ready')
);

drop policy if exists "Public read pins for ready circuit assets" on public.circuit_component_pins;
create policy "Public read pins for ready circuit assets" on public.circuit_component_pins for select to anon, authenticated using (
  exists (select 1 from public.circuit_component_assets assets where assets.id = component_id and assets.status = 'ready')
);

drop policy if exists "Public read circuit asset files" on storage.objects;
create policy "Public read circuit asset files" on storage.objects for select to anon, authenticated using (bucket_id = 'circuit-assets');
