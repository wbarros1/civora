-- Configuratie voor de eerste Flextender-connector.

update public.sources
set configuration =
    configuration
    || jsonb_build_object(
        'listing_urls',
        jsonb_build_array(
            'https://www.flextender.nl/opdrachten/',
            'https://www.flextender.nl/'
        ),
        'allowed_hosts',
        jsonb_build_array(
            'www.flextender.nl',
            'flextender.nl',
            'app.flextender.nl'
        ),
        'request_delay_seconds',
        1.0
    )
where code = 'flextender';