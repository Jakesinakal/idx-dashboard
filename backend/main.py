import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import briefing, currency, ihsg, movers, news, screener, snapshot, stocks

app = FastAPI(title="Finance Dashboard API", version="1.0.0")

_default_origins = "http://localhost:3000,http://localhost:3001,https://financial-data-dashboard-vz.vercel.app"
_allowed_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", _default_origins).split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(snapshot.router, prefix="/api")
app.include_router(stocks.router, prefix="/api")
app.include_router(currency.router, prefix="/api")
app.include_router(ihsg.router, prefix="/api")
app.include_router(screener.router, prefix="/api")
app.include_router(movers.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(briefing.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
