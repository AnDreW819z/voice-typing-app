import os
import warnings

# Подавляем консольный спам от HuggingFace Hub при первой загрузке модели
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

from app import VoiceTypingApp

def main():
    app = VoiceTypingApp()
    app.run()

if __name__ == "__main__":
    main()
