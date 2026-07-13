"""F4.1 (MI-21): CLAUDE.md §18.5 -- error responses must leak no internals
(stack traces, SQL, file paths). FastAPI's default handlers for
HTTPException and request-validation errors are already sanitized; the one
gap is an unhandled exception, which by default an ASGI server may surface
with a bare/inconsistent body. This registers a catch-all handler that
always returns a generic sanitized body and logs the real exception
(with traceback) server-side only."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception processing %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
