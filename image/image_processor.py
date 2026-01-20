from typing import Any

import cv2
import numpy as np
from pathlib import Path

from data.enums import ProcessImageStatus
from data.image_processing_results import ProcessImageResult, CropData, AnalysisResult
from files.file_manager import file_manager
from image.skin_not_found import SkinNotFound


class ImageProcessor:
    def __init__(self, image_path: str | Path, user_id: int):
        self.image_path = Path(image_path)
        self.user_id = user_id
        self.img = cv2.imread(str(self.image_path))

        if self.img is None:
            raise ValueError(f"Could not read image at {image_path}")

    def get_interestiong_crops(self, padding: int = 50, min_area: int = 300) -> list[CropData | Any]:
        crops: list[CropData | Any] = []

        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        crops_dir = file_manager.ensure_crops_directory(self.user_id)

        height_orig, width_orig = self.img.shape[:2]
        total_area = height_orig * width_orig

        for index, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            if area < min_area or area > (total_area * 0.8):
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w) / h
            if aspect_ratio > 4.0 or aspect_ratio < 0.25:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            side = max(w, h) + padding * 2
            cx, cy = x + w // 2, y + h // 2

            x1, y1 = max(0, cx - side // 2), max(0, cy - side // 2)
            x2, y2 = min(width_orig, x1 + side), min(height_orig, y1 + side)

            crop = self.img[y1:y2, x1:x2]
            crop_name = f"crop_{index}_{self.user_id}.png"
            crop_path = crops_dir / crop_name
            cv2.imwrite(str(crop_path), crop)
            crops.append(CropData(path=crop_path, x=x1, y=y1, w=(x2-x1), h=(y2-y1)))

        return crops

    def resize_for_model(self, image, target_size: tuple[int, int] = (224, 224)):
        return cv2.resize(image, target_size, interpolation=cv2.INTER_LINEAR)

    def has_skin_in_photo(self, threshold: float = 0.3):
        ycrcb = cv2.cvtColor(self.img, cv2.COLOR_BGR2YCrCb)

        lower = np.array([0, 133, 77], dtype="uint8")
        upper = np.array([255, 173, 127], dtype="uint8")

        mask = cv2.inRange(ycrcb, lower, upper)
        skin_pixel_count = cv2.countNonZero(mask)
        total_pixels = self.img.shape[0] * self.img.shape[1]
        ratio = skin_pixel_count / total_pixels
        return ratio > threshold

    def process_image(self):
        if not self.has_skin_in_photo():
            raise SkinNotFound("Кожа не обнаружена на фото.")

        crops = self.get_interestiong_crops()
        if not crops:
            return ProcessImageResult(
                status=ProcessImageStatus.CLEANED,
                message="Кожа чистая, подозрительных объектов нет."
            )

        return ProcessImageResult(
            status=ProcessImageStatus.SUCCESS,
            crops=crops
        )

    def annotate_image(self, analysis_results: list[AnalysisResult]):
        annotated_img = self.img.copy()

        h_orig, w_orig = self.img.shape[:2]
        thickness = clip(int(w_orig / 150), 1, 4)
        font_scale = w_orig / 600
        text_offset = int(h_orig / 50)

        for result in analysis_results:
            crop = result.crop
            color = result.get_color()
            cv2.rectangle(annotated_img, (crop.x, crop.y), (crop.x + crop.w, crop.y + crop.h), (color.red, color.green, color.blue), thickness)

            label_text = f"{result.get_label()} {result.confidence:.1%}"

            cv2.putText(annotated_img, label_text, (crop.x, crop.y - text_offset), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness + 1)
            cv2.putText(annotated_img, label_text, (crop.x, crop.y - text_offset), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (color.red, color.green, color.blue), thickness)

        output_path = file_manager.get_user_folder(self.user_id) / f"result_{self.user_id}.png"
        cv2.imwrite(str(output_path), annotated_img)
        return output_path

def clip(n, smallest, largest):
    return max(smallest, min(n, largest))