# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-17

### Added
- **Global Architecture**: Implement State Machine (`AppState`), strictly separated layers (Recorder -> Transcriber -> TextOutput -> App), and Dependency Injection via `main.py` (`app.py`).
- **Recorder (Audio Capture)**: 
  - Non-blocking asynchronous audio recording using `sounddevice` Streams and C-thread callbacks.
  - In-memory `float32` audio processing via `numpy` (`Zero-Disk I/O`).
  - Validation metrics: silence threshold (`RMS`) and `min_recording_duration` checks.
- **Transcriber (ML Core)**:
  - Integration of `faster-whisper` (`large-v3-turbo` model by default).
  - Implement Singleton `WhisperModelManager` with `threading.Lock` for strict once-only loading and Thread-Safe environment.
  - Implement isolated `_warmup` logic to populate VRAM and cache computing graphs proactively.
  - Advanced ML Telemetry logs (RTF, Words/sec, Chars/sec).
- **Text Output (OS Integration)**:
  - OS text insertion mechanism using `keyboard.write()`. Ensures seamless text input independently from the user's active keyboard layout.
- **Input Control (Keyboard Hook)**:
  - Global Hotkey capture with Push-To-Talk logic (defaults to `F8`).
  - Debounce logic avoiding Windows Key Repeat spam (`keydown` storm).
- **Configuration & Logging**:
  - `Pydantic` v2 configuration model tied with `config.json`.
  - Comprehensive rotational file logger alongside stream output.
  - Graceful hardware fallback functionality: Automatically shifts from CUDA (`float16`) to CPU (`int8`) upon initialization failures.
- **Telemetry**: 
  - End-to-End latency metrics output detailing *Reaction*, *Processing*, *Inference*, *Output*, and *Total Pipeline Time*.
- **Build Configurations**: Included `.spec` format ready for `PyInstaller` `.exe` compilation, tracking implicit `ctranslate2` dependencies.

### Changed
- Refactored `transcriber.py` to use an immutable Data Transfer Object (`TranscriptionResult`) via `@dataclass(frozen=True, slots=True)` instead of raw string returns.

### Fixed
- Fixed audio bleeding issue between dictations: `Queue` buffers are fully purged upon initialization and destruction.
- Addressed zero division edge case ensuring safe computing for RTF properties where audio duration strictly > 0.
