@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "PY_FILE=%SCRIPT_DIR%2 - script_pdf_to_markdown.py"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"
set "LOG_FILE=%SCRIPT_DIR%pdf_to_md_launcher.log"
set "VBS_FILE=%TEMP%\pdf_to_md_launcher_%RANDOM%%RANDOM%.vbs"
set "PYTHON_EXE="

if not exist "%PY_FILE%" (
    >"%LOG_FILE%" echo Script not found: "%PY_FILE%"
    exit /b 1
)

for /f "delims=" %%P in ('where python.exe 2^>nul') do (
    echo %%P | findstr /I /C:"WindowsApps" >nul
    if errorlevel 1 if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
)

if not defined PYTHON_EXE (
    >"%LOG_FILE%" echo Could not find a real python.exe in PATH. WindowsApps aliases were ignored.
    exit /b 1
)

>"%LOG_FILE%" echo Preparing "%PY_FILE%" with "%PYTHON_EXE%".

if not exist "%REQUIREMENTS_FILE%" (
    >>"%LOG_FILE%" echo Requirements file not found: "%REQUIREMENTS_FILE%"
    exit /b 1
)

>>"%LOG_FILE%" echo Checking and installing required Python packages from "%REQUIREMENTS_FILE%".
"%PYTHON_EXE%" -m pip install --disable-pip-version-check -r "%REQUIREMENTS_FILE%" >>"%LOG_FILE%" 2>>&1
if errorlevel 1 (
    >>"%LOG_FILE%" echo Failed to install required Python packages. The application was not started.
    exit /b 1
)

>>"%LOG_FILE%" echo Requirements are ready. Launching application.

>"%VBS_FILE%" echo Set shell = CreateObject("WScript.Shell")
>>"%VBS_FILE%" echo quote = Chr(34)
>>"%VBS_FILE%" echo pythonExe = "%PYTHON_EXE%"
>>"%VBS_FILE%" echo scriptFile = "%PY_FILE%"
>>"%VBS_FILE%" echo logFile = "%LOG_FILE%"
>>"%VBS_FILE%" echo shell.CurrentDirectory = "%SCRIPT_DIR%"
>>"%VBS_FILE%" echo command = "cmd.exe /d /s /c " ^& quote ^& quote ^& pythonExe ^& quote ^& " " ^& quote ^& scriptFile ^& quote ^& " 1^>^> " ^& quote ^& logFile ^& quote ^& " 2^>^&1" ^& quote
>>"%VBS_FILE%" echo shell.Run command, 0, False

"%SystemRoot%\System32\wscript.exe" "%VBS_FILE%"
set "LAUNCH_RESULT=%ERRORLEVEL%"
del "%VBS_FILE%" >nul 2>&1
exit /b %LAUNCH_RESULT%
