# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

import os
import sys
import glob

# Собираем скрытые импорты для CTranslate2 / faster-whisper и других библиотек
hidden_imports = collect_submodules('faster_whisper') + [
    'sounddevice', 
    'numpy', 
    'keyboard',
    'pydantic'
]

# Копируем бинарные зависимости (словари, токены)
datas = collect_data_files('faster_whisper')

# Собираем DLL NVIDIA (cuBLAS, cuDNN) из окружения для standalone CUDA
nvidia_binaries = []
venv_site = os.path.join(sys.prefix, "Lib", "site-packages")
nvidia_path = os.path.join(venv_site, "nvidia")
if os.path.exists(nvidia_path):
    for lib in os.listdir(nvidia_path):
        bin_path = os.path.join(nvidia_path, lib, "bin")
        if os.path.exists(bin_path):
            for dll in glob.glob(os.path.join(bin_path, "*.dll")):
                nvidia_binaries.append((dll, 'nvidia/bin'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=nvidia_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='VoiceTyping',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Консоль отключена для фоновой работы
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
