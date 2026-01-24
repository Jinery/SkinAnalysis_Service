from fastapi import FastAPI, Header, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.testclient import TestClient
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from datetime import datetime
import asyncio

from data.enums import APIStatus
from data.schemas import AnalysisResponse, AnalysisItemSchema, CropBoxSchema, TaskResponse, TaskStatus
from database.database import DeviceRegisterResponse, DeviceRegisterRequest, Connection
from database.database_worker import DatabaseWorker
from files.file_manager import file_manager
from handler.auth_handler import notify_device_connection
from service.analysis_service import AnalysisService
from tasks.task_manager import task_manager

app = FastAPI(
    title="SkinAnalysis API",
    description="SkinAnalysis API",
    version="1.0",
)


async def verify_token(connection_id: str = Header(...)):
    stats = await DatabaseWorker.get_connection_by_id(connection_id)
    if not stats:
        raise HTTPException(status_code=403, detail="Invalid or inactive Connection ID")
    return stats


@app.post("/analyze", response_model=TaskResponse)
async def analyze_image(
        background_tasks: BackgroundTasks,
        connection_id: str = Header(...),
        file: UploadFile = File(...),
        connection: Connection = Depends(verify_token)
):
    user_id = connection.user_id

    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    task_id = task_manager.create_task(user_id)

    content = await file.read()

    background_tasks.add_task(
        process_image_task,
        task_id=task_id,
        user_id=user_id,
        content=content,
        filename=file.filename
    )

    await task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING,
        message="Image uploaded, starting analysis",
        progress=10
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PROCESSING,
        message="Analysis started",
        created_at=datetime.now(),
        result_url=f"/tasks/{task_id}/result"
    )


@app.get("/tasks/{task_id}/status", response_model=TaskResponse)
async def get_task_status(task_id: str):
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskResponse(
        task_id=task_id,
        status=task['status'],
        message=task['message'],
        created_at=datetime.fromisoformat(task['created_at']),
        updated_at=datetime.fromisoformat(task['updated_at']) if task.get('updated_at') else None,
        progress=task.get('progress'),
        result_url=f"/tasks/{task_id}/result" if task.get('result') else None
    )


@app.get("/tasks/{task_id}/result")
async def get_task_result(
        task_id: str,
        connection_id: str = Header(...),
        connection: Connection = Depends(verify_token)
):
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task['status'] != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Task is not completed. Current status: {task['status']}"
        )

    result = task.get('result')
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")

    return result


@app.get("/result/{user_id}/{image_name}")
async def get_result_image(
        user_id: str,
        image_name: str,
        connection_id: str = Header(...),
        connection: Connection = Depends(verify_token)
):
    file_path = file_manager.get_user_folder(user_id) / image_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)


async def process_image_task(
        task_id: str,
        user_id: int,
        content: bytes,
        filename: str,
        connection_id: str = Header(...),
        connection: Connection = Depends(verify_token)
):
    try:
        await task_manager.update_task(
            task_id=task_id,
            message="Saving image file",
            progress=20
        )

        temp_path = file_manager.save_temporary_photo(content, user_id, filename)

        await task_manager.update_task(
            task_id=task_id,
            message="Processing image with AI model",
            progress=40
        )

        result = await AnalysisService.analyze(user_id, temp_path)

        await task_manager.update_task(
            task_id=task_id,
            message="Generating annotated image",
            progress=80
        )

        analysis_response = AnalysisResponse(
            status=result.get_status(),
            message=result.get_message(),
            image_url=f"/result/{user_id}/{result.get_image_path().name}" if result.get_image_path() else None,
            analysis_results=[
                AnalysisItemSchema(
                    label=res.get_label(),
                    confidence=res.get_confidence(),
                    box=CropBoxSchema(
                        x=res.crop.x,
                        y=res.crop.y,
                        w=res.crop.w,
                        h=res.crop.h
                    )
                ) for res in result.get_analysis_results()
            ]
        )

        await task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            message="Analysis completed successfully",
            progress=100,
            result=analysis_response.dict()
        )

    except Exception as e:
        import logging
        logging.error(f"Task {task_id} failed: {str(e)}", exc_info=True)

        await task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED,
            message=f"Analysis failed: {str(e)}",
            progress=0
        )

@app.post("/auth/register-device", response_model=DeviceRegisterResponse)
async def register_device(device_info: DeviceRegisterRequest, connection_id: str = Header(...), connection: Connection = Depends(verify_token)):
    try:
        user_id = connection.user_id
        device, status = await DatabaseWorker.add_device(connection_id, device_info.model_dump())

        match status:
            case APIStatus.SUCCESS:
                await notify_device_connection(
                    user_id=user_id,
                    device_platform=device.platform,
                    device_uid=device.device_uid,
                    device_name=device.name,
                    device_model=device.model,
                    device_os_version=device.os_version,
                    connection_id=connection_id
                )
                return {
                    "status": "success",
                    "device_id": device.id if device else None,
                    "message": "Device registered successfully"
                }
            case APIStatus.NOT_FOUND:
                raise HTTPException(
                    status_code=404,
                    detail=f"Connection '{connection_id}' not found"
                )
            case APIStatus.LIMIT_EXCEEDED:
                raise HTTPException(
                    status_code=403,
                    detail="Device limit reached for this connection"
                )
            case _:
                raise HTTPException(
                    status_code=500,
                    detail=f"Unknown error: {status.value}"
                )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_tasks_periodically())


async def cleanup_tasks_periodically():
    while True:
        await asyncio.sleep(3600)
        await task_manager.cleanup_old_tasks()

app.get("/")
async def root():
    return {
        "message": "Skin Analysis API",
        "status": "running",
    }


app.mount("/results", StaticFiles(directory=str(file_manager.get_temp_path())), name="results")