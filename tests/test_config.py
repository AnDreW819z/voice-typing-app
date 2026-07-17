import json
import pytest
from pathlib import Path
from pydantic import ValidationError
from config import AppConfig

def test_app_config_defaults():
    config = AppConfig()
    assert config.hotkey == "f8"
    assert config.language == "ru"
    assert config.model == "large-v3-turbo"
    assert config.config_version == 1

def test_app_config_load(tmp_path: Path):
    config_file = tmp_path / "config.json"
    test_data = {
        "config_version": 1,
        "hotkey": "ctrl+space",
        "language": "en",
        "model": "large-v3-turbo",
        "device": "cuda",
        "compute_type": "float16",
        "sample_rate": 16000,
        "model_dir": "models"
    }
    with config_file.open("w", encoding="utf-8") as f:
        json.dump(test_data, f)
        
    config = AppConfig.load(config_file)
    assert config.hotkey == "ctrl+space"
    assert config.language == "en"
    assert config.model == "large-v3-turbo"

def test_app_config_validation_error(tmp_path: Path):
    config_file = tmp_path / "config.json"
    test_data = {
        "sample_rate": -100 # Invalid sample rate
    }
    with config_file.open("w", encoding="utf-8") as f:
        json.dump(test_data, f)
        
    with pytest.raises(SystemExit):
        AppConfig.load(config_file)
