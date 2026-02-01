from fastapi import FastAPI, Header, File, UploadFile, Depends, HTTPException, BackgroundTasks
from starlette.responses import FileResponse
from datetime import datetime

from data.enums import APIStatus, Platform
from data.schemas import AnalysisResponse, AnalysisItemSchema, CropBoxSchema, TaskResponse, TaskStatus
from database.database import DeviceRegisterResponse, DeviceRegisterRequest, Connection
from database.database_worker import DatabaseWorker
from files.file_manager import file_manager
from handler.auth_handler import notify_device_connection
from service.analysis_service import AnalysisService
from tasks.task_manager import task_manager
from transflate.translator import translator

app = FastAPI(
    title="SkinAnalysis API",
    description="SkinAnalysis API",
    version="1.0",
)


async def verify_token(
        connection_id: str = Header(...),
        device_uid: str = Header(..., alias="X-Device-ID"),
        lang: str = Header("en", alias="Accept-Language")
):
    stats = await DatabaseWorker.get_connection_by_id(connection_id)

    if not stats:
        raise HTTPException(
            status_code=403,
            detail=translator.translate("errors.auth.invalid_connection_id", Platform.API, lang)
        )

    if not stats.is_active:
        raise HTTPException(
            status_code=403,
            detail=translator.translate("errors.auth.connection_not_active", Platform.API, lang)
        )

    active_status, api_status = await DatabaseWorker.get_device_active_status(connection_id, device_uid)
    if not active_status:
        raise HTTPException(
            status_code=403,
            detail=translator.translate("errors.auth.device_not_active", Platform.API, lang)
        )

    return stats


@app.post("/analyze", response_model=TaskResponse)
async def analyze_image(
        background_tasks: BackgroundTasks,
        connection_id: str = Header(...),
        device_uid: str = Header(..., alias="X-Device-ID"),
        file: UploadFile = File(...),
        connection: Connection = Depends(verify_token),
        lang: str = Header("en", alias="Accept-Language")
):
    user_id = connection.user_id

    if not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=translator.translate("errors.validation.file_not_image", Platform.API, lang)
        )

    task_id = await task_manager.create_task(user_id)
    content = await file.read()

    background_tasks.add_task(
        process_image_task,
        task_id=task_id,
        user_id=user_id,
        content=content,
        filename=file.filename,
        lang=lang
    )

    await task_manager.update_task(
        task_id=task_id,
        status=TaskStatus.PROCESSING,
        message=translator.translate("status.upload.image_uploaded", Platform.API, lang),
        progress=10
    )

    return TaskResponse(
        task_id=task_id,
        status=TaskStatus.PROCESSING,
        message=translator.translate("success.tasks.analysis_started", Platform.API, lang),
        created_at=datetime.now(),
        result_url=f"/tasks/{task_id}/result"
    )


@app.get("/tasks/{task_id}/status", response_model=TaskResponse)
async def get_task_status(
        task_id: str,
        connection_id: str = Header(...),
        device_uid: str = Header(..., alias="X-Device-ID"),
        connection: Connection = Depends(verify_token),
        lang: str = Header("en", alias="Accept-Language")
):
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=translator.translate("errors.tasks.task_not_found", Platform.API, lang)
        )

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
        device_uid: str = Header(..., alias="X-Device-ID"),
        connection: Connection = Depends(verify_token),
        lang: str = Header("en", alias="Accept-Language")
):
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=404,
            detail=translator.translate("errors.tasks.task_not_found", Platform.API, lang)
        )

    if task['status'] != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=translator.translate("errors.tasks.working_task_status", Platform.API, lang, status=task['status'])
        )

    result = task.get('result')
    if not result:
        raise HTTPException(
            status_code=404,
            detail=translator.translate("errors.resources.result_not_found", Platform.API, lang)
        )

    return result


@app.get("/result/{user_id}/{image_name}")
async def get_result_image(
        user_id: str,
        image_name: str,
        connection_id: str = Header(...),
        device_uid: str = Header(..., alias="X-Device-ID"),
        connection: Connection = Depends(verify_token),
        lang: str = Header("en", alias="Accept-Language")
):
    file_path = file_manager.get_user_folder(user_id) / image_name
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=translator.translate("errors.resources.image_not_found", Platform.API, lang)
        )
    return FileResponse(file_path)


async def process_image_task(
        task_id: str,
        user_id: int,
        content: bytes,
        filename: str,
        lang: str = "en"
):
    try:
        await task_manager.update_task(
            task_id=task_id,
            message=translator.translate("status.upload.saving_image", Platform.API, lang),
            progress=20
        )

        temp_path = file_manager.save_temporary_photo(content, user_id, filename)

        await task_manager.update_task(
            task_id=task_id,
            message=translator.translate("status.processing.processing_ai", Platform.API, lang),
            progress=40
        )

        result = await AnalysisService.analyze(user_id, temp_path)

        await task_manager.update_task(
            task_id=task_id,
            message=translator.translate("status.processing.generating_result", Platform.API, lang),
            progress=80
        )

        analysis_response = AnalysisResponse(
            status=result.get_status(),
            message=result.get_message_key(),
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
            message=translator.translate("success.tasks.analysis_completed", Platform.API, lang),
            progress=100,
            result=analysis_response.dict()
        )

    except Exception as e:
        import logging
        logging.error(f"Task {task_id} failed: {str(e)}", exc_info=True)

        await task_manager.update_task(
            task_id=task_id,
            status=TaskStatus.FAILED,
            message=translator.translate("errors.tasks.task_failed", Platform.API, lang, task_id=task_id, error=str(e)),
            progress=0
        )


@app.post("/auth/register-device", response_model=DeviceRegisterResponse)
async def register_device(
        device_info: DeviceRegisterRequest,
        connection_id: str = Header(...),
        device_uid: str = Header(..., alias="X-Device-ID"),
        connection: Connection = Depends(verify_token),
        lang: str = Header("en", alias="Accept-Language")
):
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
                    "message": translator.translate("success.auth.device_registered", Platform.API, lang)
                }
            case APIStatus.NOT_FOUND:
                raise HTTPException(
                    status_code=404,
                    detail=translator.translate("errors.auth.connection_not_found", Platform.API, lang,
                                                connection_id=connection_id)
                )
            case APIStatus.LIMIT_EXCEEDED:
                raise HTTPException(
                    status_code=403,
                    detail=translator.translate("errors.auth.device_limit", Platform.API, lang)
                )
            case _:
                raise HTTPException(
                    status_code=500,
                    detail=translator.translate("errors.server.unknown_error", Platform.API, lang, error=status.value)
                )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=translator.translate("errors.server.unknown_error", Platform.API, lang, error=str(e))
        )


@app.get("/auth/check")
async def check(
        connection_id: str = Header(...),
        device_uid: str = Header(..., alias="X-Device-ID"),
        connection: Connection = Depends(verify_token),
        lang: str = Header("en", alias="Accept-Language")
):
    return {
        "status": "success",
        "message": translator.translate("success.auth.secure_endpoint_available", Platform.API, lang)
    }


@app.get("/")
async def root(lang: str = Header("en", alias="Accept-Language")):
    message = translator.translate(
        "success.api_running",
        Platform.API,
        lang
    )

    return {
        "message": "Skin Analysis API",
        "status": message,
        "debug": {
            "lang": lang
        }
    }