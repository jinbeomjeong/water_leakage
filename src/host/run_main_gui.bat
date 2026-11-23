@echo off
rem Launch the FT-210 flow rate GUI (main_gui.py) with the python-dev environment of this PC.
rem The environment paths are the ones listed in .claude/rules/python-style.md.

setlocal

set "PIXI_PYTHON=E:\Workspace\python-dev\.pixi\envs\default\python.exe"
set "CONDA_PYTHON=C:\Users\jinbeom\.conda\envs\python-dev\python.exe"

if exist "%PIXI_PYTHON%" (
    set "PYTHON=%PIXI_PYTHON%"
) else if exist "%CONDA_PYTHON%" (
    set "PYTHON=%CONDA_PYTHON%"
) else (
    echo python-dev environment not found:
    echo   %PIXI_PYTHON%
    echo   %CONDA_PYTHON%
    pause
    exit /b 1
)

rem main_gui.py imports its modules relative to src/host, which is the folder of this file
"%PYTHON%" -s "%~dp0main_gui.py"

if errorlevel 1 (
    echo.
    echo main_gui.py exited with error code %errorlevel%
    pause
)

endlocal
