from __future__ import annotations

import datetime as dt
import ipaddress
import json
import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import pymupdf
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from analysis import analyze_research


app = FastAPI(title="StarlightAI Research Engine", version="3.0.0")


def _frontend_origins() -> list[str]:
    configured = os.getenv("FRONTEND_ORIGIN", "")
    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    return origins or ["http://localhost:5173", "http://127.0.0.1:5173"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_SOURCE_CHARS = 40_000


class ResearchSource(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    text: str | None = Field(default=None, max_length=MAX_SOURCE_CHARS)
    url: str | None = Field(default=None, max_length=2_000)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    sources: list[ResearchSource] = Field(min_length=1, max_length=12)


def _validate_public_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(status_code=422, detail="Source URL must use http or https.")
    if parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="Source URLs cannot contain credentials.")
    try:
        addresses = {
            ipaddress.ip_address(result[4][0])
            for result in socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        }
    except (OSError, ValueError):
        raise HTTPException(status_code=422, detail="The source URL host could not be resolved.") from None
    if not addresses or any(not address.is_global for address in addresses):
        raise HTTPException(status_code=422, detail="Private and local network source URLs are not allowed.")


def _fetch_url(url: str) -> tuple[str, str]:
    _validate_public_url(url)
    try:
        with requests.get(
            url,
            timeout=(4, 10),
            allow_redirects=False,
            stream=True,
            headers={"User-Agent": "StarlightAI/1.0 (research source reader)"},
        ) as response:
            if response.is_redirect:
                raise HTTPException(
                    status_code=422,
                    detail="Redirected URLs are not supported. Add the final URL directly.",
                )
            response.raise_for_status()
            try:
                content_length = int(response.headers.get("Content-Length", "0"))
            except ValueError:
                raise HTTPException(status_code=422, detail="Source returned an invalid content length.") from None
            if content_length > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Source is larger than the 10 MB limit.")
            content = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                content.extend(chunk)
                if len(content) > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Source is larger than the 10 MB limit.")
            content = bytes(content)
            content_type = response.headers.get("Content-Type", "").lower()
            if "pdf" in content_type or url.lower().endswith(".pdf"):
                document = pymupdf.open(stream=content, filetype="pdf")
                return "\n".join(page.get_text() for page in document), "pdf"
            soup = BeautifulSoup(content, "html.parser")
            for element in soup(["script", "style", "noscript", "nav", "footer", "header"]):
                element.decompose()
            return soup.get_text(" ", strip=True), "web"
    except HTTPException:
        raise
    except (requests.RequestException, pymupdf.FileDataError) as error:
        raise HTTPException(status_code=422, detail=f"Could not read source URL: {error}") from error


@app.get("/health")
@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {
        "status": "online",
        "brand": "StarlightAI",
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


@app.post("/api/extract")
async def extract_upload(file: UploadFile = File(...)) -> dict[str, str]:
    filename = Path(file.filename or "uploaded-source").name
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
    try:
        if filename.lower().endswith(".pdf") or file.content_type == "application/pdf":
            document = pymupdf.open(stream=content, filetype="pdf")
            text = "\n".join(page.get_text() for page in document)
        elif filename.lower().endswith((".txt", ".md")) or file.content_type in {
            "text/plain",
            "text/markdown",
        }:
            text = content.decode("utf-8-sig")
        else:
            raise HTTPException(status_code=415, detail="Upload a PDF, TXT, or Markdown file.")
    except (UnicodeDecodeError, pymupdf.FileDataError) as error:
        raise HTTPException(status_code=422, detail="The uploaded file could not be read.") from error
    if not text.strip():
        raise HTTPException(status_code=422, detail="No readable text was found in the uploaded file.")
    return {"name": filename, "text": text[:MAX_SOURCE_CHARS], "truncated": str(len(text) > MAX_SOURCE_CHARS).lower()}


@app.post("/api/research")
def perform_research(request: ResearchRequest) -> dict:
    analyzed_sources = []
    for source in request.sources:
        text = source.text or ""
        source_type = "text"
        if source.url:
            fetched_text, source_type = _fetch_url(source.url)
            text = fetched_text
        if not text.strip():
            raise HTTPException(status_code=422, detail=f"Source '{source.name}' has no readable text.")
        analyzed_sources.append(
            {
                "name": source.name.strip(),
                "text": text[:MAX_SOURCE_CHARS],
                "url": source.url,
                "type": source_type,
            }
        )
    return analyze_research(request.query.strip(), analyzed_sources)


@app.post("/api/research/stream")
def stream_research(request: ResearchRequest) -> StreamingResponse:
    result = perform_research(request)

    def events():
        yield f"event: result\ndata: {json.dumps(result, ensure_ascii=False)}\n\n"
        yield "event: complete\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
