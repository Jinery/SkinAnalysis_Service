import os
from pathlib import Path
import shutil

class FileManager:
    def __init__(self, base_path: str = "files"):
        self.base_path = Path(base_path)
        self.temp_path = self.base_path / "temp"
        self.models_path = self.base_path / "models"
        self.users_files_path = self.base_path / "users_files"
        self.classification_model_name = "SkinAnalysis_AI.keras"
        self.detector_model_name = "SkinAnalysisDetector"
        self.database_name = "skin_analysis_BotAndAPI_data.db"
        self.setup_directories()

    def setup_directories(self):
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        self.models_path.mkdir(parents=True, exist_ok=True)
        self.users_files_path.mkdir(parents=True, exist_ok=True)

    def get_user_folder(self, user_id: int) -> Path:
        user_path = self.users_files_path / str(user_id)
        if not user_path.exists():
            user_path.mkdir(parents=True, exist_ok=True)
        return user_path

    def write_file_data(self, file_data: bytes, file_path: str | Path) -> str:
        with open(file_path, "wb") as f:
            f.write(file_data)

        return str(file_path)

    def save_temporary_photo(self, photo_data: bytes, user_id: int, photo_name: str = None) -> Path:
        if photo_name is not None:
            name, extension = os.path.splitext(photo_name)
            exit_file_path = self.temp_path / f"{name}_{user_id}{extension or '.png'}"
        else:
            exit_file_path = self.temp_path / f"UserPhoto_{user_id}.png"

        self.write_file_data(photo_data, exit_file_path)
        return exit_file_path

    def clear_user_temp(self, user_id: int):
        for file in self.temp_path.iterdir():
            if str(user_id) in file.name:
                file.unlink()

        try:
            shutil.rmtree(self.get_crops_directory(user_id), ignore_errors=True)
        except FileNotFoundError:
            pass

    def get_crops_directory(self, user_id: int) -> Path:
        return self.temp_path / f"user_{user_id}_crops"

    def ensure_crops_directory(self, user_id: int) -> Path:
        crops_path = self.get_crops_directory(user_id)
        crops_path.mkdir(parents=True, exist_ok=True)
        return crops_path

    def get_classification_model_path(self) -> Path:
        model_path = self.models_path / self.classification_model_name
        if not model_path.exists():
            raise FileNotFoundError("Model not found")
        return model_path

    def get_detector_model_path(self) -> Path:
        model_path = self.models_path / self.detector_model_name
        if not model_path.exists():
            raise FileNotFoundError("Detector not found")
        return model_path

    def get_database_path(self) -> Path:
        database_path = self.base_path / self.database_name
        return database_path

    def get_temp_path(self) -> Path:
        return self.temp_path

    def get_file(self, file_path: str) -> bytes:
        path_to_file = Path(file_path)
        if path_to_file.exists():
            if path_to_file.is_file():
                with open(path_to_file, "rb") as f:
                    return f.read()

        raise FileNotFoundError(f"File not found: {path_to_file}")

    def delete_file(self, file_path: str):
        path_to_file = Path(file_path)
        if path_to_file.exists():
            if path_to_file.is_file():
                os.remove(path_to_file)
                return
        raise FileNotFoundError(f"File not found: {path_to_file}")


file_manager = FileManager()