# @gaia-registry/api-client

TypeScript/JavaScript client for the [Gaia Registry API](https://gaiaskilltree.com/api/v1/health.json).

**Zero runtime dependencies.** Uses native `fetch` (Node 18+, all modern browsers).

## Installation

```bash
npm install @gaia-registry/api-client
```

## Quick Start

```typescript
import { GaiaClient } from '@gaia-registry/api-client';

const gaia = new GaiaClient();

// Health check
const health = await gaia.getHealth();
console.log(`Registry v${health.version} — ${health.namedSkillsCount} named skills`);

// List skills (paginated)
const page1 = await gaia.listSkills();
console.log(`Page 1 of ${page1.totalPages} (${page1.totalSkills} total)`);

// Get a specific skill
const skill = await gaia.getSkill('garrytan', 'gstack');
console.log(`${skill.name} — ${skill.overallTrustGrade} grade, TM=${skill.trustMagnitude}`);

// List contributors
const { contributors } = await gaia.listContributors();
console.log(`Top contributor: ${contributors[0].handle} (prestige: ${contributors[0].prestigeScore})`);

// Leaderboard
const leaderboard = await gaia.getLeaderboard();
console.log(`Grade distribution:`, leaderboard.distribution);

// Search index (for client-side search)
const searchIndex = await gaia.getSearchIndex();
const results = searchIndex.filter(entry =>
  entry.tokens.some(t => t.includes('agent'))
);
```

## Configuration

```typescript
const gaia = new GaiaClient({
  // Custom base URL (for local development or mirrors)
  baseUrl: 'http://localhost:8080',
  // Custom fetch (for testing or special environments)
  fetch: customFetchImplementation,
});
```

## API Methods

| Method | Endpoint | Returns |
|--------|----------|---------|
| `getHealth()` | `/api/v1/health.json` | `Health` |
| `listSkills(page?)` | `/api/v1/skills/index.json` | `SkillListPage` |
| `getSkill(contributor, skill)` | `/api/v1/skills/{c}/{s}.json` | `SkillDetail` |
| `listContributors()` | `/api/v1/contributors/index.json` | `ContributorList` |
| `getContributor(handle)` | `/api/v1/contributors/{h}.json` | `ContributorDetail` |
| `getLeaderboard()` | `/api/v1/leaderboard.json` | `Leaderboard` |
| `getEvidenceTypes()` | `/api/v1/evidence-types.json` | `EvidenceTypeCatalogue` |
| `getSearchIndex()` | `/api/v1/search-index.json` | `SearchIndex` |
| `getTrending(window)` | `/api/v1/trending/{window}.json` | `Trending` |
| `getHeroes()` | `/api/v1/heroes.json` | `Heroes` |

## Error Handling

```typescript
import { GaiaClient, GaiaApiError } from '@gaia-registry/api-client';

const gaia = new GaiaClient();

try {
  const skill = await gaia.getSkill('nobody', 'nonexistent');
} catch (err) {
  if (err instanceof GaiaApiError) {
    console.error(`API error: ${err.status} at ${err.url}`);
  }
}
```

## Requirements

- Node.js 18+ (native `fetch`) or any modern browser
- ESM and CJS builds included

## License

MIT
