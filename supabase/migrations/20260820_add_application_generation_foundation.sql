begin;


-- ============================================================
-- Civora Phase C
-- Application generation foundation
-- ============================================================


-- ============================================================
-- 1. Enums
-- ============================================================

create type public.civora_cv_processing_status
as enum (
    'uploaded',
    'processing',
    'ready',
    'failed'
);


create type public.civora_template_type
as enum (
    'motivation_letter',
    'cv'
);


create type public.civora_template_status
as enum (
    'draft',
    'active',
    'archived'
);


create type public.civora_application_package_status
as enum (
    'draft',
    'generating',
    'ready',
    'failed'
);


create type public.civora_generation_run_status
as enum (
    'pending',
    'generating',
    'ready',
    'failed'
);


create type public.civora_generated_document_type
as enum (
    'motivation_letter',
    'cv'
);


create type public.civora_generated_document_status
as enum (
    'pending',
    'ready',
    'failed'
);


-- ============================================================
-- 2. Shared updated_at trigger
-- ============================================================

create or replace function
    public.civora_set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();

    return new;
end;
$$;


-- ============================================================
-- 3. User CVs
-- ============================================================

create table public.user_cvs (
    id uuid
        primary key
        default gen_random_uuid(),

    user_id uuid
        not null
        references public.profiles(id)
        on delete cascade,

    original_filename text
        not null,

    storage_bucket text
        not null
        default 'user-cvs',

    storage_path text
        not null,

    mime_type text
        not null,

    file_size_bytes bigint
        not null,

    sha256 text
        not null,

    processing_status
        public.civora_cv_processing_status
        not null
        default 'uploaded',

    processing_error text,

    is_active boolean
        not null
        default true,

    uploaded_at timestamptz
        not null
        default now(),

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint user_cvs_original_filename_not_blank
        check (
            length(
                btrim(
                    original_filename
                )
            ) > 0
        ),

    constraint user_cvs_storage_bucket_valid
        check (
            storage_bucket = 'user-cvs'
        ),

    constraint user_cvs_storage_path_not_blank
        check (
            length(
                btrim(
                    storage_path
                )
            ) > 0
        ),

    constraint user_cvs_mime_type_valid
        check (
            mime_type in (
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
        ),

    constraint user_cvs_file_size_valid
        check (
            file_size_bytes > 0
            and file_size_bytes <= 10485760
        ),

    constraint user_cvs_sha256_valid
        check (
            sha256 ~ '^[0-9a-fA-F]{64}$'
        )
);


create unique index
    user_cvs_storage_path_unique
on public.user_cvs (
    storage_path
);


create unique index
    user_cvs_one_active_per_user
on public.user_cvs (
    user_id
)
where is_active = true;


create index
    user_cvs_user_id_idx
on public.user_cvs (
    user_id
);


create index
    user_cvs_processing_status_idx
on public.user_cvs (
    processing_status
);


create trigger
    user_cvs_set_updated_at
before update
on public.user_cvs
for each row
execute function
    public.civora_set_updated_at();


-- ============================================================
-- 4. Structured candidate profiles
-- ============================================================

create table
    public.structured_candidate_profiles
(
    id uuid
        primary key
        default gen_random_uuid(),

    user_id uuid
        not null
        references public.profiles(id)
        on delete cascade,

    user_cv_id uuid
        not null
        references public.user_cvs(id)
        on delete cascade,

    schema_version text
        not null,

    profile_data jsonb
        not null,

    provider text,

    model_name text,

    prompt_version text,

    input_hash text,

    input_token_count integer,

    output_token_count integer,

    total_token_count integer,

    validation_errors jsonb
        not null
        default '[]'::jsonb,

    extraction_confidence numeric(4, 3),

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint structured_candidate_profiles_cv_unique
        unique (
            user_cv_id
        ),

    constraint structured_candidate_profiles_schema_version_not_blank
        check (
            length(
                btrim(
                    schema_version
                )
            ) > 0
        ),

    constraint structured_candidate_profiles_profile_data_object
        check (
            jsonb_typeof(
                profile_data
            ) = 'object'
        ),

    constraint structured_candidate_profiles_validation_errors_array
        check (
            jsonb_typeof(
                validation_errors
            ) = 'array'
        ),

    constraint structured_candidate_profiles_input_hash_valid
        check (
            input_hash is null
            or input_hash
                ~ '^[0-9a-fA-F]{64}$'
        ),

    constraint structured_candidate_profiles_input_tokens_valid
        check (
            input_token_count is null
            or input_token_count >= 0
        ),

    constraint structured_candidate_profiles_output_tokens_valid
        check (
            output_token_count is null
            or output_token_count >= 0
        ),

    constraint structured_candidate_profiles_total_tokens_valid
        check (
            total_token_count is null
            or total_token_count >= 0
        ),

    constraint structured_candidate_profiles_confidence_valid
        check (
            extraction_confidence is null
            or (
                extraction_confidence >= 0
                and extraction_confidence <= 1
            )
        )
);


create index
    structured_candidate_profiles_user_id_idx
on public.structured_candidate_profiles (
    user_id
);


create trigger
    structured_candidate_profiles_set_updated_at
before update
on public.structured_candidate_profiles
for each row
execute function
    public.civora_set_updated_at();


-- ============================================================
-- 5. Validate candidate profile -> source CV ownership
-- ============================================================

create or replace function
    public.validate_candidate_profile_cv_link()
returns trigger
language plpgsql
as $$
declare
    cv_user_id uuid;
begin
    select
        user_id
    into
        cv_user_id
    from public.user_cvs
    where id = new.user_cv_id;

    if not found then
        raise exception
            'user_cv_id % bestaat niet',
            new.user_cv_id;
    end if;

    if cv_user_id <> new.user_id then
        raise exception
            'Candidate profile user_id komt niet overeen met het bron-CV';
    end if;

    return new;
end;
$$;


create trigger
    validate_candidate_profile_cv_link_trigger
before insert or update
on public.structured_candidate_profiles
for each row
execute function
    public.validate_candidate_profile_cv_link();


-- ============================================================
-- 6. Admin document templates
-- ============================================================

create table
    public.document_templates
(
    id uuid
        primary key
        default gen_random_uuid(),

    template_type
        public.civora_template_type
        not null,

    name text
        not null,

    version integer
        not null,

    status
        public.civora_template_status
        not null
        default 'draft',

    storage_bucket text
        not null
        default 'document-templates',

    storage_path text
        not null,

    original_filename text
        not null,

    mime_type text
        not null,

    file_size_bytes bigint
        not null,

    sha256 text
        not null,

    created_by uuid
        references public.profiles(id)
        on delete set null,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint document_templates_type_version_unique
        unique (
            template_type,
            version
        ),

    constraint document_templates_name_not_blank
        check (
            length(
                btrim(
                    name
                )
            ) > 0
        ),

    constraint document_templates_version_valid
        check (
            version >= 1
        ),

    constraint document_templates_storage_bucket_valid
        check (
            storage_bucket
                = 'document-templates'
        ),

    constraint document_templates_storage_path_not_blank
        check (
            length(
                btrim(
                    storage_path
                )
            ) > 0
        ),

    constraint document_templates_filename_not_blank
        check (
            length(
                btrim(
                    original_filename
                )
            ) > 0
        ),

    constraint document_templates_mime_type_valid
        check (
            mime_type
                = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ),

    constraint document_templates_file_size_valid
        check (
            file_size_bytes > 0
            and file_size_bytes <= 5242880
        ),

    constraint document_templates_sha256_valid
        check (
            sha256
                ~ '^[0-9a-fA-F]{64}$'
        )
);


create unique index
    document_templates_storage_path_unique
on public.document_templates (
    storage_path
);


create unique index
    document_templates_one_active_per_type
on public.document_templates (
    template_type
)
where status = 'active';


create index
    document_templates_type_status_idx
on public.document_templates (
    template_type,
    status
);


create trigger
    document_templates_set_updated_at
before update
on public.document_templates
for each row
execute function
    public.civora_set_updated_at();


-- ============================================================
-- 7. Application packages
-- ============================================================

create table
    public.application_packages
(
    id uuid
        primary key
        default gen_random_uuid(),

    user_id uuid
        not null
        references public.profiles(id)
        on delete cascade,

    structured_opportunity_id uuid
        not null
        references public.structured_opportunities(id)
        on delete restrict,

    status
        public.civora_application_package_status
        not null
        default 'draft',

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint application_packages_user_opportunity_unique
        unique (
            user_id,
            structured_opportunity_id
        )
);


create index
    application_packages_user_id_idx
on public.application_packages (
    user_id
);


create index
    application_packages_opportunity_id_idx
on public.application_packages (
    structured_opportunity_id
);


create index
    application_packages_status_idx
on public.application_packages (
    status
);


create trigger
    application_packages_set_updated_at
before update
on public.application_packages
for each row
execute function
    public.civora_set_updated_at();


-- ============================================================
-- 8. Application generation runs
-- ============================================================

create table
    public.application_generation_runs
(
    id uuid
        primary key
        default gen_random_uuid(),

    application_package_id uuid
        not null
        references public.application_packages(id)
        on delete cascade,

    user_id uuid
        not null
        references public.profiles(id)
        on delete cascade,

    structured_opportunity_id uuid
        not null
        references public.structured_opportunities(id)
        on delete restrict,

    user_cv_id uuid
        not null
        references public.user_cvs(id)
        on delete restrict,

    candidate_profile_id uuid
        not null
        references public.structured_candidate_profiles(id)
        on delete restrict,

    motivation_template_id uuid
        not null
        references public.document_templates(id)
        on delete restrict,

    cv_template_id uuid
        not null
        references public.document_templates(id)
        on delete restrict,

    status
        public.civora_generation_run_status
        not null
        default 'pending',

    opportunity_snapshot jsonb
        not null,

    match_analysis jsonb,

    motivation_content jsonb,

    cv_content jsonb,

    provider text,

    model_name text,

    match_prompt_version text,

    motivation_prompt_version text,

    cv_prompt_version text,

    input_hash text,

    input_token_count integer,

    output_token_count integer,

    total_token_count integer,

    validation_errors jsonb
        not null
        default '[]'::jsonb,

    error_type text,

    error_message text,

    started_at timestamptz
        not null
        default now(),

    completed_at timestamptz,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint application_generation_runs_snapshot_object
        check (
            jsonb_typeof(
                opportunity_snapshot
            ) = 'object'
        ),

    constraint application_generation_runs_match_analysis_object
        check (
            match_analysis is null
            or jsonb_typeof(
                match_analysis
            ) = 'object'
        ),

    constraint application_generation_runs_motivation_content_object
        check (
            motivation_content is null
            or jsonb_typeof(
                motivation_content
            ) = 'object'
        ),

    constraint application_generation_runs_cv_content_object
        check (
            cv_content is null
            or jsonb_typeof(
                cv_content
            ) = 'object'
        ),

    constraint application_generation_runs_validation_errors_array
        check (
            jsonb_typeof(
                validation_errors
            ) = 'array'
        ),

    constraint application_generation_runs_input_hash_valid
        check (
            input_hash is null
            or input_hash
                ~ '^[0-9a-fA-F]{64}$'
        ),

    constraint application_generation_runs_input_tokens_valid
        check (
            input_token_count is null
            or input_token_count >= 0
        ),

    constraint application_generation_runs_output_tokens_valid
        check (
            output_token_count is null
            or output_token_count >= 0
        ),

    constraint application_generation_runs_total_tokens_valid
        check (
            total_token_count is null
            or total_token_count >= 0
        ),

    constraint application_generation_runs_completed_status_valid
        check (
            status not in (
                'ready',
                'failed'
            )
            or completed_at is not null
        )
);


create index
    application_generation_runs_package_created_idx
on public.application_generation_runs (
    application_package_id,
    created_at desc
);


create index
    application_generation_runs_user_created_idx
on public.application_generation_runs (
    user_id,
    created_at desc
);


create index
    application_generation_runs_opportunity_idx
on public.application_generation_runs (
    structured_opportunity_id
);


create index
    application_generation_runs_status_idx
on public.application_generation_runs (
    status
);


create trigger
    application_generation_runs_set_updated_at
before update
on public.application_generation_runs
for each row
execute function
    public.civora_set_updated_at();


-- ============================================================
-- 9. Validate generation run relationships
-- ============================================================

create or replace function
    public.validate_application_generation_run_links()
returns trigger
language plpgsql
as $$
declare
    package_user_id uuid;
    package_opportunity_id uuid;

    cv_user_id uuid;

    profile_user_id uuid;
    profile_cv_id uuid;

    motivation_type
        public.civora_template_type;

    cv_type
        public.civora_template_type;
begin
    select
        user_id,
        structured_opportunity_id
    into
        package_user_id,
        package_opportunity_id
    from public.application_packages
    where id = new.application_package_id;

    if not found then
        raise exception
            'application_package_id % bestaat niet',
            new.application_package_id;
    end if;

    if package_user_id <> new.user_id then
        raise exception
            'Generation run user_id komt niet overeen met application package';
    end if;

    if (
        package_opportunity_id
        <> new.structured_opportunity_id
    ) then
        raise exception
            'Generation run opportunity komt niet overeen met application package';
    end if;


    select
        user_id
    into
        cv_user_id
    from public.user_cvs
    where id = new.user_cv_id;

    if not found then
        raise exception
            'user_cv_id % bestaat niet',
            new.user_cv_id;
    end if;

    if cv_user_id <> new.user_id then
        raise exception
            'Generation run CV is niet van dezelfde gebruiker';
    end if;


    select
        user_id,
        user_cv_id
    into
        profile_user_id,
        profile_cv_id
    from public.structured_candidate_profiles
    where id = new.candidate_profile_id;

    if not found then
        raise exception
            'candidate_profile_id % bestaat niet',
            new.candidate_profile_id;
    end if;

    if profile_user_id <> new.user_id then
        raise exception
            'Candidate profile is niet van dezelfde gebruiker';
    end if;

    if profile_cv_id <> new.user_cv_id then
        raise exception
            'Candidate profile hoort niet bij het geselecteerde CV';
    end if;


    select
        template_type
    into
        motivation_type
    from public.document_templates
    where id = new.motivation_template_id;

    if not found then
        raise exception
            'motivation_template_id % bestaat niet',
            new.motivation_template_id;
    end if;

    if motivation_type <> 'motivation_letter' then
        raise exception
            'motivation_template_id moet een motivation_letter-template zijn';
    end if;


    select
        template_type
    into
        cv_type
    from public.document_templates
    where id = new.cv_template_id;

    if not found then
        raise exception
            'cv_template_id % bestaat niet',
            new.cv_template_id;
    end if;

    if cv_type <> 'cv' then
        raise exception
            'cv_template_id moet een cv-template zijn';
    end if;


    return new;
end;
$$;


create trigger
    validate_application_generation_run_links_trigger
before insert or update
on public.application_generation_runs
for each row
execute function
    public.validate_application_generation_run_links();


-- ============================================================
-- 10. Generated application documents
-- ============================================================

create table
    public.generated_application_documents
(
    id uuid
        primary key
        default gen_random_uuid(),

    generation_run_id uuid
        not null
        references public.application_generation_runs(id)
        on delete cascade,

    application_package_id uuid
        not null
        references public.application_packages(id)
        on delete cascade,

    user_id uuid
        not null
        references public.profiles(id)
        on delete cascade,

    document_type
        public.civora_generated_document_type
        not null,

    status
        public.civora_generated_document_status
        not null
        default 'pending',

    storage_bucket text
        not null
        default 'generated-application-documents',

    storage_path text,

    filename text,

    mime_type text,

    file_size_bytes bigint,

    sha256 text,

    error_message text,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint generated_application_documents_run_type_unique
        unique (
            generation_run_id,
            document_type
        ),

    constraint generated_application_documents_storage_bucket_valid
        check (
            storage_bucket
                = 'generated-application-documents'
        ),

    constraint generated_application_documents_storage_path_valid
        check (
            storage_path is null
            or length(
                btrim(
                    storage_path
                )
            ) > 0
        ),

    constraint generated_application_documents_filename_valid
        check (
            filename is null
            or length(
                btrim(
                    filename
                )
            ) > 0
        ),

    constraint generated_application_documents_mime_type_valid
        check (
            mime_type is null
            or mime_type
                = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ),

    constraint generated_application_documents_file_size_valid
        check (
            file_size_bytes is null
            or (
                file_size_bytes > 0
                and file_size_bytes <= 10485760
            )
        ),

    constraint generated_application_documents_sha256_valid
        check (
            sha256 is null
            or sha256
                ~ '^[0-9a-fA-F]{64}$'
        ),

    constraint generated_application_documents_ready_requires_file
        check (
            status <> 'ready'
            or (
                storage_path is not null
                and filename is not null
                and mime_type is not null
                and file_size_bytes is not null
                and sha256 is not null
            )
        )
);


create unique index
    generated_application_documents_storage_path_unique
on public.generated_application_documents (
    storage_path
)
where storage_path is not null;


create index
    generated_application_documents_user_id_idx
on public.generated_application_documents (
    user_id
);


create index
    generated_application_documents_package_id_idx
on public.generated_application_documents (
    application_package_id
);


create index
    generated_application_documents_run_id_idx
on public.generated_application_documents (
    generation_run_id
);


create index
    generated_application_documents_status_idx
on public.generated_application_documents (
    status
);


create trigger
    generated_application_documents_set_updated_at
before update
on public.generated_application_documents
for each row
execute function
    public.civora_set_updated_at();


-- ============================================================
-- 11. Validate generated document relationships
-- ============================================================

create or replace function
    public.validate_generated_application_document_links()
returns trigger
language plpgsql
as $$
declare
    run_user_id uuid;
    run_package_id uuid;
begin
    select
        user_id,
        application_package_id
    into
        run_user_id,
        run_package_id
    from public.application_generation_runs
    where id = new.generation_run_id;

    if not found then
        raise exception
            'generation_run_id % bestaat niet',
            new.generation_run_id;
    end if;

    if run_user_id <> new.user_id then
        raise exception
            'Generated document user_id komt niet overeen met generation run';
    end if;

    if (
        run_package_id
        <> new.application_package_id
    ) then
        raise exception
            'Generated document application package komt niet overeen met generation run';
    end if;

    return new;
end;
$$;


create trigger
    validate_generated_application_document_links_trigger
before insert or update
on public.generated_application_documents
for each row
execute function
    public.validate_generated_application_document_links();


-- ============================================================
-- 12. RLS
-- Browser krijgt geen directe toegang.
-- Backend gebruikt service_role.
-- ============================================================

alter table
    public.user_cvs
enable row level security;

alter table
    public.structured_candidate_profiles
enable row level security;

alter table
    public.document_templates
enable row level security;

alter table
    public.application_packages
enable row level security;

alter table
    public.application_generation_runs
enable row level security;

alter table
    public.generated_application_documents
enable row level security;


revoke all
on public.user_cvs
from anon, authenticated;

revoke all
on public.structured_candidate_profiles
from anon, authenticated;

revoke all
on public.document_templates
from anon, authenticated;

revoke all
on public.application_packages
from anon, authenticated;

revoke all
on public.application_generation_runs
from anon, authenticated;

revoke all
on public.generated_application_documents
from anon, authenticated;


grant
    select,
    insert,
    update,
    delete
on public.user_cvs
to service_role;

grant
    select,
    insert,
    update,
    delete
on public.structured_candidate_profiles
to service_role;

grant
    select,
    insert,
    update,
    delete
on public.document_templates
to service_role;

grant
    select,
    insert,
    update,
    delete
on public.application_packages
to service_role;

grant
    select,
    insert,
    update,
    delete
on public.application_generation_runs
to service_role;

grant
    select,
    insert,
    update,
    delete
on public.generated_application_documents
to service_role;


-- ============================================================
-- 13. Private Supabase Storage buckets
-- ============================================================

insert into storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
values (
    'user-cvs',
    'user-cvs',
    false,
    10485760,
    array[
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]::text[]
)
on conflict (id)
do update set
    name = excluded.name,
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;


insert into storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
values (
    'document-templates',
    'document-templates',
    false,
    5242880,
    array[
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]::text[]
)
on conflict (id)
do update set
    name = excluded.name,
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;


insert into storage.buckets (
    id,
    name,
    public,
    file_size_limit,
    allowed_mime_types
)
values (
    'generated-application-documents',
    'generated-application-documents',
    false,
    10485760,
    array[
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]::text[]
)
on conflict (id)
do update set
    name = excluded.name,
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;


commit;