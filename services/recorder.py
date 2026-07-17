"""
services/recorder.py

Модуль для записи аудио с микрофона (Push-To-Talk).
Реализует захват аудио через sounddevice и неблокирующий callback.
"""

import queue
import logging
import numpy as np
import sounddevice as sd

class RecordingValidationError(Exception):
    """Исключение для ошибок валидации записанного аудио (слишком короткое, тишина)."""
    pass

class Recorder:
    """
    Класс для управления захватом аудио.
    Обеспечивает потокобезопасный сбор данных в очередь, обработку переполнений,
    лимиты записи и очистку ресурсов без утечек.
    """
    def __init__(self, config, logger: logging.Logger):
        """
        Инициализирует рекордер с конфигурацией и логгером.
        
        Args:
            config: Конфигурация приложения (AppConfig).
            logger: Инстанс логгера.
        """
        self.config = config
        self.logger = logger
        
        self.audio_queue = queue.Queue()
        self.stream = None
        
        self._frames_recorded = 0
        self._max_frames = int(self.config.sample_rate * self.config.max_recording_duration)
        self._is_recording = False
        self._limit_reached = False

    def _clear_queue(self) -> None:
        """Полностью очищает очередь от старых аудио-блоков."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def start_recording(self) -> None:
        """Запускает захват аудио с микрофона в фоновом режиме."""
        if self._is_recording:
            self.logger.warning("Попытка начать запись, когда она уже идет (State: RECORDING). Игнорируется.")
            return

        self._clear_queue()

        self._frames_recorded = 0
        self._is_recording = True
        self._limit_reached = False

        try:
            self.stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.config.blocksize,
                callback=self._audio_callback
            )
            self.stream.start()
            self.logger.debug("Начата запись аудио.")
        except Exception as e:
            self._is_recording = False
            if self.stream is not None:
                self.stream.close()
                self.stream = None
            self.logger.error(f"Не удалось инициализировать аудиопоток: {e}")
            raise

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status: sd.CallbackFlags) -> None:
        """
        Callback-функция sounddevice для обработки аудио-блоков.
        Вызывается в отдельном C-потоке.
        Обернута в try-except для безопасности.
        """
        try:
            if status:
                if status.input_overflow:
                    self.logger.warning("Переполнение входного буфера аудиокарты (input overflow). Возможна потеря аудиокадров.")
                else:
                    self.logger.warning(f"Статус аудиопотока: {status}")

            if not self._is_recording:
                return

            if self._frames_recorded + frames > self._max_frames:
                if not self._limit_reached:
                    self.logger.warning(f"Достигнут лимит записи ({self.config.max_recording_duration} сек). Автоматическая остановка захвата.")
                    self._limit_reached = True
                raise sd.CallbackStop()

            # Копируем данные
            self.audio_queue.put(indata.copy())
            self._frames_recorded += frames

        except sd.CallbackStop:
            raise  # Это ожидаемое исключение sounddevice для остановки
        except Exception as e:
            self.logger.error(f"Критическая ошибка внутри аудио callback'а: {e}", exc_info=True)
            # Чтобы не повесить приложение, останавливаем захват
            raise sd.CallbackAbort()

    def stop_recording(self) -> np.ndarray:
        """
        Останавливает запись, собирает аудиоданные, валидирует их и возвращает.
        Гарантированно освобождает ресурсы sounddevice через finally.
        
        Returns:
            np.ndarray: Записанное аудио в виде одномерного массива (float32).
            
        Raises:
            RecordingValidationError: Если запись слишком короткая или состоит из тишины.
        """
        if not self._is_recording:
            self.logger.warning("Попытка остановить запись, которая не была начата (State: IDLE).")
            raise RecordingValidationError("Запись не была начата.")

        try:
            # Корректно закрываем поток и освобождаем ресурсы ОС
            if self.stream is not None:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception as e:
                    self.logger.error(f"Ошибка при закрытии потока sounddevice: {e}")
                finally:
                    self.stream = None
            
            chunks = []
            while not self.audio_queue.empty():
                try:
                    chunks.append(self.audio_queue.get_nowait())
                except queue.Empty:
                    break

            if not chunks:
                raise RecordingValidationError("Нет аудиоданных для обработки (пустая очередь).")

            audio_data = np.concatenate(chunks, axis=0).flatten()

            # Контракт типов: Приводим к float32 на случай сбоев в sounddevice
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            duration = len(audio_data) / self.config.sample_rate
            
            # Валидация: минимальная длительность
            if duration < self.config.min_recording_duration:
                raise RecordingValidationError(f"Запись слишком короткая ({duration:.2f} сек < {self.config.min_recording_duration} сек).")

            # Расчет RMS и максимальной амплитуды
            rms = np.sqrt(np.mean(np.square(audio_data)))
            max_amplitude = np.max(np.abs(audio_data))

            # Валидация: порог тишины
            if rms < self.config.silence_threshold:
                raise RecordingValidationError(f"Запись содержит только тишину (RMS {rms:.4f} < {self.config.silence_threshold}).")

            # Телеметрия
            status_str = "Остановка по лимиту" if self._limit_reached else "Успешно"
            self.logger.info(
                f"Телеметрия записи: Статус='{status_str}', "
                f"Длительность={duration:.2f}с, Кадров={len(audio_data)}, "
                f"RMS={rms:.4f}, MaxAmp={max_amplitude:.4f}, dtype={audio_data.dtype}"
            )

            return audio_data
        
        finally:
            self._is_recording = False
            self._clear_queue() # Окончательная очистка очереди после возврата или исключения
