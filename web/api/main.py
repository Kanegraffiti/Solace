"""FastAPI service exposing Solace journal and training data locally.

This API is intended for *local* use only. Authentication piggybacks on the
existing Solace password/encryption flow so the server never invents its own
remote identity system. The frontend is expected to run on the same machine
and call the API directly.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from typing import Dict, List

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from journal import ENTRY_TYPES, add_entry, export_entries, load_entries
from solace.configuration import (
    CONFIG_PATH,
    STORAGE_DIR,
    get_cipher,
    is_password_enabled,
    load_config,
)
from trainer import load_index, query, rebuild_index, teach

LOCAL_ONLY_NOTICE = (
    "Local-only Solace API. Do not expose this service to networks you do not"
    " trust."
)

CONFIG = load_config()


class LoginRequest(BaseModel):
    password: str | None = None


class LoginResponse(BaseModel):
    token: str
    local_only: str
    requires_password: bool


class EntryRequest(BaseModel):
    content: str
    entry_type: str
    tags: List[str] | None = None


class EntryResponse(BaseModel):
    identifier: str
    entry_type: str
    timestamp: str
    date: str
    time: str
    content: str
    tags: List[str]
    encrypted: bool


class SnippetRequest(BaseModel):
    language: str
    text: str
    category: str = "example"
    source: str | None = None


class SnippetResponse(BaseModel):
    language: str
    category: str
    text: str
    source: str


class ExportResponse(BaseModel):
    path: str
    format: str


class AuthContext(BaseModel):
    token: str
    created_at: float
    cipher: object | None = None
    password_used: str | None = None


class AuthManager:
    """Very small in-memory token store for local-only sessions."""

    def __init__(self) -> None:
        self.sessions: Dict[str, AuthContext] = {}

    def login(self, password: str | None) -> AuthContext:
        security = CONFIG.get("security", {})
        if is_password_enabled(CONFIG):
            hashed = hashlib.sha256((password or "").encode("utf-8")).hexdigest()
            expected = security.get("password_hash") or ""
            if hashed != expected:
                raise HTTPException(status_code=401, detail="Invalid password")
        cipher = None
        if security.get("encryption_enabled", True):
            cipher = get_cipher(CONFIG, password=password)
        token = secrets.token_urlsafe(32)
        context = AuthContext(
            token=token,
            created_at=time.time(),
            cipher=cipher,
            password_used=password,
        )
        self.sessions[token] = context
        return context

    def get(self, token: str) -> AuthContext:
        context = self.sessions.get(token)
        if not context:
            raise HTTPException(status_code=401, detail="Missing or expired token")
        return context


auth_manager = AuthManager()

app = FastAPI(title="Solace Web", description=LOCAL_ONLY_NOTICE)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str]:
    return {
        "message": "Solace local API is running",
        "local_only": LOCAL_ONLY_NOTICE,
        "config": str(CONFIG_PATH),
        "storage": str(STORAGE_DIR),
    }


def _get_context(authorization: str = Header(...)) -> AuthContext:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Use Bearer token auth")
    token = authorization.split(" ", 1)[1]
    return auth_manager.get(token)


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    context = auth_manager.login(payload.password)
    return LoginResponse(
        token=context.token,
        local_only=LOCAL_ONLY_NOTICE,
        requires_password=is_password_enabled(CONFIG),
    )


@app.get("/api/entries", response_model=List[EntryResponse])
async def list_entries(tag: str | None = None, context: AuthContext = Depends(_get_context)) -> List[EntryResponse]:
    entries = load_entries(cipher=context.cipher, password=context.password_used)
    filtered = entries
    if tag:
        filtered = [entry for entry in entries if tag in (entry.tags or [])]
    return [EntryResponse(**entry.serialise()) for entry in filtered]


@app.post("/api/entries", response_model=EntryResponse)
async def create_entry(payload: EntryRequest, context: AuthContext = Depends(_get_context)) -> EntryResponse:
    if payload.entry_type not in ENTRY_TYPES:
        raise HTTPException(status_code=400, detail="Unknown entry type")
    entry = add_entry(
        payload.content,
        entry_type=payload.entry_type,
        tags=payload.tags or [],
        cipher=context.cipher,
        password=context.password_used,
    )
    return EntryResponse(**entry.serialise())


@app.get("/api/tags", response_model=List[str])
async def list_tags(context: AuthContext = Depends(_get_context)) -> List[str]:
    entries = load_entries(cipher=context.cipher, password=context.password_used)
    tags = set()
    for entry in entries:
        tags.update(entry.tags or [])
    return sorted(tags)


@app.get("/api/entries/export")
async def export(format: str = "markdown", context: AuthContext = Depends(_get_context)) -> FileResponse:
    timestamp = int(time.time())
    suffix = "md" if format.lower() in {"markdown", "md"} else format.lower()
    destination = STORAGE_DIR / "cache" / f"export-{timestamp}.{suffix}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    export_entries(destination, format=format, cipher=context.cipher, password=context.password_used)
    headers = {"X-Solace-Local": LOCAL_ONLY_NOTICE}
    media_type = "text/markdown" if suffix in {"md", "markdown"} else "application/octet-stream"
    return FileResponse(destination, filename=destination.name, media_type=media_type, headers=headers)


@app.get("/api/snippets", response_model=List[SnippetResponse])
async def list_snippets(language: str | None = None, context: AuthContext = Depends(_get_context)) -> List[SnippetResponse]:
    snippets = load_index()
    results = []
    for snippet in snippets:
        if language and snippet.language != language:
            continue
        results.append(SnippetResponse(**snippet.serialise()))
    return results


@app.get("/api/snippets/search", response_model=List[SnippetResponse])
async def search_snippets(language: str, prompt: str, context: AuthContext = Depends(_get_context)) -> List[SnippetResponse]:
    matches = query(language=language, prompt=prompt)
    return [SnippetResponse(**m.serialise()) for m in matches]


@app.post("/api/snippets", response_model=SnippetResponse)
async def create_snippet(payload: SnippetRequest, context: AuthContext = Depends(_get_context)) -> SnippetResponse:
    snippet = teach(language=payload.language, content=payload.text, category=payload.category)
    source = payload.source or snippet.source
    serialised = snippet.serialise()
    serialised["source"] = source
    return SnippetResponse(**serialised)


@app.post("/api/snippets/rebuild", response_model=List[SnippetResponse])
async def rebuild(context: AuthContext = Depends(_get_context)) -> List[SnippetResponse]:
    snippets = rebuild_index()
    return [SnippetResponse(**s.serialise()) for s in snippets]


@app.get("/api/meta", response_model=Dict[str, str])
async def meta(context: AuthContext = Depends(_get_context)) -> Dict[str, str]:
    return {
        "local_only": LOCAL_ONLY_NOTICE,
        "storage_root": str(STORAGE_DIR),
        "config_path": str(CONFIG_PATH),
        "password_required": str(is_password_enabled(CONFIG)),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.api.main:app", host="0.0.0.0", port=8000, reload=True)
