@echo off
setlocal

set "PROJECT_DIR=%~dp0"
if "%PROJECT_DIR:~-1%"=="\" set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "PYCHARM_EXE=C:\Program Files\JetBrains\PyCharm 2025.3.2.1\bin\pycharm64.exe"

if not exist "%PYCHARM_EXE%" (
  echo [ERROR] PyCharm executable not found:
  echo %PYCHARM_EXE%
  exit /b 1
)

start "" "%PYCHARM_EXE%" "%PROJECT_DIR%"

endlocal
