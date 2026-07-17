import pytest
import numpy as np
import logging
from unittest.mock import patch, MagicMock

from config import AppConfig
from services.recorder import Recorder, RecordingValidationError

@pytest.fixture
def dummy_config():
    return AppConfig(
        sample_rate=16000,
        min_recording_duration=0.1,
        max_recording_duration=1.0,
        silence_threshold=0.01
    )

@pytest.fixture
def dummy_logger():
    return logging.getLogger("TestRecorder")

@pytest.fixture
def recorder(dummy_config, dummy_logger):
    with patch("services.recorder.sd.InputStream") as mock_stream:
        # Mock instance
        instance = MagicMock()
        mock_stream.return_value = instance
        yield Recorder(dummy_config, dummy_logger)

def test_recorder_state_machine(recorder):
    assert not recorder._is_recording
    
    # 1. Обычный старт
    recorder.start_recording()
    assert recorder._is_recording
    assert recorder.stream is not None
    
    # 2. Двойной старт (не должно ломать логику, игнорируется)
    recorder.start_recording()
    assert recorder._is_recording
    
    # 3. Нормальный стоп (с имитацией данных)
    dummy_data = np.ones(16000, dtype=np.float32) * 0.5 
    recorder.audio_queue.put(dummy_data)
    
    audio = recorder.stop_recording()
    assert not recorder._is_recording
    assert recorder.stream is None
    assert audio.dtype == np.float32
    assert len(audio) == 16000
    
    # 4. Двойной стоп (должен выкинуть исключение)
    with pytest.raises(RecordingValidationError, match="Запись не была начата"):
        recorder.stop_recording()

def test_recorder_validation_too_short(recorder):
    recorder.start_recording()
    
    # Имитируем слишком короткие данные (< 0.1 сек)
    dummy_data = np.ones(100, dtype=np.float32) * 0.5 
    recorder.audio_queue.put(dummy_data)
    
    with pytest.raises(RecordingValidationError, match="слишком короткая"):
        recorder.stop_recording()
        
    # Проверяем, что после исключения очередь очищена и состояние сброшено
    assert not recorder._is_recording
    assert recorder.audio_queue.empty()

def test_recorder_validation_silence(recorder):
    recorder.start_recording()
    
    # Имитируем тишину (RMS < 0.01)
    dummy_data = np.zeros(16000, dtype=np.float32) 
    recorder.audio_queue.put(dummy_data)
    
    with pytest.raises(RecordingValidationError, match="содержит только тишину"):
        recorder.stop_recording()
        
    assert not recorder._is_recording
    assert recorder.audio_queue.empty()
