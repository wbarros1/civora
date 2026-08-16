create or replace function public.protect_profile_role()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
    if
        auth.uid() is not null
        and new.role is distinct from old.role
    then
        raise exception
            'profile role cannot be changed by the user';
    end if;

    return new;
end;
$$;