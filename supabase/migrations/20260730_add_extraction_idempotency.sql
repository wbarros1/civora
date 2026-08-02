alter table public.opportunity_extraction_runs
add column if not exists idempotency_key text;

create unique index if not exists
    idx_opportunity_extraction_runs_idempotency_key
on public.opportunity_extraction_runs (
    idempotency_key
)
where idempotency_key is not null;  