import cv2
import numpy as np
from pathlib import Path

from data.enums import ProcessImageStatus
from data.image_processing_results import ProcessImageResult, CropData, AnalysisResult
from files.file_manager import file_manager
from image.skin_not_found import SkinNotFound
import tensorflow as tf


class ImageProcessor:
    _detector_model = None

    def __init__(self, img_path: str, user_id: int):
        if ImageProcessor._detector_model is None:
            try:
                model_path = str(file_manager.get_detector_model_path())
                loaded = tf.saved_model.load(model_path)
                ImageProcessor._detector_model = loaded.signatures['serving_default']
                print("Detector loaded successfully")
            except Exception as e:
                print(f"Error on loading model: {e}")

        self.detect_fn = ImageProcessor._detector_model
        self.user_id = user_id
        self.image = cv2.imread(img_path)

        if self.image is None:
            raise ValueError(f"Could not read image at path: {img_path}")

    def process_image(self):
        skin_mask = self.get_advanced_skin_mask()
        skin_pixels = cv2.countNonZero(skin_mask)
        if skin_pixels < (self.image.shape[0] * self.image.shape[1] * 0.01):
            raise SkinNotFound("attentions.analysis.skin_not_found")

        crops = self.get_interesting_crops()

        if not crops:
            return ProcessImageResult(
                status=ProcessImageStatus.CLEANED,
                message_key="success.analysis.cleaned"
            )

        return ProcessImageResult(
            status=ProcessImageStatus.SUCCESS,
            crops=crops
        )

    def get_interesting_crops(self, padding: int = 5) -> list:
        h_orig, w_orig = self.image.shape[:2]

        img_640 = cv2.resize(self.image, (640, 640))
        input_tensor = tf.cast(cv2.cvtColor(img_640, cv2.COLOR_BGR2RGB), tf.float32) / 255.0

        outputs = self.detect_fn(input_tensor[tf.newaxis, ...])
        raw_data = outputs['output_0'].numpy()[0]

        boxes, confidences = [], []

        for pred in raw_data:
            y1_640, x1_640, y2_640, x2_640, conf = pred[:5]
            if conf < 0.40: continue

            x1 = int(x1_640 * w_orig / 640)
            y1 = int(y1_640 * h_orig / 640)
            x2 = int(x2_640 * w_orig / 640)
            y2 = int(y2_640 * h_orig / 640)

            w, h = x2 - x1, y2 - y1

            boxes.append([x1, y1, w, h])
            confidences.append(float(conf))

        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.45, 0.4)
        crops = []

        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = boxes[i]

                x_start = max(0, x - padding)
                y_start = max(0, y - padding)
                x_end = min(w_orig, x + w + padding)
                y_end = min(h_orig, y + h + padding)

                crop_img = self.image[y_start:y_end, x_start:x_end]
                if crop_img.size == 0: continue

                path = file_manager.ensure_crops_directory(self.user_id) / f"crop_{i}.png"
                cv2.imwrite(str(path), crop_img)

                crops.append(CropData(path=path, x=x_start, y=y_start, w=(x_end - x_start), h=(y_end - y_start)))

        return crops

    def get_advanced_skin_mask(self) -> np.ndarray:
        ycrcb = cv2.cvtColor(self.image, cv2.COLOR_BGR2YCrCb)
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
        print("\nAnnotating image")
        annotated_img = self.image.copy()

        h_orig, w_orig = self.image.shape[:2]
        thickness = clip(int(w_orig / 150), 1, 4)
        font_scale = w_orig / 600
        text_offset = int(h_orig / 50)

        for result in analysis_results:
            crop = result.crop
            color = result.get_color()

            x = int(crop.x)
            y = int(crop.y)
            w = int(crop.w)
            h = int(crop.h)

            print(f"x: {x}, y: {y}, w: {w}, h: {h}")

            x2 = min(x + w, w_orig - 1)
            y2 = min(y + h, h_orig - 1)
            print(f"x2: {x2}, y2: {y2}")

            if x2 <= x or y2 <= y:
                print(f"Warning: invalid crop coordinates: x={x}, y={y}, w={w}, h={h}")
                continue

            label_text = f"{result.get_label()} {result.confidence:.1%}"

            cv2.rectangle(annotated_img, (x, y), (x2, y2), (color.red, color.green, color.blue), thickness)
            text_size = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness + 1)[0]
            cv2.rectangle(annotated_img,
                          (x, y - text_offset - text_size[1]),
                          (x + text_size[0], y - text_offset + 5),
                          (0, 0, 0), -1)

            cv2.putText(annotated_img, label_text,
                        (x, y - text_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                        (color.red, color.green, color.blue), thickness)

        output_path = file_manager.get_user_folder(self.user_id) / f"result_{self.user_id}.png"
        cv2.imwrite(str(output_path), annotated_img)
        return output_path

def clip(n, smallest, largest):
    return max(smallest, min(n, largest))