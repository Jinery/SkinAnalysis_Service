from pathlib import Path

import numpy as np
import tensorflow as tf

from data.model_results import ModelPredictResult
from files.file_manager import file_manager


class InferenceEngine:
    def __init__(self):
        self.model: tf.keras.Model = tf.keras.models.load_model(str(file_manager.get_base_model_path()))
        self.class_names = ["healthy", "nevus", "problem"]

    def predict_crop(self, crop_path: Path):
        img = tf.keras.utils.load_img(str(crop_path), target_size=(224, 224))
        img_array = tf.keras.utils.img_to_array(img)
        img_array = np.expand_dims(img_array, axis=0)
        predictions = self.model.predict(img_array, verbose=0)
        class_idx = np.argmax(predictions[0])

        return ModelPredictResult(
            label=self.class_names[class_idx],
            confidence=float(np.max(predictions[0]))
        )


inference_engine = InferenceEngine()