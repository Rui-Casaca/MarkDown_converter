@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Launcher helper for the Document to Markdown Converter.
rem On first run it creates a local virtual environment (.venv) and installs the
rem doc2md package into it. On later runs it reuses that environment and only
rem reinstalls when the package version changes, so no network access or pip run
rem is needed for a normal launch. The GUI then starts without a console window.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_DIR=%%~fI"
set "LOG_FILE=%SCRIPT_DIR%pdf_to_md_launcher.log"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "STAMP_FILE=%VENV_DIR%\doc2md-version.txt"
set "VBS_FILE=%TEMP%\pdf_to_md_launcher_%RANDOM%%RANDOM%.vbs"

>"%LOG_FILE%" echo Starting Document to Markdown Converter launcher.

rem 1. Create the virtual environment on first run using a real python.exe
rem    (Windows Store aliases under WindowsApps are ignored).
if not exist "%VENV_PY%" (
    set "SYSTEM_PYTHON="
    for /f "delims=" %%P in ('where python.exe 2^>nul') do (
        echo %%P | findstr /I /C:"WindowsApps" >nul
        if errorlevel 1 if not defined SYSTEM_PYTHON set "SYSTEM_PYTHON=%%P"
    )
    if not defined SYSTEM_PYTHON (
        >>"%LOG_FILE%" echo Could not find a real python.exe in PATH. WindowsApps aliases were ignored.
        exit /b 1
    )
    >>"%LOG_FILE%" echo Creating virtual environment with "!SYSTEM_PYTHON!".
    "!SYSTEM_PYTHON!" -m venv "%VENV_DIR%" >>"%LOG_FILE%" 2>>&1
    if errorlevel 1 (
        >>"%LOG_FILE%" echo Failed to create the virtual environment.
        exit /b 1
    )
)

if not exist "%VENV_PY%" (
    >>"%LOG_FILE%" echo Virtual environment Python was not found after creation.
    exit /b 1
)

rem 2. Read the source package version (doc2md.__init__ has no heavy imports).
set "VERSION_TMP=%TEMP%\doc2md_version_%RANDOM%%RANDOM%.txt"
"%VENV_PY%" -c "import sys; sys.path.insert(0, r'%PROJECT_DIR%\src'); import doc2md; print(doc2md.__version__)" >"%VERSION_TMP%" 2>nul
set "SRC_VERSION="
if exist "%VERSION_TMP%" set /p SRC_VERSION=<"%VERSION_TMP%"
del "%VERSION_TMP%" >nul 2>&1

rem 3. Decide whether installation is required.
set "NEED_INSTALL=1"
if exist "%STAMP_FILE%" (
    set "STAMP_VERSION="
    set /p STAMP_VERSION=<"%STAMP_FILE%"
    if defined SRC_VERSION if "!STAMP_VERSION!"=="!SRC_VERSION!" set "NEED_INSTALL=0"
)
if "!NEED_INSTALL!"=="0" (
    "%VENV_PY%" -c "import doc2md" >nul 2>&1
    if errorlevel 1 set "NEED_INSTALL=1"
)

rem 4. Install the package into the virtual environment when required.
if "!NEED_INSTALL!"=="1" (
    >>"%LOG_FILE%" echo Installing doc2md into the virtual environment. This can take a moment on the first run.
    "%VENV_PY%" -m pip install --disable-pip-version-check -e "%PROJECT_DIR%" >>"%LOG_FILE%" 2>>&1
    if errorlevel 1 (
        >>"%LOG_FILE%" echo Failed to install doc2md. The application was not started.
        exit /b 1
    )
    if defined SRC_VERSION >"%STAMP_FILE%" echo !SRC_VERSION!
) else (
    >>"%LOG_FILE%" echo doc2md !SRC_VERSION! is already installed. Skipping installation.
)

>>"%LOG_FILE%" echo Launching application.

>"%VBS_FILE%" echo Set shell = CreateObject("WScript.Shell")
>>"%VBS_FILE%" echo quote = Chr(34)
>>"%VBS_FILE%" echo pythonExe = "%VENV_PY%"
>>"%VBS_FILE%" echo projectDir = "%PROJECT_DIR%"
>>"%VBS_FILE%" echo logFile = "%LOG_FILE%"
>>"%VBS_FILE%" echo shell.CurrentDirectory = projectDir
>>"%VBS_FILE%" echo command = "cmd.exe /d /s /c " ^& quote ^& quote ^& pythonExe ^& quote ^& " -m doc2md 1^>^> " ^& quote ^& logFile ^& quote ^& " 2^>^&1" ^& quote
>>"%VBS_FILE%" echo shell.Run command, 0, False

"%SystemRoot%\System32\wscript.exe" "%VBS_FILE%"
set "LAUNCH_RESULT=%ERRORLEVEL%"
del "%VBS_FILE%" >nul 2>&1
exit /b %LAUNCH_RESULT%
