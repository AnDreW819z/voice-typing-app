import time
import logging
import threading
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Sequence, Tuple

from faster_whisper import WhisperModel

@dataclass(frozen=True, slots=True)
class SegmentResult:
    start: float
    end: float
    text: str

@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """DTO (Data Transfer Object) для хранения результатов распознавания."""
    text: str
    language: str
    duration: float
    segments: Tuple[SegmentResult, ...]
    elapsed_time: float

class WhisperModelManager:
    """Управляет жизненным циклом модели: Singleton загрузка, фолбэк на CPU, прогрев."""
    _instance = None
    _init_lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._init_lock:
                if not cls._instance:
                    cls._instance = super(WhisperModelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config, logger: logging.Logger):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self.config = config
        self.logger = logger
        self.model: Optional[WhisperModel] = None
        self.load_time: float = 0.0
        self._initialized = True
        self._model_lock = threading.Lock()

    def get_model(self) -> WhisperModel:
        """Возвращает загруженную модель (загружает при первом обращении потокобезопасно)."""
        if self.model is None:
            with self._model_lock:
                if self.model is None:
                    self._load_model()
        return self.model

    def _log_loaded(self, device: str, compute_type: str):
        self.logger.info(
            f"[✔] Whisper model loaded: {self.config.model} | "
            f"Device: {device} | Compute: {compute_type} | Beam: {self.config.beam_size}"
        )

    def _load_model(self) -> None:
        """Инициализирует faster-whisper. Обеспечивает Graceful Degradation."""
        start_time = time.perf_counter()
        device = self.config.device
        compute_type = self.config.compute_type
        
        try:
            self.model = WhisperModel(
                model_size_or_path=self.config.model,
                device=device,
                compute_type=compute_type,
                download_root=self.config.model_dir,
                local_files_only=False
            )
            self._warmup()
            self.load_time = time.perf_counter() - start_time
            self._log_loaded(device, compute_type)
        except Exception as e:
            self.logger.warning(f"Ошибка загрузки на {device}: {e}. Fallback на CPU (int8)...")
            device = "cpu"
            compute_type = "int8"
            try:
                self.model = WhisperModel(
                    model_size_or_path=self.config.model,
                    device=device,
                    compute_type=compute_type,
                    download_root=self.config.model_dir,
                    local_files_only=False
                )
                self._warmup()
                self.load_time = time.perf_counter() - start_time
                self._log_loaded(device, compute_type)
            except Exception as cpu_e:
                self.logger.error(f"Критическая ошибка: не удалось загрузить модель даже на CPU: {cpu_e}", exc_info=True)
                raise

    def _warmup(self) -> None:
        """Прогрев (warmup) модели пустым аудиокадром. Изолирован от метрик."""
        self.logger.debug("Начало прогрева (warmup) модели...")
        # Короткий пустой аудиокадр (~0.5 сек)
        dummy_audio = np.zeros(int(self.config.sample_rate * 0.5), dtype=np.float32)
        segments, info = self.model.transcribe(
            audio=dummy_audio,
            language=self.config.language,
            beam_size=self.config.beam_size
        )
        list(segments)
        self.logger.debug("Прогрев успешно завершен.")

class BaseTranscriber(ABC):
    """Интерфейс для движков распознавания речи."""
    
    @abstractmethod
    def load_model(self) -> None:
        pass
        
    @abstractmethod
    def transcribe(self, audio_data: np.ndarray) -> Optional[TranscriptionResult]:
        pass

class WhisperTranscriber(BaseTranscriber):
    """Реализация движка распознавания на базе faster-whisper."""
    def __init__(self, config, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.manager = WhisperModelManager(config, logger)
        
    def load_model(self) -> None:
        """Запускает предзагрузку модели."""
        self.manager.get_model()
        
    def transcribe(self, audio_data: np.ndarray) -> Optional[TranscriptionResult]:
        """Выполняет инференс модели и возвращает DTO с результатами."""
        model = self.manager.get_model()
        start_time = time.perf_counter()
        
        try:
            self.logger.info("Начало вызова transcribe()")
            segments_gen, info = model.transcribe(
                audio=audio_data,
                language=self.config.language,
                beam_size=self.config.beam_size
            )
            self.logger.info("transcribe() вернул генератор")
            
            seg_results = []
            full_text = []
            
            self.logger.info("Начинаю чтение сегментов")
            # Извлекаем текст
            for s in segments_gen:
                clean_text = s.text.strip()
                full_text.append(clean_text)
                seg_results.append(SegmentResult(
                    start=s.start,
                    end=s.end,
                    text=clean_text
                ))
            self.logger.info("Сегменты обработаны")
                
            text = " ".join(full_text).strip()
            elapsed_time = time.perf_counter() - start_time
            audio_duration = len(audio_data) / self.config.sample_rate
            
            result = TranscriptionResult(
                text=text,
                language=info.language,
                duration=audio_duration,
                segments=tuple(seg_results),
                elapsed_time=elapsed_time
            )
            
            # ML Метрики
            if text:
                words = len(text.split())
                chars = len(text)
                rtf = elapsed_time / audio_duration if audio_duration > 0 else 0.0
                wps = words / elapsed_time if elapsed_time > 0 else 0.0
                cps = chars / elapsed_time if elapsed_time > 0 else 0.0
                
                self.logger.info(
                    f"ML Метрики: "
                    f"Инференс={elapsed_time:.3f}с, RTF={rtf:.3f}, "
                    f"Words/sec={wps:.1f}, Chars/sec={cps:.1f}"
                )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка во время распознавания: {e}", exc_info=True)
            return None
