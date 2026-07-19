-- Create knowledge and QA tables for circuit tutoring.
-- This deliberately excludes generic connection-rule tables because connection
-- validation/generation rules are owned by the backend Python pipeline.

create table if not exists public.circuit_knowledge_sources (
  source_key text primary key check (source_key ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),
  title text not null,
  publisher text,
  source_type text not null check (source_type in ('official_doc', 'official_example', 'datasheet', 'vendor_guide', 'calculator', 'local_calibration')),
  url text not null check (url ~ '^https?://'),
  retrieved_at date not null,
  license_status text not null default 'needs_review' check (license_status in ('approved', 'needs_review', 'restricted')),
  reliability_score numeric not null check (reliability_score >= 0 and reliability_score <= 1),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.circuit_component_electrical_specs (
  id uuid primary key default gen_random_uuid(),
  component_id uuid not null references public.circuit_component_assets(id) on delete cascade,
  spec_key text not null check (spec_key ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),
  spec_category text not null check (spec_category in ('power', 'io', 'timing', 'measurement', 'mechanical', 'behavior', 'safety', 'interface', 'passive')),
  summary text not null,
  spec_value jsonb not null,
  source_keys text[] not null default '{}',
  confidence_score numeric not null check (confidence_score >= 0 and confidence_score <= 1),
  review_status text not null default 'needs_review' check (review_status in ('reviewed', 'needs_review')),
  status text not null default 'ready' check (status in ('draft', 'ready', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint circuit_component_electrical_specs_unique_key unique (component_id, spec_key)
);

create table if not exists public.circuit_code_snippets (
  snippet_key text primary key check (snippet_key ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),
  title text not null,
  platform text not null check (platform in ('arduino', 'raspberry_pi', 'conceptual')),
  language text not null,
  board_slugs text[] not null default '{}',
  component_slugs text[] not null default '{}',
  code text not null,
  setup_notes text[] not null default '{}',
  source_keys text[] not null default '{}',
  confidence_score numeric not null check (confidence_score >= 0 and confidence_score <= 1),
  review_status text not null default 'needs_review' check (review_status in ('reviewed', 'needs_review')),
  status text not null default 'ready' check (status in ('draft', 'ready', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.circuit_task_result_templates (
  task_key text primary key check (task_key ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),
  title text not null,
  task_type text not null check (task_type in ('build', 'measure', 'control', 'debug', 'explain')),
  difficulty text not null check (difficulty in ('beginner', 'intermediate', 'advanced')),
  user_intent_patterns text[] not null default '{}',
  board_slugs text[] not null default '{}',
  component_slugs text[] not null default '{}',
  task_payload jsonb not null,
  result_payload jsonb not null,
  expected_result text not null,
  code_snippet_key text references public.circuit_code_snippets(snippet_key) on delete set null,
  troubleshooting_keys text[] not null default '{}',
  source_keys text[] not null default '{}',
  tags text[] not null default '{}',
  confidence_score numeric not null check (confidence_score >= 0 and confidence_score <= 1),
  review_status text not null default 'needs_review' check (review_status in ('reviewed', 'needs_review')),
  status text not null default 'ready' check (status in ('draft', 'ready', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.circuit_troubleshooting_guides (
  issue_key text primary key check (issue_key ~ '^[a-z0-9]+(_[a-z0-9]+)*$'),
  title text not null,
  severity text not null check (severity in ('info', 'warning', 'risk')),
  symptom_patterns text[] not null default '{}',
  board_slugs text[] not null default '{}',
  component_slugs text[] not null default '{}',
  likely_causes jsonb not null,
  diagnostic_steps jsonb not null,
  fixes jsonb not null,
  source_keys text[] not null default '{}',
  confidence_score numeric not null check (confidence_score >= 0 and confidence_score <= 1),
  review_status text not null default 'needs_review' check (review_status in ('reviewed', 'needs_review')),
  status text not null default 'ready' check (status in ('draft', 'ready', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists circuit_component_electrical_specs_component_idx on public.circuit_component_electrical_specs(component_id);
create index if not exists circuit_code_snippets_platform_idx on public.circuit_code_snippets(platform);
create index if not exists circuit_task_result_templates_task_type_idx on public.circuit_task_result_templates(task_type);
create index if not exists circuit_troubleshooting_guides_severity_idx on public.circuit_troubleshooting_guides(severity);

alter table public.circuit_knowledge_sources enable row level security;
alter table public.circuit_component_electrical_specs enable row level security;
alter table public.circuit_code_snippets enable row level security;
alter table public.circuit_task_result_templates enable row level security;
alter table public.circuit_troubleshooting_guides enable row level security;

grant select on public.circuit_knowledge_sources to anon, authenticated;
grant select on public.circuit_component_electrical_specs to anon, authenticated;
grant select on public.circuit_code_snippets to anon, authenticated;
grant select on public.circuit_task_result_templates to anon, authenticated;
grant select on public.circuit_troubleshooting_guides to anon, authenticated;

grant select, insert, update, delete on public.circuit_knowledge_sources to service_role;
grant select, insert, update, delete on public.circuit_component_electrical_specs to service_role;
grant select, insert, update, delete on public.circuit_code_snippets to service_role;
grant select, insert, update, delete on public.circuit_task_result_templates to service_role;
grant select, insert, update, delete on public.circuit_troubleshooting_guides to service_role;

drop policy if exists "Public read ready knowledge sources" on public.circuit_knowledge_sources;
create policy "Public read ready knowledge sources" on public.circuit_knowledge_sources
for select to anon, authenticated using (true);

drop policy if exists "Public read ready component specs" on public.circuit_component_electrical_specs;
create policy "Public read ready component specs" on public.circuit_component_electrical_specs
for select to anon, authenticated using (
  status = 'ready'
  and exists (
    select 1 from public.circuit_component_assets assets
    where assets.id = component_id and assets.status = 'ready'
  )
);

drop policy if exists "Public read ready code snippets" on public.circuit_code_snippets;
create policy "Public read ready code snippets" on public.circuit_code_snippets
for select to anon, authenticated using (status = 'ready');

drop policy if exists "Public read ready task results" on public.circuit_task_result_templates;
create policy "Public read ready task results" on public.circuit_task_result_templates
for select to anon, authenticated using (status = 'ready');

drop policy if exists "Public read ready troubleshooting guides" on public.circuit_troubleshooting_guides;
create policy "Public read ready troubleshooting guides" on public.circuit_troubleshooting_guides
for select to anon, authenticated using (status = 'ready');
