@echo off
cd /d "%~dp0"

set PY=python
%PY% --version >nul 2>nul || set PY=py
%PY% --version >nul 2>nul || (echo Python was not found. Install Python from python.org and check Add python.exe to PATH. & pause & exit /b 1)

for %%F in (installer.py main.py uninstall.py i18n.py icon.ico) do if not exist %%F (echo %%F was not found in this folder. & pause & exit /b 1)

echo [1/2] Installing PyInstaller...
%PY% -m pip install -U pyinstaller || (echo Package install failed. & pause & exit /b 1)

echo [2/2] Building YDL-setup.exe...
set WORK=%TEMP%\ydl_setup_build
%PY% -m PyInstaller --onefile --noconsole --clean --noconfirm --name YDL-setup --icon "%~dp0icon.ico" --add-data "%~dp0main.py;." --add-data "%~dp0uninstall.py;." --add-data "%~dp0i18n.py;." --add-data "%~dp0icon.ico;." --distpath "." --workpath "%WORK%" --specpath "%WORK%" "%~dp0installer.py"
set RESULT=%errorlevel%

rmdir /s /q "%WORK%" 2>nul

if not %RESULT%==0 (echo Build failed. See the messages above. & pause & exit /b 1)
if not exist YDL-setup.exe (echo YDL-setup.exe was not created. & pause & exit /b 1)

explorer /select,"%~dp0YDL-setup.exe"
exit /b 0