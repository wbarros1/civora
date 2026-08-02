alter table public.structured_opportunities
add column if not exists application_status text
not null default 'unknown';

alter table public.structured_opportunities
drop constraint if exists
structured_opportunities_application_status_check;

alter table public.structured_opportunities
add constraint
structured_opportunities_application_status_check
check (
    application_status in (
        'open',
        'expired',
        'closed',
        'unknown'
    )
);

create index if not exists
    idx_structured_opportunities_application_status
on public.structured_opportunities (
    application_status
);