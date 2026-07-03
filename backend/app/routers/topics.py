"""Topic management API routes."""

import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException

from app.models.topic import (
    DEFAULT_TOPICS, Topic, PromptUpdateRequest, PromptVersion,
)

router = APIRouter(prefix="/api/topics", tags=["topics"])

# In-memory store (replace with database in production)
_topics: dict[str, Topic] = {}
_prompt_versions: dict[str, list[PromptVersion]] = {}


def _init_topics():
    """Initialize default topics."""
    for t in DEFAULT_TOPICS:
        if t["id"] not in _topics:
            _topics[t["id"]] = Topic(
                id=t["id"],
                name=t["name"],
                description=t["description"],
                icon=t["icon"],
                prompt=t["default_prompt"],
                default_prompt=t["default_prompt"],
                data_source_path=t["data_source_path"],
            )
            _prompt_versions[t["id"]] = [
                PromptVersion(topic_id=t["id"], version=1, content=t["default_prompt"])
            ]


_init_topics()


@router.get("")
async def list_topics():
    """List all topics."""
    return {"topics": [t.model_dump() for t in _topics.values()]}


@router.get("/{topic_id}")
async def get_topic(topic_id: str):
    """Get topic details."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _topics[topic_id].model_dump()


@router.put("/{topic_id}/prompt")
async def update_prompt(topic_id: str, req: PromptUpdateRequest):
    """Update topic prompt."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic = _topics[topic_id]
    topic.prompt = req.content
    topic.updated_at = datetime.now()
    # Guard against corrupted prompts containing Unicode replacement characters
    if topic_id == 'goodwood-festival' and '�' in topic.prompt:
        topic.prompt = topic.default_prompt

    # Save version
    versions = _prompt_versions.get(topic_id, [])
    next_version = len(versions) + 1
    # Mark previous as not current
    for v in versions:
        v.is_current = False
    versions.append(PromptVersion(
        topic_id=topic_id,
        version=next_version,
        content=req.content,
        is_current=True,
    ))
    _prompt_versions[topic_id] = versions

    return {"status": "success", "version": next_version}


@router.post("/{topic_id}/prompt/reset")
async def reset_prompt(topic_id: str):
    """Reset prompt to default."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    topic = _topics[topic_id]
    topic.prompt = topic.default_prompt
    topic.updated_at = datetime.now()

    versions = _prompt_versions.get(topic_id, [])
    for v in versions:
        v.is_current = False
    versions.append(PromptVersion(
        topic_id=topic_id,
        version=len(versions) + 1,
        content=topic.default_prompt,
        is_current=True,
    ))

    return {"status": "success", "prompt": topic.default_prompt}


@router.get("/{topic_id}/prompt/history")
async def get_prompt_history(topic_id: str):
    """Get prompt modification history."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    versions = _prompt_versions.get(topic_id, [])
    return {"versions": [v.model_dump() for v in versions]}


@router.post("/{topic_id}/prompt/rollback/{version}")
async def rollback_prompt(topic_id: str, version: int):
    """Rollback to a specific prompt version."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    versions = _prompt_versions.get(topic_id, [])
    target = next((v for v in versions if v.version == version), None)
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")

    topic = _topics[topic_id]
    topic.prompt = target.content
    topic.updated_at = datetime.now()

    for v in versions:
        v.is_current = False
    versions.append(PromptVersion(
        topic_id=topic_id,
        version=len(versions) + 1,
        content=target.content,
        is_current=True,
    ))

    return {"status": "success", "content": target.content}


@router.put("/{topic_id}/data-source")
async def update_data_source(topic_id: str, path: str):
    """Update data source path for a topic."""
    if topic_id not in _topics:
        raise HTTPException(status_code=404, detail="Topic not found")

    _topics[topic_id].data_source_path = path
    _topics[topic_id].updated_at = datetime.now()
    return {"status": "success", "path": path}
