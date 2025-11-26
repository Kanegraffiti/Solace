# Solace Web

A local-only web layer for browsing and managing Solace journals and training snippets.

## Services

- **API**: FastAPI server in `web/api/main.py` that reuses the existing Solace configuration for password/encryption. The API is meant to run on localhost and refuses unauthenticated requests.
- **Frontend**: React + Vite client in `web/frontend` for diary browsing, tag filtering, snippet management, and exports.

## Running locally

```bash
make dev
```

`make dev` starts both the API (default `localhost:8000`) and Vite dev server (default `localhost:4173`) with hot reload. The stack is local-only—keep both processes bound to loopback or behind a firewall.

## Build

```bash
cd web/frontend
npm install
npm run build
```

The build artifacts are emitted to `web/frontend/dist`.
