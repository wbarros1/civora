-- ============================================================
-- Civora opportunity vakgroep classification
-- ============================================================


-- ------------------------------------------------------------
-- Enums
-- ------------------------------------------------------------

create type public.opportunity_vakgroep as enum (
    'procesmanagement',
    'data_ai',
    'ict',
    'finance',
    'overige'
);


create type public.classification_source as enum (
    'llm',
    'manual'
);


-- ============================================================
-- Opportunity classifications
-- ============================================================

create table public.opportunity_classifications (
    id uuid primary key
        default gen_random_uuid(),

    opportunity_extraction_run_id uuid not null
        references public.opportunity_extraction_runs(id)
        on delete cascade,

    structured_opportunity_id uuid not null
        references public.structured_opportunities(id)
        on delete cascade,

    primary_vakgroep public.opportunity_vakgroep
        not null,

    classification_confidence numeric(4, 3)
        not null,

    classifier_version text
        not null,

    classification_source public.classification_source
        not null
        default 'llm',

    manual_override boolean
        not null
        default false,

    relevance_threshold smallint
        not null
        default 60,

    max_matches smallint
        not null
        default 3,

    review_reasons jsonb
        not null
        default '[]'::jsonb,

    classified_at timestamptz
        not null
        default now(),

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint opportunity_classifications_confidence_range
        check (
            classification_confidence >= 0
            and classification_confidence <= 1
        ),

    constraint opportunity_classifications_version_not_blank
        check (
            length(
                trim(classifier_version)
            ) > 0
        ),

    constraint opportunity_classifications_threshold_range
        check (
            relevance_threshold >= 0
            and relevance_threshold <= 100
        ),

    constraint opportunity_classifications_max_matches_range
        check (
            max_matches >= 1
            and max_matches <= 4
        ),

    constraint opportunity_classifications_review_reasons_array
        check (
            jsonb_typeof(
                review_reasons
            ) = 'array'
        ),

    constraint opportunity_classifications_manual_source
        check (
            manual_override = false
            or classification_source = 'manual'
        ),

    constraint opportunity_classifications_unique_version
        unique (
            opportunity_extraction_run_id,
            classifier_version
        )
);


comment on table public.opportunity_classifications is
'Versioned Civora vakgroep classification for a structured opportunity extraction.';


comment on column public.opportunity_classifications.primary_vakgroep is
'Primary vakgroep derived from the four relevance scores, or overige when no score reaches the threshold.';


comment on column public.opportunity_classifications.classification_confidence is
'Confidence from 0 to 1 in the overall classification.';


comment on column public.opportunity_classifications.classifier_version is
'Version identifier of the classifier, for example civora-vakgroep-v1.';


comment on column public.opportunity_classifications.relevance_threshold is
'Threshold used to derive relevant vakgroep matches from raw scores.';


comment on column public.opportunity_classifications.max_matches is
'Maximum number of vakgroepen considered relevant after ranking scores.';


-- ============================================================
-- Vakgroep scores
-- ============================================================

create table public.opportunity_vakgroep_scores (
    id uuid primary key
        default gen_random_uuid(),

    classification_id uuid not null
        references public.opportunity_classifications(id)
        on delete cascade,

    vakgroep public.vakgroep
        not null,

    relevance_score smallint
        not null,

    reason text,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint opportunity_vakgroep_scores_score_range
        check (
            relevance_score >= 0
            and relevance_score <= 100
        ),

    constraint opportunity_vakgroep_scores_reason_not_blank
        check (
            reason is null
            or length(
                trim(reason)
            ) > 0
        ),

    constraint opportunity_vakgroep_scores_unique_vakgroep
        unique (
            classification_id,
            vakgroep
        )
);


comment on table public.opportunity_vakgroep_scores is
'Raw relevance scores from 0 to 100 for each Civora user vakgroep.';


comment on column public.opportunity_vakgroep_scores.reason is
'Short classifier explanation for the relevance score.';


-- ============================================================
-- Validate extraction -> structured opportunity relationship
-- ============================================================

create or replace function
    public.validate_opportunity_classification_link()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    expected_structured_opportunity_id uuid;
begin
    select
        extraction_run.structured_opportunity_id
    into
        expected_structured_opportunity_id
    from
        public.opportunity_extraction_runs
            as extraction_run
    where
        extraction_run.id
        = new.opportunity_extraction_run_id;

    if not found then
        raise exception
            'opportunity extraction run does not exist';
    end if;

    if expected_structured_opportunity_id is null then
        raise exception
            'opportunity extraction run has no structured opportunity';
    end if;

    if
        new.structured_opportunity_id
        is distinct from
        expected_structured_opportunity_id
    then
        raise exception
            'structured opportunity does not belong to extraction run';
    end if;

    return new;
end;
$$;


create trigger opportunity_classifications_validate_link
    before insert or update
    of
        opportunity_extraction_run_id,
        structured_opportunity_id
    on public.opportunity_classifications
    for each row
    execute procedure
        public.validate_opportunity_classification_link();


-- ============================================================
-- updated_at triggers
-- ============================================================

create trigger opportunity_classifications_set_updated_at
    before update
    on public.opportunity_classifications
    for each row
    execute procedure public.set_updated_at();


create trigger opportunity_vakgroep_scores_set_updated_at
    before update
    on public.opportunity_vakgroep_scores
    for each row
    execute procedure public.set_updated_at();


-- ============================================================
-- Indexes
-- ============================================================

create index
    opportunity_classifications_structured_idx
on public.opportunity_classifications (
    structured_opportunity_id,
    classified_at desc
);


create index
    opportunity_classifications_version_idx
on public.opportunity_classifications (
    classifier_version,
    classified_at desc
);


create index
    opportunity_vakgroep_scores_matching_idx
on public.opportunity_vakgroep_scores (
    vakgroep,
    relevance_score desc,
    classification_id
);


-- ============================================================
-- Permissions
-- ============================================================

revoke all
on public.opportunity_classifications
from
    anon,
    authenticated;


revoke all
on public.opportunity_vakgroep_scores
from
    anon,
    authenticated;


grant
    select,
    insert,
    update,
    delete
on public.opportunity_classifications
to service_role;


grant
    select,
    insert,
    update,
    delete
on public.opportunity_vakgroep_scores
to service_role;


-- ============================================================
-- Row Level Security
-- ============================================================

alter table public.opportunity_classifications
enable row level security;


alter table public.opportunity_vakgroep_scores
enable row level security;


-- No anon/authenticated policies are intentionally created.
-- These tables are accessed through the trusted Civora backend.