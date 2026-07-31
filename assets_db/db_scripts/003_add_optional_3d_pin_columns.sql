alter table if exists public.circuit_component_pins
  add column if not exists x_3d numeric,
  add column if not exists y_3d numeric,
  add column if not exists z_3d numeric,
  add column if not exists model_anchor_name text;

do $$
begin
  if to_regclass('public.circuit_component_pins') is not null and not exists (
    select 1
    from pg_constraint
    where conname = 'circuit_component_pins_3d_complete_check'
      and conrelid = to_regclass('public.circuit_component_pins')
  ) then
    alter table public.circuit_component_pins
      add constraint circuit_component_pins_3d_complete_check check (
        (x_3d is null and y_3d is null and z_3d is null)
        or
        (x_3d is not null and y_3d is not null and z_3d is not null)
      );
  end if;
end $$;
