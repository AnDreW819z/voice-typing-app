"""
config.py

Модуль для загрузки, валидации и управления конфигурацией приложения.
Использует Pydantic v2 для строгой валидации типов и значений.
"""

import sys
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ValidationError, field_validator

from constants import (
    DeviceType, ComputeType, DEFAULT_DEVICE, DEFAULT_COMPUTE_TYPE,
    DEFAULT_MODEL, DEFAULT_LANGUAGE, DEFAULT_MODEL_DIR, 
    DEFAULT_SAMPLE_RATE, DEFAULT_HOTKEY, CURRENT_CONFIG_VERSION,
    DEFAULT_CHANNELS, DEFAULT_DTYPE, DEFAULT_BLOCKSIZE,
    DEFAULT_SILENCE_THRESHOLD, DEFAULT_MIN_DURATION, DEFAULT_MAX_DURATION,
    DEFAULT_BEAM_SIZE, DEFAULT_SUPPRESS_HOTKEY, DEFAULT_APPEND_TRAILING_SPACE
)

logger = logging.getLogger("VoiceTypingApp")

class AppConfig(BaseModel):
    """
    Класс конфигурации приложения на базе Pydantic.
    Обеспечивает валидацию входных данных.
    """
    model_config = {'protected_namespaces': ()}

    config_version: int = Field(default=CURRENT_CONFIG_VERSION, description="Версия файла конфигурации")
    hotkey: str = Field(default=DEFAULT_HOTKEY, description="Горячая клавиша для записи")
    language: str = Field(default=DEFAULT_LANGUAGE, description="Язык распознавания")
    model: str = Field(default=DEFAULT_MODEL, description="Модель faster-whisper")
    device: DeviceType = Field(default=DEFAULT_DEVICE, description="Устройство для вычислений (cuda/cpu)")
    compute_type: ComputeType = Field(default=DEFAULT_COMPUTE_TYPE, description="Тип вычислений (float16/int8)")
    beam_size: int = Field(default=DEFAULT_BEAM_SIZE, gt=0, description="Beam size для faster-whisper")
    sample_rate: int = Field(default=DEFAULT_SAMPLE_RATE, gt=0, description="Частота дискретизации аудио (Hz)")
    model_dir: str = Field(default=DEFAULT_MODEL_DIR, description="Директория для хранения моделей")
    channels: int = Field(default=DEFAULT_CHANNELS, gt=0, description="Количество аудиоканалов")
    dtype: str = Field(default=DEFAULT_DTYPE, description="Тип данных аудио (float32)")
    blocksize: int = Field(default=DEFAULT_BLOCKSIZE, gt=0, description="Размер блока аудио")
    silence_threshold: float = Field(default=DEFAULT_SILENCE_THRESHOLD, ge=0.0, description="Порог тишины (RMS)")
    min_recording_duration: float = Field(default=DEFAULT_MIN_DURATION, gt=0.0, description="Минимальная длина (сек)")
    max_recording_duration: float = Field(default=DEFAULT_MAX_DURATION, gt=0.0, description="Максимальная длина (сек)")
    suppress_hotkey: bool = Field(default=DEFAULT_SUPPRESS_HOTKEY, description="Подавлять ли горячую клавишу в ОС")
    append_trailing_space: bool = Field(default=DEFAULT_APPEND_TRAILING_SPACE, description="Добавлять ли пробел в конце текста")

    @field_validator("config_version")
    @classmethod
    def check_version(cls, v: int) -> int:
        """
        Проверяет версию конфигурации.
        
        Args:
            v: Версия конфигурации из файла.
            
        Returns:
            int: Валидированная версия конфигурации.
        """
        if v != CURRENT_CONFIG_VERSION:
            logger.warning(f"Версия конфига {v} отличается от ожидаемой {CURRENT_CONFIG_VERSION}.")
        return v

    @classmethod
    def load(cls, config_path: Path) -> "AppConfig":
        """
        Загружает конфигурацию из JSON файла.
        В случае ошибки валидации логирует проблему и завершает работу программы (без print).

        Args:
            config_path: Путь к JSON файлу конфигурации.

        Returns:
            AppConfig: Валидированный объект конфигурации.
        """
        if not config_path.exists():
            logger.info("Файл конфигурации не найден. Будут использованы значения по умолчанию.")
            default_config = cls()
            default_config.save(config_path)
            return default_config

        try:
            with config_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Критическая ошибка: файл конфигурации {config_path} поврежден. {e}")
            sys.exit(1)
        except ValidationError as e:
            logger.error(f"Критическая ошибка: неверные параметры в файле {config_path}:\n{e}")
            sys.exit(1)

    def save(self, config_path: Path) -> None:
        """
        Сохраняет текущую конфигурацию в JSON файл.
        
        Args:
            config_path: Путь для сохранения JSON файла.
        """
        try:
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(self.model_dump(), f, indent=4, ensure_ascii=False)
            logger.info(f"Конфигурация успешно сохранена в {config_path}.")
        except Exception as e:
            logger.error(f"Не удалось сохранить конфигурацию в {config_path}: {e}")
