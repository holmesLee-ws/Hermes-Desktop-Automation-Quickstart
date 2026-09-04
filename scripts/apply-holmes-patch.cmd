@echo off
setlocal

set "PATCH_SCRIPT=%~dp0apply-holmes-patch.py"
set "HERMES_PYTHON=%LOCALAPPDATA%\hermes\hermes-agent\venv\Scripts\python.exe"

if exist "%HERMES_PYTHON%" (
  "%HERMES_PYTHON%" "%PATCH_SCRIPT%" %*
) else (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 "%PATCH_SCRIPT%" %*
  ) else (
    python "%PATCH_SCRIPT%" %*
  )
)

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Patch failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
