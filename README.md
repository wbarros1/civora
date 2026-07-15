# Public Inhuur Platform

Een webapp voor het verzamelen, structureren, doorzoeken en gericht distribueren van openbare publieke inhuuropdrachten.

## Eerste databronnen

- Flextender
- Inhuurdesk
- TenderNed API/RSS

## Techniek

- Python
- Supabase
- LLM-extractie
- Webfrontend

## Projectstructuur

- `backend/app/connectors`: ophalen van brongegevens
- `backend/app/extraction`: LLM-extractie
- `backend/app/database`: Supabase-integratie
- `backend/app/api`: backend-API
- `backend/tests`: geautomatiseerde tests
- `frontend`: toekomstige frontend
- `docs`: documentatie

## Virtuele omgeving activeren

### macOS/Linux

```bash
source .venv/bin/activate
```
