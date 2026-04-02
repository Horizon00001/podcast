import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.schemas.generation import (
    GenerationTaskStatusResponse,
    GenerationTriggerRequest,
    GenerationTriggerResponse,
)
from app.services.generation_service import generation_service


router = APIRouter(prefix="/generation", tags=["generation"])


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


@router.get("/{task_id}", response_model=GenerationTaskStatusResponse)
def get_generation_task(task_id: str):
    task = generation_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return GenerationTaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        message=task.message,
        rss_source=task.rss_source,
        topic=task.topic,
        created_at=task.created_at.isoformat(),
        updated_at=task.updated_at.isoformat(),
    )
