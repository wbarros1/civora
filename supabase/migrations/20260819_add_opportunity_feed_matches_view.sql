-- ============================================================
-- Civora personalised opportunity feed
-- ============================================================

create or replace view
    public.opportunity_feed_matches
with (
    security_invoker = true
)
as
select
    so.id,
    so.source_reference,
    so.title,
    so.client_name,
    so.location,
    so.province,
    so.work_arrangement,
    so.start_date,
    so.end_date,
    so.application_deadline,
    so.hours_per_week_min,
    so.hours_per_week_max,
    so.rate_min,
    so.rate_max,
    so.rate_currency,
    so.rate_period,
    so.employment_relationship,
    so.source_status,
    so.application_status,

    oc.primary_vakgroep,
    oc.classification_confidence,
    oc.classifier_version,

    ovs.vakgroep as matched_vakgroep,
    ovs.relevance_score

from
    public.opportunity_vakgroep_scores ovs

join public.opportunity_classifications oc
    on oc.id = ovs.classification_id

join public.structured_opportunities so
    on so.id = oc.structured_opportunity_id

where
    so.source_status = 'active'
    and ovs.relevance_score
        >= oc.relevance_threshold;


revoke all
on public.opportunity_feed_matches
from
    anon,
    authenticated;


grant select
on public.opportunity_feed_matches
to service_role;