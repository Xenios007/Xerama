# Xerama Studio (frontend)

The Xerama web studio shell (MODULE-055) - an API client for the backend
in `../src/xerama`, never a second business-logic implementation. Every
page reads/writes exclusively through `src/api/client.ts`; no page calls
an AI provider or touches the filesystem directly.

## Stack (current stable, chosen for MODULE-055)

- **React 19 + TypeScript** - the stack already used as a research
  reference for this class of production tool (see
  `research/WIND_COMIC_DEEP_DIVE.md`).
- **Vite** - the standard lean build tool for a TypeScript SPA; this is
  an internal production studio, not a public/SEO-facing site, so a
  full Next.js SSR framework would add complexity with no benefit here.
- **React Router v7** (`createBrowserRouter`) - routing; `src/router.tsx`
  exports the route tree separately from the router instance so tests
  can build a `MemoryRouter` from the exact same routes.
- **TanStack Query v5** - the state/query strategy: every page reads
  server state through the hooks in `src/api/queries.ts`, never raw
  `fetch` calls scattered through components. Polling (`refetchInterval`)
  is used for job/observability data per MODULE-054's "support polling
  first."
- **Vitest + Testing Library** - unit/component tests with mocked
  `fetch` (`src/test/*.test.tsx`); **oxlint** for lint; `tsc -b` for the
  type check.

## Design system

`src/components/ui/` - `Button`, `Card`, `LoadingSpinner`, `ErrorBanner`,
and `QueryState` (the one loading/error pattern every page wraps a
TanStack Query result in). `src/components/layout/AppShell.tsx` is the
nav shell that hosts every studio page (modules 056-060).

## Setup

```bash
npm install
cp .env.example .env   # set VITE_API_BASE_URL if not http://localhost:8000
npm run dev            # http://localhost:5173
```

The backend's `CORS_ALLOWED_ORIGINS` env var must include this dev
server's origin (defaults to `http://localhost:5173` already) - see
`../.env.example`.

## Checks

```bash
npm run typecheck
npm test
npm run lint
npm run build
```
