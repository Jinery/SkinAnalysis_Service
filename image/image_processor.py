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

    def process_image(self):

        skin_mask = self.get_advanced_skin_mask()
        skin_pixels = cv2.countNonZero(skin_mask)
        total_pixels = self.img.shape[0] * self.img.shape[1]

        if skin_pixels < (total_pixels * 0.01):
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

    def get_interestiong_crops(self, padding: int = 50) -> list:
        crops = []
        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))
        blackhat = cv2.morphologyEx(blurred, cv2.MORPH_BLACKHAT, kernel)

        _, thresh = cv2.threshold(blackhat, 18, 255, cv2.THRESH_BINARY)

        skin_mask = self.get_advanced_skin_mask()
        skin_border_exclude = cv2.erode(skin_mask, np.ones((10, 10), np.uint8), iterations=1)
        final_mask = cv2.bitwise_and(thresh, skin_border_exclude)

        contours, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        height_orig, width_orig = self.img.shape[:2]
        total_area = height_orig * width_orig

        for index, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)

            if area < 150 or area > (total_area * 0.1):
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            roi_gray = gray[y:y + h, x:x + w]

            object_brightness = np.mean(roi_gray[thresh[y:y + h, x:x + w] > 0])

            if object_brightness > 120:
                continue

            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            if hull_area == 0 or (area / hull_area) < 0.65:
                continue

            roi_color = self.img[y:y + h, x:x + w]

            if self.is_lip_or_red_spot(roi_color):
                continue

            if self.is_too_dark_or_empty(roi_color):
                continue

            aspect_ratio = float(w) / h
            if aspect_ratio > 2.2 or aspect_ratio < 0.45:
                continue

            side = max(w, h) + padding * 2
            cx, cy = x + w // 2, y + h // 2
            x1, y1 = max(0, cx - side // 2), max(0, cy - side // 2)
            x2, y2 = min(width_orig, x1 + side), min(height_orig, y1 + side)

            crop_path = file_manager.ensure_crops_directory(self.user_id) / f"crop_{index}.png"
            cv2.imwrite(str(crop_path), self.img[y1:y2, x1:x2])

            crops.append(CropData(path=crop_path, x=x1, y=y1, w=(x2 - x1), h=(y2 - y1)))

        return crops

    def get_advanced_skin_mask(self) -> np.ndarray:
        ycrcb = cv2.cvtColor(self.img, cv2.COLOR_BGR2YCrCb)
        mask = cv2.inRange(ycrcb, np.array([0, 133, 77]), np.array([255, 173, 127]))

        kernel = np.ones((15, 15), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def is_lip_or_red_spot(self, roi: np.ndarray) -> bool:
        if roi.size == 0: return True
        lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
        avg_a = np.mean(lab[:, :, 1])
        return avg_a > 153

    def is_too_dark_or_empty(self, roi: np.ndarray) -> bool:
        if roi.size == 0: return True
        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_val = np.mean(gray_roi)
        return mean_val < 40

    def resize_for_model(self, image, target_size: tuple[int, int] = (224, 224)):
        return cv2.resize(image, target_size, interpolation=cv2.INTER_LINEAR)

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