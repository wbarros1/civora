-- ============================================================
-- Civora saved searches
-- ============================================================


create table public.saved_searches (
    id uuid primary key
        default gen_random_uuid(),

    user_id uuid not null
        references auth.users(id)
        on delete cascade,

    name text not null,

    filters jsonb not null
        default '{}'::jsonb,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint saved_searches_name_not_blank
        check (
            length(
                trim(name)
            ) > 0
        ),

    constraint saved_searches_filters_is_object
        check (
            jsonb_typeof(filters)
            = 'object'
        ),

    constraint saved_searches_unique_name_per_user
        unique (
            user_id,
            name
        )
);


create index
    saved_searches_user_id_idx
on public.saved_searches (
    user_id
);


comment on table public.saved_searches is
'Saved Civora opportunity search filters per authenticated user.';


-- ------------------------------------------------------------
-- updated_at
-- ------------------------------------------------------------

create trigger saved_searches_set_updated_at
    before update
    on public.saved_searches
    for each row
    execute procedure public.set_updated_at();


-- ------------------------------------------------------------
-- Permissions
-- ------------------------------------------------------------

revoke all
on public.saved_searches
from anon;


grant
    select,
    insert,
    update,
    delete
on public.saved_searches
to authenticated;


-- ------------------------------------------------------------
-- Row Level Security
-- ------------------------------------------------------------

alter table public.saved_searches
enable row level security;


create policy
    "Users can read own saved searches"
on public.saved_searches
for select
to authenticated
using (
    user_id = (
        select auth.uid()
    )
);


create policy
    "Users can create own saved searches"
on public.saved_searches
for insert
to authenticated
with check (
    user_id = (
        select auth.uid()
    )
);


create policy
    "Users can update own saved searches"
on public.saved_searches
for update
to authenticated
using (
    user_id = (
        select auth.uid()
    )
)
with check (
    user_id = (
        select auth.uid()
    )
);


create policy
    "Users can delete own saved searches"
on public.saved_searches
for delete
to authenticated
using (
    user_id = (
        select auth.uid()
    )
);