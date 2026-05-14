@echo off
pyinstaller --noconsole --onefile --collect-data customtkinter --hidden-import pystray._win32 --icon icon.ico --name TGBlaster --distpath . --workpath build --specpath . main.py
echo.
echo === Build complete: TGBlaster.exe ===
pause
