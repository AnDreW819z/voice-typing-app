from pathlib import Path
from logger import setup_logger

def test_setup_logger(tmp_path: Path):
    log_dir = tmp_path / "logs"
    logger = setup_logger("TestLogger", log_dir=log_dir)
    
    assert logger.name == "TestLogger"
    assert log_dir.exists()
    assert (log_dir / "app.log").exists()
