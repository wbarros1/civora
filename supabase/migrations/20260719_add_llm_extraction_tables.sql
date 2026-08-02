-- Tabellen voor gestructureerde opdrachten en LLM-extractieruns.

create table if not exists public.structured_opportunities (
    id uuid primary key default gen_random_uuid(),

    raw_opportunity_id uuid not null
        references public.raw_opportunities(id)
        on delete cascade,

    source_id uuid not null
        references public.sources(id)
        on delete cascade,

    source_reference text not null,

    title text not null,
    client_name text,
    description text,
    location text,
    province text,

    work_arrangement text not null default 'unknown'
        check (
            work_arrangement in (
                'on_site',
                'hybrid',
                'remote',
                'unknown'
            )
        ),

    start_date date,
    end_date date,
    application_deadline timestamptz,
    publication_date date,

    hours_per_week_min numeric(6, 2),
    hours_per_week_max numeric(6, 2),
    duration_months numeric(6, 2),

    extension_possible boolean,
    number_of_positions integer,

    rate_min numeric(12, 2),
    rate_max numeric(12, 2),
    rate_currency text not null default 'EUR',
    rate_period text not null default 'unknown'
        check (
            rate_period in (
                'hour',
                'day',
                'month',
                'fixed',
                'unknown'
            )
        ),

    employment_relationship text not null default 'unknown'
        check (
            employment_relationship in (
                'zzp',
                'secondment',
                'both',
                'unknown'
            )
        ),

    education_level text,
    minimum_years_experience numeric(6, 2),

    requirements jsonb not null default '[]'::jsonb
        check (
            jsonb_typeof(requirements) = 'array'
        ),

    wishes jsonb not null default '[]'::jsonb
        check (
            jsonb_typeof(wishes) = 'array'
        ),

    competencies jsonb not null default '[]'::jsonb
        check (
            jsonb_typeof(competencies) = 'array'
        ),

    skills jsonb not null default '[]'::jsonb
        check (
            jsonb_typeof(skills) = 'array'
        ),

    contact_information jsonb not null default '{}'::jsonb
        check (
            jsonb_typeof(contact_information) = 'object'
        ),

    source_status text not null default 'active'
        check (
            source_status in (
                'active',
                'closed',
                'unknown'
            )
        ),

    extraction_confidence numeric(5, 4)
        check (
            extraction_confidence is null
            or (
                extraction_confidence >= 0
                and extraction_confidence <= 1
            )
        ),

    review_required boolean not null default false,
    review_reasons jsonb not null default '[]'::jsonb
        check (
            jsonb_typeof(review_reasons) = 'array'
        ),

    extracted_from_hash text not null,
    extraction_prompt_version text not null,
    extraction_model text not null,
    extracted_at timestamptz not null default now(),

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    constraint structured_opportunities_raw_unique
        unique (raw_opportunity_id),

    constraint structured_opportunities_source_reference_unique
        unique (source_id, source_reference),

    constraint structured_opportunities_hours_range_valid
        check (
            hours_per_week_min is null
            or hours_per_week_max is null
            or hours_per_week_max >= hours_per_week_min
        ),

    constraint structured_opportunities_rate_range_valid
        check (
            rate_min is null
            or rate_max is null
            or rate_max >= rate_min
        ),

    constraint structured_opportunities_positions_positive
        check (
            number_of_positions is null
            or number_of_positions >= 1
        )
);


create table if not exists public.opportunity_extraction_runs (
    id uuid primary key default gen_random_uuid(),

    raw_opportunity_id uuid not null
        references public.raw_opportunities(id)
        on delete cascade,

    raw_opportunity_version_id uuid
        references public.raw_opportunity_versions(id)
        on delete set null,

    structured_opportunity_id uuid
        references public.structured_opportunities(id)
        on delete set null,

    source_id uuid not null
        references public.sources(id)
        on delete cascade,

    source_reference text not null,

    status text not null default 'queued'
        check (
            status in (
                'queued',
                'running',
                'succeeded',
                'review_required',
                'failed',
                'skipped'
            )
        ),

    provider text not null,
    model_name text not null,
    prompt_version text not null,

    input_hash text not null,
    input_character_count integer not null
        check (
            input_character_count >= 0
        ),

    overall_confidence numeric(5, 4)
        check (
            overall_confidence is null
            or (
                overall_confidence >= 0
                and overall_confidence <= 1
            )
        ),

    request_metadata jsonb not null default '{}'::jsonb
        check (
            jsonb_typeof(request_metadata) = 'object'
        ),

    raw_response jsonb,
    parsed_output jsonb,

    validation_errors jsonb not null default '[]'::jsonb
        check (
            jsonb_typeof(validation_errors) = 'array'
        ),

    review_reasons jsonb not null default '[]'::jsonb
        check (
            jsonb_typeof(review_reasons) = 'array'
        ),

    input_tokens integer,
    output_tokens integer,
    total_tokens integer,
    estimated_cost_usd numeric(12, 6),

    error_type text,
    error_message text,

    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),

    constraint opportunity_extraction_runs_token_counts_valid
        check (
            (input_tokens is null or input_tokens >= 0)
            and (output_tokens is null or output_tokens >= 0)
            and (total_tokens is null or total_tokens >= 0)
        )
);


create index if not exists
    idx_structured_opportunities_source
on public.structured_opportunities (
    source_id,
    source_reference
);


create index if not exists
    idx_structured_opportunities_deadline
on public.structured_opportunities (
    application_deadline
);


create index if not exists
    idx_structured_opportunities_review
on public.structured_opportunities (
    review_required
)
where review_required = true;


create index if not exists
    idx_extraction_runs_raw_opportunity
on public.opportunity_extraction_runs (
    raw_opportunity_id,
    created_at desc
);


create index if not exists
    idx_extraction_runs_status
on public.opportunity_extraction_runs (
    status,
    created_at
);


create index if not exists
    idx_extraction_runs_input_hash
on public.opportunity_extraction_runs (
    input_hash
);