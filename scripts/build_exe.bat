@echo off
setlocal EnableExtensions

rem Build the standalone Windows executable for the Document to Markdown Converter.
rem Requires the build extra: python -m pip install -e .[build]
rem The result is dist\doc2md.exe.

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_DIR=%%~fI"

pushd "%PROJECT_DIR%"

echo Installing build dependencies...
python -m pip install --disable-pip-version-check -e ".[build]" || goto :error

echo Building standalone executable with PyInstaller...
python -m PyInstaller --noconfirm --clean doc2md.spec || goto :error

echo.
echo Build complete. The executable is at: "%PROJECT_DIR%\dist\doc2md.exe"
popd
exit /b 0

:error
echo.
echo Build failed. See the output above for details.
popd
exit /b 1
