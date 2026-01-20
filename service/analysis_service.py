from pathlib import Path

from data.enums import ProcessImageStatus
from data.image_processing_results import AnalysisResult, AnalyseServiceResult
from engine.inference_engine import inference_engine
from image.image_processor import ImageProcessor
from image.skin_not_found import SkinNotFound


class AnalysisService:
    @staticmethod
    async def analyze(user_id: int, photo_path: Path | str) -> AnalyseServiceResult:
        if isinstance(photo_path, str): photo_path = Path(photo_path)

        processor = ImageProcessor(photo_path, user_id)

        try:
            process_result = processor.process_image()
            if process_result.status == ProcessImageStatus.CLEANED:
                return AnalyseServiceResult(
                    status=process_result.status,
                    message=process_result.message,
                )

            analysis_results: list[AnalysisResult] = []
            for crop in process_result.crops:
                model_res = inference_engine.predict_crop(crop.path)

                if model_res.get_confidence() < 0.40:
                    continue

                if model_res.get_label() == "healthy" and model_res.get_confidence() < 0.60:
                    continue

                analysis_results.append(AnalysisResult(
                    crop=crop,
                    label=model_res.get_label(),
                    confidence=model_res.get_confidence()
                ))

            annotated_image_path = processor.annotate_image(analysis_results)

            return AnalyseServiceResult(
                status=ProcessImageStatus.SUCCESS,
                image_path=annotated_image_path,
                analysis_results=analysis_results
            )

        except SkinNotFound as se:
            return AnalyseServiceResult(
                status=ProcessImageStatus.ERROR,
                message=str(se),
            )
        except ValueError as ve:
            print(ve)
            return AnalyseServiceResult(
                status=ProcessImageStatus.ERROR,
                message="Не удалось обработать ваше фото."
            )
        except Exception as e:
            print(e)
            return AnalyseServiceResult(
                status=ProcessImageStatus.ERROR,
                message="Непредвиденная ошибка при обработке."
            )