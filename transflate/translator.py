from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

from data.enums import Platform


class BaseTranslator(ABC):
    @abstractmethod
    def translate(self, key: str, platform: Platform, lang: str = "en", **params) -> str:
        pass

    @abstractmethod
    def get_available_languages(self) -> list[str]:
        pass

class JsonTranslator(BaseTranslator):
    def __init__(self, translations_path: str = "locales"):
        self.translations_path = Path(translations_path)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _load_all(self):
        for lang_dir in self.translations_path.iterdir():
            if lang_dir.is_dir():
                lang = lang_dir.name.lower()
                self._cache[lang] = {}
                for platform in Platform:
                    file_path = lang_dir / f"{platform.value}.json"
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            import json
                            self._cache[lang][platform.value] = json.load(f)

    def translate(self, key: str, platform: Platform, lang: str = "en", **params) -> str:
        translations = self._cache.get(lang, {}).get(platform.value, {})
        parts = key.split(".")
        value = translations

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = None
                break

        if value is None and lang != "en":
            return self.translate(key, platform, "en", **params)

        if value is None or not isinstance(value, str):
            return key

        try:
            return value.format(**params) if params else value
        except KeyError:
            return value

    def get_available_languages(self) -> list[str]:
        return list(self._cache.keys())