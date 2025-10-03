from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import saga_configuration, saga_execution

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="SAGA orchestration engine with FastAPI"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(saga_configuration.router, prefix=settings.API_PREFIX)
app.include_router(saga_execution.router, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
