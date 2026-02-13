@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo [ERROR] .venv Python not found: %PYTHON_EXE%
  echo Create venv first: py -m venv .venv
  exit /b 1
)

pushd "%PROJECT_ROOT%"
"%PYTHON_EXE%" -m streamlit run app.py
popd

endlocal
