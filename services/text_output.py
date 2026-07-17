"""
services/text_output.py

Модуль для интеграции распознанного текста в активное окно ОС.
Изолирует логику ввода и обеспечивает безопасную деградацию при ошибках.
"""

import logging
import keyboard

class TextOutput:
    """
    Класс для вывода текста в активное окно.
    Скрывает детали реализации ввода (эмуляция клавиатуры).
    """
    def __init__(self, config, logger: logging.Logger):
        """
        Инициализирует модуль вывода текста.
        
        Args:
            config: Конфигурация приложения.
            logger: Инстанс логгера.
        """
        self.config = config
        self.logger = logger
        
    def output_text(self, text: str) -> bool:
        """
        Выводит текст в активное окно ОС.
        
        Стратегия: Прямая эмуляция клавиатурных событий через библиотеку `keyboard`.
        
        Args:
            text: Распознанный текст для вывода.
            
        Returns:
            bool: True если вывод успешен, False если произошла ошибка.
        """
        if not text:
            self.logger.debug("Пустой текст для вывода. Пропуск.")
            return True
            
        try:
            formatted_text = text
            if getattr(self.config, 'append_trailing_space', True):
                formatted_text += " "
            
            # Эмуляция ввода. 
            # keyboard.write на Windows использует флаг KEYEVENTF_UNICODE под капотом.
            # Работает "из коробки" мгновенно, без задержек.
            keyboard.write(formatted_text)
            
            self.logger.debug(f"Текст успешно напечатан ({len(formatted_text)} символов).")
            return True
            
        except Exception as e:
            # Детализация ошибки (напр. отклонение ввода из-за UAC или неактивного окна)
            self.logger.error(f"Failed: target window rejected input (эмуляция отклонена ОС). Ошибка: {e}", exc_info=True)
            return False
