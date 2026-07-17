-- ============================================================
-- Voeg een inhoudelijke hash toe naast de exacte HTML-hash.
-- Bestaande records blijven geldig doordat de nieuwe kolommen
-- voorlopig nullable zijn.
-- ============================================================


alter table public.raw_opportunities
add column if not exists normalized_content_hash text;


alter table public.raw_opportunity_versions
add column if not exists normalized_content_hash text;


do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'raw_opportunities_normalized_hash_length'
    ) then
        alter table public.raw_opportunities
        add constraint raw_opportunities_normalized_hash_length
        check (
            normalized_content_hash is null
            or length(normalized_content_hash) = 64
        );
    end if;
end;
$$;


do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'raw_versions_normalized_hash_length'
    ) then
        alter table public.raw_opportunity_versions
        add constraint raw_versions_normalized_hash_length
        check (
            normalized_content_hash is null
            or length(normalized_content_hash) = 64
        );
    end if;
end;
$$;


create index if not exists
raw_opportunities_normalized_content_hash_idx
on public.raw_opportunities(normalized_content_hash);


create index if not exists
raw_versions_normalized_content_hash_idx
on public.raw_opportunity_versions(normalized_content_hash);