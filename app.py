import sys
import time
import queue
import logging
import threading
from pathlib import Path

from config import AppConfig
from logger import setup_logger
from state import AppState
from services.recorder import Recorder, RecordingValidationError
from services.transcriber import WhisperTranscriber
from services.keyboard_listener import KeyboardListener
from services.text_output import TextOutput


class VoiceTypingApp:
    """
    Главный класс приложения.
    Управляет жизненным циклом, инициализацией подсистем и координацией потоков.
    """
    def __init__(self):
        self.state = AppState.IDLE
        self.logger = setup_logger("VoiceTypingApp")
        
        # Сначала логгер, затем конфиг (чтобы конфиг мог логировать ошибки)
        self.config_path = Path("config.json")
        self.config = AppConfig.load(self.config_path)
        self.logger.info("[✔] Config loaded")
        
        # Dependency Injection
        self.recorder = Recorder(self.config, self.logger)
        self.transcriber = WhisperTranscriber(self.config, self.logger)
        self.keyboard_listener = KeyboardListener(self.config, self.logger)
        self.text_output = TextOutput(self.config, self.logger)
        
        # Очереди для потокобезопасной передачи аудио на распознавание
        self.audio_queue = queue.Queue()
        self.is_running = False
        
        self._press_time = 0.0
        self._release_time = 0.0
        self._last_reaction_time = 0.0

    def set_state(self, new_state: AppState) -> None:
        """Меняет глобальное состояние приложения и логирует это."""
        self.logger.info(f"Смена состояния: {self.state.name} -> {new_state.name}")
        self.state = new_state

    def start(self) -> None:
        """Запускает приложение, инициализирует подсистемы."""
        self.logger.info("Инициализация приложения...")
        
        try:
            self.transcriber.load_model()
        except Exception as e:
            self.logger.error(f"Фатальная ошибка загрузки модели. Приложение не может продолжить работу: {e}")
            sys.exit(1)
        
        self.keyboard_listener.register_hotkey(
            hotkey=self.config.hotkey,
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release
        )
        self.is_running = True
        
        # Запуск фонового потока обработки очереди
        threading.Thread(target=self._transcribe_worker, daemon=True).start()
        
        try:
            self.keyboard_listener.start()
        except Exception as e:
            self.logger.error(f"Фатальная ошибка: не удалось захватить горячую клавишу {self.config.hotkey}: {e}")
            sys.exit(1)
            
        self.logger.info("[✔] Audio device and Keyboard hooks ready")
        self.logger.info("Приложение готово к работе.")

    def stop(self) -> None:
        """Корректно останавливает потоки и подсистемы."""
        self.logger.info("Остановка приложения...")
        self.is_running = False
        self.keyboard_listener.stop()

    def run(self) -> None:
        """Главный цикл приложения, блокирующий выход."""
        try:
            self.start()
            while self.is_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            self.set_state(AppState.ERROR)
            self.logger.error(f"Критическая ошибка: {e}", exc_info=True)
            self.stop()

    def _on_hotkey_press(self) -> None:
        """Коллбек, срабатывающий при нажатии горячей клавиши."""
        self._press_time = time.perf_counter()
        if self.state == AppState.IDLE:
            try:
                self.set_state(AppState.RECORDING)
                self.recorder.start_recording()
                self._last_reaction_time = time.perf_counter() - self._press_time
            except Exception as e:
                self.logger.error(f"Сбой при старте записи (возможно, микрофон отключен): {e}", exc_info=True)
                self.set_state(AppState.IDLE)

    def _on_hotkey_release(self) -> None:
        """Коллбек, срабатывающий при отпускании горячей клавиши."""
        self._release_time = time.perf_counter()
        if self.state == AppState.RECORDING:
            try:
                audio_data = self.recorder.stop_recording()
                # Передаем аудио, время отпускания и время реакции в очередь
                self.audio_queue.put((audio_data, self._release_time, self._last_reaction_time))
                self.set_state(AppState.TRANSCRIBING)
            except RecordingValidationError as e:
                self.logger.warning(f"Запись отбракована: {e}")
                self.set_state(AppState.IDLE)
            except Exception as e:
                self.logger.error(f"Неожиданная ошибка при остановке записи: {e}", exc_info=True)
                self.set_state(AppState.IDLE)

    def _transcribe_worker(self) -> None:
        """Фоновый поток для распознавания аудио из очереди."""
        while self.is_running:
            try:
                item = self.audio_queue.get(timeout=0.5)
                if item is not None:
                    audio_data, release_time, reaction_time = item
                    
                    processing_time = time.perf_counter() - release_time
                    
                    inf_start = time.perf_counter()
                    result = self.transcriber.transcribe(audio_data)
                    inf_time = time.perf_counter() - inf_start
                    
                    out_time = 0.0
                    if result and result.text:
                        out_start = time.perf_counter()
                        success = self.text_output.output_text(result.text)
                        if success:
                            out_time = time.perf_counter() - out_start
                            
                        total_time = reaction_time + processing_time + inf_time + out_time
                        log_msg = (
                            "\n"
                            f"    Reaction:   {reaction_time*1000:4.0f} ms\n"
                            f"    Processing: {processing_time*1000:4.0f} ms\n"
                            f"    Inference:  {inf_time*1000:4.0f} ms\n"
                            f"    Output:     {out_time*1000:4.0f} ms\n"
                            f"    --------------------------------\n"
                            f"    Total:      {total_time*1000:4.0f} ms"
                        )
                        self.logger.info(log_msg)
                    
                    self.set_state(AppState.IDLE)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Сбой во время фоновой обработки (инференс/вывод): {e}", exc_info=True)
                self.set_state(AppState.IDLE)
