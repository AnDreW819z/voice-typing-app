import os
import sys
import site
import warnings

# Подавляем консольный спам от HuggingFace Hub при первой загрузке модели
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_EXPERIMENTAL_WARNING"] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")

# Динамическая загрузка библиотек NVIDIA (cuBLAS, cuDNN) для CTranslate2
try:
    if hasattr(sys, "_MEIPASS"):
        bin_path = os.path.join(sys._MEIPASS, "nvidia", "bin")
        if os.path.exists(bin_path):
            os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(bin_path)
    else:
        site_packages = site.getsitepackages()
        venv_site = os.path.join(sys.prefix, "Lib", "site-packages")
        if venv_site not in site_packages:
            site_packages.append(venv_site)
            
        for sp in site_packages:
            nvidia_path = os.path.join(sp, "nvidia")
            if os.path.exists(nvidia_path):
                for lib in os.listdir(nvidia_path):
                    bin_path = os.path.join(nvidia_path, lib, "bin")
                    if os.path.exists(bin_path):
                        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")
                        if hasattr(os, "add_dll_directory"):
                            os.add_dll_directory(bin_path)
except Exception:
    pass

from app import VoiceTypingApp

def main():
    app = VoiceTypingApp()
    app.run()

if __name__ == "__main__":
    main()
