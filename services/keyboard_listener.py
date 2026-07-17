"""
services/keyboard_listener.py

Модуль для обработки глобальных горячих клавиш.
Реализует абстракцию HotkeyProvider с защитой от спама/key_repeat.
"""

import logging
import threading
import keyboard
from typing import Callable, Protocol, Optional

class HotkeyProvider(Protocol):
    """
    Интерфейс для провайдера горячих клавиш.
    Обеспечивает независимость от конкретной библиотеки.
    """
    def register_hotkey(self, hotkey: str, on_press: Callable, on_release: Callable) -> None:
        """Регистрирует обработчики нажатия и отпускания горячей клавиши."""
        ...

    def start(self) -> None:
        """Запускает прослушивание."""
        ...

    def stop(self) -> None:
        """Останавливает прослушивание."""
        ...

class KeyboardListener(HotkeyProvider):
    """
    Реализация HotkeyProvider на базе библиотеки keyboard.
    Обеспечивает debounce-логику и устранение key_repeat ОС.
    """
    def __init__(self, config, logger: logging.Logger):
        """
        Инициализирует слушатель клавиатуры.
        
        Args:
            config: Конфигурация приложения.
            logger: Инстанс логгера.
        """
        self.config = config
        self.logger = logger
        
        self._is_pressed = False
        self._lock = threading.Lock()
        
        self._hotkey: Optional[str] = None
        self._on_press_cb: Optional[Callable] = None
        self._on_release_cb: Optional[Callable] = None
        self._listening = False
        
        self._press_hook = None
        self._release_hook = None

    def register_hotkey(self, hotkey: str, on_press: Callable, on_release: Callable) -> None:
        """Регистрирует функции обратного вызова."""
        self._hotkey = hotkey
        self._on_press_cb = on_press
        self._on_release_cb = on_release

    def start(self) -> None:
        """Запускает прослушивание горячих клавиш."""
        if not self._hotkey:
            self.logger.error("Невозможно запустить слушатель: горячая клавиша не зарегистрирована.")
            return
            
        if self._listening:
            return

        with self._lock:
            self._is_pressed = False
            
            # Регистрируем хуки с учетом флага suppress из конфига
            suppress = getattr(self.config, 'suppress_hotkey', True)
            self._press_hook = keyboard.on_press_key(self._hotkey, self._handle_press, suppress=suppress)
            self._release_hook = keyboard.on_release_key(self._hotkey, self._handle_release, suppress=suppress)
            
            self._listening = True
            self.logger.debug(f"Начато прослушивание горячей клавиши: {self._hotkey}")

    def stop(self) -> None:
        """Останавливает прослушивание горячих клавиш."""
        if not self._listening:
            return
            
        with self._lock:
            if self._press_hook is not None:
                try:
                    keyboard.unhook(self._press_hook)
                except KeyError:
                    pass
                self._press_hook = None
            if self._release_hook is not None:
                try:
                    keyboard.unhook(self._release_hook)
                except KeyError:
                    pass
                self._release_hook = None
                
            self._listening = False
            self._is_pressed = False
            self.logger.debug("Прослушивание горячих клавиш остановлено.")

    def _handle_press(self, event) -> None:
        """Внутренний коллбек нажатия с защитой от залипания (debounce)."""
        with self._lock:
            if not self._is_pressed:
                self._is_pressed = True
                if self._on_press_cb:
                    self._on_press_cb()

    def _handle_release(self, event) -> None:
        """Внутренний коллбек отпускания."""
        with self._lock:
            if self._is_pressed:
                self._is_pressed = False
                if self._on_release_cb:
                    self._on_release_cb()
