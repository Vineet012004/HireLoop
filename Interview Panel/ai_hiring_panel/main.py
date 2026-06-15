"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.db import init_db
from api.routes import router

app = FastAPI(
    title="HireLoop",
    description="Multi-agent interview system for SDE hiring — powered by Groq + Llama",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    init_db()
    print("✅  Database initialised.")


@app.get("/health")
def health():
    return {"status": "ok", "service": "HireLoop"}
