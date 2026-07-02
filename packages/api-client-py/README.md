# gaia-registry-client

Python client for the [Gaia Registry API](https://gaia.tiongson.co/api/v1/health.json).

Provides both **synchronous** and **asynchronous** typed HTTP clients.

## Installation

```bash
pip install gaia-registry-client
```

## Quick Start

### Synchronous

```python
from gaia_registry_client import GaiaClient

client = GaiaClient()

# Health check
health = client.get_health()
print(f"Registry v{health.version} — {health.named_skills_count} named skills")

# List skills (paginated)
page1 = client.list_skills()
print(f"Page 1 of {page1.total_pages} ({page1.total_skills} total)")

# Get a specific skill
skill = client.get_skill("garrytan", "gstack")
print(f"{skill.name} — {skill.overall_trust_grade} grade, TM={skill.trust_magnitude}")

# List contributors
contributors = client.list_contributors()
print(f"Top: {contributors.contributors[0].handle}")

# Context manager (auto-closes connection)
with GaiaClient() as client:
    leaderboard = client.get_leaderboard()
    print(f"Total graded: {leaderboard.distribution.total}")
```

### Asynchronous

```python
import asyncio
from gaia_registry_client import AsyncGaiaClient

async def main():
    async with AsyncGaiaClient() as client:
        health = await client.get_health()
        print(f"Registry v{health.version}")

        # Fetch multiple endpoints concurrently
        skills, contributors = await asyncio.gather(
            client.list_skills(),
            client.list_contributors(),
        )
        print(f"{skills.total_skills} skills, {len(contributors.contributors)} contributors")

asyncio.run(main())
```

## Configuration

```python
# Custom base URL (for local development or mirrors)
client = GaiaClient(base_url="http://localhost:8080")

# Custom timeout
client = GaiaClient(timeout=10.0)

# Bring your own httpx client
import httpx
transport = httpx.HTTPTransport(retries=3)
http_client = httpx.Client(transport=transport)
client = GaiaClient(client=http_client)
```

## API Methods

| Method | Endpoint | Returns |
|--------|----------|---------|
| `get_health()` | `/api/v1/health.json` | `Health` |
| `list_skills(page=1)` | `/api/v1/skills/index.json` | `SkillListPage` |
| `get_skill(contributor, skill)` | `/api/v1/skills/{c}/{s}.json` | `SkillDetail` |
| `list_contributors()` | `/api/v1/contributors/index.json` | `ContributorList` |
| `get_contributor(handle)` | `/api/v1/contributors/{h}.json` | `ContributorDetail` |
| `get_leaderboard()` | `/api/v1/leaderboard.json` | `Leaderboard` |
| `get_evidence_types()` | `/api/v1/evidence-types.json` | `EvidenceTypeCatalogue` |
| `get_search_index()` | `/api/v1/search-index.json` | `SearchIndex` |
| `get_trending(window)` | `/api/v1/trending/{window}.json` | `Trending` |
| `get_heroes()` | `/api/v1/heroes.json` | `Heroes` |

## Error Handling

```python
from gaia_registry_client import GaiaClient
from gaia_registry_client.client import GaiaApiError

client = GaiaClient()

try:
    skill = client.get_skill("nobody", "nonexistent")
except GaiaApiError as e:
    print(f"API error: {e.status_code} at {e.url}")
```

## Requirements

- Python 3.10+
- httpx (only runtime dependency)

## License

MIT
