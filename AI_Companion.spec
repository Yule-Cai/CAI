# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\caiyule\\AppData\\Roaming\\Python\\Python313\\site-packages\\llama_cpp', 'llama_cpp'), ('C:\\Users\\caiyule\\Desktop\\CAI\\models', 'models'), ('C:\\Users\\caiyule\\Desktop\\CAI\\tts_model', 'tts_model')]
binaries = []
hiddenimports = ['services', 'services.local_llm_service', 'services.sherpa_service', 'core.cai_brain', 'llama_cpp', 'sherpa_onnx', 'sounddevice']
tmp_ret = collect_all('llama_cpp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['ui_module.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI_Companion',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI_Companion',
)
