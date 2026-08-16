-- ============================================================
-- Civora user profiles
-- ============================================================


-- ------------------------------------------------------------
-- Enums
-- ------------------------------------------------------------

create type public.user_role as enum (
    'user',
    'admin'
);


create type public.vakgroep as enum (
    'procesmanagement',
    'data_ai',
    'ict',
    'finance'
);


-- ------------------------------------------------------------
-- Profiles
-- ------------------------------------------------------------

create table public.profiles (
    id uuid primary key
        references auth.users(id)
        on delete cascade,

    full_name text not null,

    role public.user_role
        not null
        default 'user',

    vakgroep public.vakgroep
        not null,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint profiles_full_name_not_blank
        check (
            length(
                trim(full_name)
            ) > 0
        )
);


comment on table public.profiles is
'Application profile for a Civora authenticated user.';


comment on column public.profiles.role is
'Application role. New users always start as user.';


comment on column public.profiles.vakgroep is
'Primary Civora discipline selected by the user.';


-- ------------------------------------------------------------
-- Automatically create profile after signup
-- ------------------------------------------------------------

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
    profile_full_name text;
    profile_vakgroep public.vakgroep;
begin
    profile_full_name := trim(
        coalesce(
            new.raw_user_meta_data
                ->> 'full_name',
            ''
        )
    );

    if profile_full_name = '' then
        raise exception
            'full_name is required';
    end if;


    begin
        profile_vakgroep := (
            new.raw_user_meta_data
                ->> 'vakgroep'
        )::public.vakgroep;

    exception
        when invalid_text_representation then
            raise exception
                'invalid vakgroep';
    end;


    if profile_vakgroep is null then
        raise exception
            'vakgroep is required';
    end if;


    insert into public.profiles (
        id,
        full_name,
        role,
        vakgroep
    )
    values (
        new.id,
        profile_full_name,
        'user',
        profile_vakgroep
    );

    return new;
end;
$$;


create trigger on_auth_user_created
    after insert
    on auth.users
    for each row
    execute procedure public.handle_new_user();


-- ------------------------------------------------------------
-- Keep updated_at current
-- ------------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();

    return new;
end;
$$;


create trigger profiles_set_updated_at
    before update
    on public.profiles
    for each row
    execute procedure public.set_updated_at();


-- ------------------------------------------------------------
-- Permissions
-- ------------------------------------------------------------

revoke all
on public.profiles
from anon;


grant select, update
on public.profiles
to authenticated;


-- ------------------------------------------------------------
-- Row Level Security
-- ------------------------------------------------------------

alter table public.profiles
enable row level security;


create policy
    "Users can read own profile"
on public.profiles
for select
to authenticated
using (
    id = (
        select auth.uid()
    )
);


create policy
    "Users can update own profile"
on public.profiles
for update
to authenticated
using (
    id = (
        select auth.uid()
    )
)
with check (
    id = (
        select auth.uid()
    )
);

-- ------------------------------------------------------------
-- Users may never promote themselves to admin
-- ------------------------------------------------------------

create or replace function public.protect_profile_role()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if new.role is distinct from old.role then
        raise exception
            'profile role cannot be changed by the user';
    end if;

    return new;
end;
$$;


create trigger profiles_protect_role
    before update
    on public.profiles
    for each row
    execute procedure public.protect_profile_role();