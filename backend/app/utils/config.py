"""Application configuration management."""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel


class AppConfig(BaseModel):
    """Application configuration."""
    # GenAI
    genai_endpoint: str = ""
    genai_api_key: str = ""
    genai_model: str = "xai.grok-4.20-multi-agent-0309"

    # Object Storage
    os_namespace: str = ""
    os_bucket_reports: str = "autogeo-reports"
    os_bucket_data: str = "autogeo-data"
    os_config_profile: str = "DEFAULT"
    oci_region: str = "us-chicago-1"

    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Analysis
    analysis_timeout: int = 120


def _load_env_file(path: str) -> None:
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    project_env = Path(__file__).resolve().parents[2] / ".env"
    repo_env = Path(__file__).resolve().parents[3] / "backend" / ".env"
    _load_env_file(project_env)
    _load_env_file(repo_env)
    return AppConfig(
        genai_endpoint=os.getenv(
            "OPENAI_BASE_URL",
            os.getenv(
                "OCI_GENAI_ENDPOINT",
                "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130/actions/v1",
            ),
        ),
        genai_api_key=os.getenv("OPENAI_API_KEY", os.getenv("OCI_GENAI_API_KEY", "")),
        genai_model=os.getenv("OCI_GENAI_MODEL", os.getenv("OPENAI_MODEL", "xai.grok-4.20-multi-agent-0309")),
        os_namespace=os.getenv("OCI_OBJECT_STORAGE_NAMESPACE", ""),
        os_bucket_reports=os.getenv("OCI_OBJECT_STORAGE_BUCKET", "autogeo-reports"),
        os_bucket_data=os.getenv("OCI_OBJECT_STORAGE_DATA_BUCKET", "autogeo-data"),
        os_config_profile=os.getenv("OCI_CONFIG_PROFILE", "DEFAULT"),
        oci_region=os.getenv("OCI_REGION", "us-chicago-1"),
        api_host=os.getenv("API_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        analysis_timeout=int(os.getenv("ANALYSIS_TIMEOUT", "120")),
    )
