# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

datas = []

path = os.getcwd()

a = Analysis(['scicall/__main__.py'],
             pathex=[path],
             binaries=[],
             datas=datas,
             hiddenimports=["PyQt5", "PyQt5.sip"],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='SciCall.exe' if sys.platform == "win32" else 'SciCall',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='SciCall')
