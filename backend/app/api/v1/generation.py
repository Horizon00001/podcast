import uuid
import json
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.schemas.generation import (
    GenerationTaskStatusResponse,
    GenerationTriggerRequest,
    GenerationTriggerResponse,
    RSSSourceListResponse,
    TopicOptionListResponse,
)
from app.services.generation_service import generation_service
from app.services.rss_service import RSSService
from app.services.topic_service import topic_service


router = APIRouter(prefix="/generation", tags=["generation"])


@router.get("/sources", response_model=RSSSourceListResponse)
def get_rss_sources():
    rss_service = RSSService(config_path=settings.feed_config_path, output_dir=settings.output_dir)
    feeds = rss_service.load_config()
    enabled_feeds = [
        {
            "id": f["id"],
            "name": f["name"],
            "url": f["url"],
            "category": f.get("category", "general"),
        }
        for f in feeds
        if f.get("enabled", False)
    ]
    return RSSSourceListResponse(sources=enabled_feeds)


@router.get("/topics", response_model=TopicOptionListResponse)
def get_topic_options():
    return TopicOptionListResponse(topics=topic_service.list_topics())


@router.post("/trigger", response_model=GenerationTriggerResponse)
def trigger_generation(payload: GenerationTriggerRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    task = generation_service.create_task(payload.rss_source, payload.topic, task_id)
    background_tasks.add_task(generation_service.run_task, task_id)
    return GenerationTriggerResponse(
        task_id=task.task_id,
        status=task.status,
        message=task.message,
    )


@router.get("/{task_id}/stream")
async def stream_generation_logs(task_id: str) -> StreamingResponse:
    async def event_generator() -> AsyncGenerator[str, None]:
        task = generation_service.get_task(task_id)
        if not task:
            yield f"data: {json.dumps(['error', 'Task not found'])}\n\n"
            return
        
        last_processed_count = 0
        
        while True:
            task = generation_service.get_task(task_id)
            if not task:
                break
            
            if task.status in ("succeeded", "failed"):
                yield f"data: {json.dumps(['status', task.status, task.message])}\n\n"
                break
            
            new_logs = generation_service.get_new_logs(task_id, last_processed_count)
            
            for log in new_logs:
                yield f"data: {json.dumps(['log', log])}\n\n"
                last_processed_count += 1
            
            if task.status == "running" and task.message:
                if len(new_logs) == 0:
                    yield f"data: {json.dumps(['status', task.status, task.message])}\n\n"
            
            import asyncio
            await asyncio.sleep(0.5)
        
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{task_id}", response_model=GenerationTaskStatusResponse)
def get_generation_task(task_id: str):
    task = generation_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    logs = task.logs if isinstance(task.logs, list) else []
    return GenerationTaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        message=task.message,
        rss_source=task.rss_source,
        topic=task.topic,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )
