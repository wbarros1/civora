-- ============================================================
-- Public Inhuur Platform
-- Tabellen voor bronophalingen en ruwe opdrachten
-- ============================================================


-- ------------------------------------------------------------
-- 1. Fetch runs
-- Registreert iedere poging om gegevens uit een bron op te halen.
-- ------------------------------------------------------------

create table if not exists public.fetch_runs (
    id uuid primary key default gen_random_uuid(),

    source_id uuid not null
        references public.sources(id)
        on delete cascade,

    status text not null default 'running'
        check (
            status in (
                'queued',
                'running',
                'succeeded',
                'partial',
                'failed'
            )
        ),

    triggered_by text not null default 'manual'
        check (
            triggered_by in (
                'manual',
                'scheduled',
                'api'
            )
        ),

    request_url text,
    http_status integer
        check (
            http_status is null
            or http_status between 100 and 599
        ),

    started_at timestamptz not null default now(),
    finished_at timestamptz,

    items_discovered integer not null default 0
        check (items_discovered >= 0),

    items_new integer not null default 0
        check (items_new >= 0),

    items_changed integer not null default 0
        check (items_changed >= 0),

    items_unchanged integer not null default 0
        check (items_unchanged >= 0),

    items_failed integer not null default 0
        check (items_failed >= 0),

    error_message text,

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint fetch_runs_finished_after_started
        check (
            finished_at is null
            or finished_at >= started_at
        )
);


create index if not exists fetch_runs_source_id_idx
    on public.fetch_runs(source_id);


create index if not exists fetch_runs_status_idx
    on public.fetch_runs(status);


create index if not exists fetch_runs_started_at_idx
    on public.fetch_runs(started_at desc);


drop trigger if exists set_fetch_runs_updated_at
on public.fetch_runs;


create trigger set_fetch_runs_updated_at
before update on public.fetch_runs
for each row
execute function public.set_updated_at();


alter table public.fetch_runs
enable row level security;


-- ------------------------------------------------------------
-- 2. Raw opportunities
-- Bevat de meest recente ruwe versie van iedere bronopdracht.
-- ------------------------------------------------------------

create table if not exists public.raw_opportunities (
    id uuid primary key default gen_random_uuid(),

    source_id uuid not null
        references public.sources(id)
        on delete cascade,

    source_reference text not null,
    source_url text not null,

    title_hint text,

    raw_format text not null
        check (
            raw_format in (
                'html',
                'json',
                'xml',
                'text'
            )
        ),

    raw_content text not null,

    content_hash text not null
        check (length(content_hash) = 64),

    source_status text not null default 'active'
        check (
            source_status in (
                'active',
                'closed',
                'removed',
                'unknown'
            )
        ),

    processing_status text not null default 'pending'
        check (
            processing_status in (
                'pending',
                'extracted',
                'review_required',
                'failed',
                'ignored'
            )
        ),

    latest_fetch_run_id uuid
        references public.fetch_runs(id)
        on delete set null,

    published_at timestamptz,
    closed_at timestamptz,

    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint raw_opportunities_source_reference_unique
        unique (source_id, source_reference),

    constraint raw_opportunities_seen_dates_valid
        check (last_seen_at >= first_seen_at)
);


create index if not exists raw_opportunities_source_id_idx
    on public.raw_opportunities(source_id);


create index if not exists raw_opportunities_processing_status_idx
    on public.raw_opportunities(processing_status);


create index if not exists raw_opportunities_source_status_idx
    on public.raw_opportunities(source_status);


create index if not exists raw_opportunities_last_seen_at_idx
    on public.raw_opportunities(last_seen_at desc);


create index if not exists raw_opportunities_content_hash_idx
    on public.raw_opportunities(content_hash);


drop trigger if exists set_raw_opportunities_updated_at
on public.raw_opportunities;


create trigger set_raw_opportunities_updated_at
before update on public.raw_opportunities
for each row
execute function public.set_updated_at();


alter table public.raw_opportunities
enable row level security;


-- ------------------------------------------------------------
-- 3. Raw opportunity versions
-- Bewaart iedere inhoudelijk gewijzigde versie.
-- ------------------------------------------------------------

create table if not exists public.raw_opportunity_versions (
    id uuid primary key default gen_random_uuid(),

    raw_opportunity_id uuid not null
        references public.raw_opportunities(id)
        on delete cascade,

    fetch_run_id uuid
        references public.fetch_runs(id)
        on delete set null,

    version_number integer not null
        check (version_number > 0),

    source_url text not null,

    raw_format text not null
        check (
            raw_format in (
                'html',
                'json',
                'xml',
                'text'
            )
        ),

    raw_content text not null,

    content_hash text not null
        check (length(content_hash) = 64),

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now(),

    constraint raw_opportunity_version_number_unique
        unique (
            raw_opportunity_id,
            version_number
        ),

    constraint raw_opportunity_content_hash_unique
        unique (
            raw_opportunity_id,
            content_hash
        )
);


create index if not exists raw_opportunity_versions_opportunity_idx
    on public.raw_opportunity_versions(raw_opportunity_id);


create index if not exists raw_opportunity_versions_created_at_idx
    on public.raw_opportunity_versions(created_at desc);


alter table public.raw_opportunity_versions
enable row level security;