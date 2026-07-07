"""FastAPI main application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.utils.config import load_config
from app.services.genai_client import GenAIClient
from app.services.object_storage import ObjectStorageService
from app.services.analysis_engine import AnalysisEngine
from app.services.pdf_generator import PDFGenerator
from app.routers import topics, analysis, reports, settings, auth, dashboard

app = FastAPI(
    title="AUTO GEO 舆情分析系统",
    description="汽车行业舆情监测与分析平台 - 基于 OCI GenAI Grok 模型",
    version="1.0.0",
)

# CORS — allow_credentials=True is incompatible with allow_origins=["*"];
# we use header-based auth (Authorization) so credentials (cookies) are not needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load config and initialize services
config = load_config()
genai_client = GenAIClient(
    api_key=config.genai_api_key,
    base_url=config.genai_endpoint,
    default_model=config.genai_model,
)
storage_service = ObjectStorageService(
    namespace=config.os_namespace,
    config_profile=config.os_config_profile,
)
analysis_engine = AnalysisEngine(genai_client, storage_service)
pdf_generator = PDFGenerator()

# Set dependencies for routers
analysis.set_engine(analysis_engine)
reports.set_dependencies(pdf_generator, storage_service, config.os_bucket_reports)

# Include routers
app.include_router(topics.router)
app.include_router(analysis.router)
app.include_router(reports.router)
app.include_router(settings.router)
app.include_router(auth.router)
app.include_router(dashboard.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/models")
async def list_models():
    """List available AI models."""
    return {"models": genai_client.list_models()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.api_host, port=config.api_port)
