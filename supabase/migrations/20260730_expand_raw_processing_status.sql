begin;

alter table public.raw_opportunities
drop constraint if exists
raw_opportunities_processing_status_check;

alter table public.raw_opportunities
add constraint
raw_opportunities_processing_status_check
check (
    processing_status in (
        'pending',
        'processing',
        'processed',
        'review_required',
        'failed'
    )
);

commit;