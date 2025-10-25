from fastapi import FastAPI
from .routes import router

app = FastAPI(
    title="Lean API Worker System",
    version="1.0.0",
    description="A lean messaging system with API-to-worker communication via Kafka",
    docs_url="/docs",
    redoc_url="/redoc"
)
app.include_router(router)