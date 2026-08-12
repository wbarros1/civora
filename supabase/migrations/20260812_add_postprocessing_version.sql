alter table public.opportunity_extraction_runs
add column postprocessing_version text;

update public.opportunity_extraction_runs
set postprocessing_version = 'legacy-pre-v1'
where postprocessing_version is null;

alter table public.opportunity_extraction_runs
alter column postprocessing_version set not null;

alter table public.opportunity_extraction_runs
add constraint opportunity_extraction_runs_postprocessing_version_not_blank
check (
    length(trim(postprocessing_version)) > 0
);

comment on column public.opportunity_extraction_runs.postprocessing_version
is 'Version of deterministic postprocessing applied after LLM extraction.';