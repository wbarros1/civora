begin;


-- ============================================================
-- Civora C2
-- Active user CV switching
-- ============================================================

create or replace function
    public.activate_user_cv(
        p_user_id uuid,
        p_user_cv_id uuid
    )
returns uuid
language plpgsql
security definer
set search_path = public
as $$
begin
    -- Serializeer gelijktijdige CV-wijzigingen
    -- voor dezelfde gebruiker.
    perform 1
    from public.profiles
    where id = p_user_id
    for update;

    if not found then
        raise exception
            'Gebruiker % bestaat niet',
            p_user_id;
    end if;


    -- Controleer expliciet dat het nieuwe CV
    -- daadwerkelijk van deze gebruiker is.
    perform 1
    from public.user_cvs
    where
        id = p_user_cv_id
        and user_id = p_user_id;

    if not found then
        raise exception
            'CV % behoort niet tot gebruiker %',
            p_user_cv_id,
            p_user_id;
    end if;


    -- Eerst huidig actief CV uitzetten.
    update public.user_cvs
    set is_active = false
    where
        user_id = p_user_id
        and is_active = true
        and id <> p_user_cv_id;


    -- Daarna het nieuwe CV activeren.
    update public.user_cvs
    set is_active = true
    where
        id = p_user_cv_id
        and user_id = p_user_id;


    return p_user_cv_id;
end;
$$;


revoke all
on function public.activate_user_cv(
    uuid,
    uuid
)
from public, anon, authenticated;


grant execute
on function public.activate_user_cv(
    uuid,
    uuid
)
to service_role;


commit;