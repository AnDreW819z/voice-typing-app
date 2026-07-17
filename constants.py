"""
constants.py

Модуль содержит все глобальные константы приложения,
магические строки и значения по умолчанию.
"""
from typing import Literal

# Типы вычислений и устройств
DeviceType = Literal["cuda", "cpu"]
ComputeType = Literal["float16", "int8", "float32"]

DEFAULT_DEVICE: DeviceType = "cuda"
DEFAULT_COMPUTE_TYPE: ComputeType = "float16"

# Настройки модели по умолчанию
DEFAULT_MODEL = "large-v3-turbo"
DEFAULT_LANGUAGE = "ru"
DEFAULT_MODEL_DIR = "models"

# Настройки аудио
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_HOTKEY = "f8"
DEFAULT_CHANNELS = 1
DEFAULT_DTYPE = "float32"
DEFAULT_BLOCKSIZE = 2048
DEFAULT_SILENCE_THRESHOLD = 0.01
DEFAULT_MIN_DURATION = 0.5
DEFAULT_MAX_DURATION = 60.0

# Настройки ML
DEFAULT_BEAM_SIZE = 5

# Настройки взаимодействия с ОС
DEFAULT_SUPPRESS_HOTKEY = True
DEFAULT_APPEND_TRAILING_SPACE = True

# Версия конфигурации
CURRENT_CONFIG_VERSION = 1
