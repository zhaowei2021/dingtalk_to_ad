@echo off
set SCRIPT_NAME=main.py
set LOG_FILE=output.log
set PID_FILE=main.pid

REM Function to start the script
:start
if exist %PID_FILE% (
    echo Script is already running.
    exit /b 1
)
echo Starting script...
start /b python %SCRIPT_NAME% > %LOG_FILE% 2>&1
echo %! > %PID_FILE%
exit /b 0

REM Function to restart the script
:restart
call :stop
timeout /t 2 /nobreak > nul
call :start
exit /b 0

REM Function to stop the script
:stop
if not exist %PID_FILE% (
    echo Script is not running.
    exit /b 1
)
for /f "usebackq" %%a in (%PID_FILE%) do (
    taskkill /f /pid %%a
)
del %PID_FILE%
echo Script stopped.
exit /b 0

REM Main logic
if "%1"=="start" (
    call :start
) else if "%1"=="restart" (
    call :restart
) else if "%1"=="stop" (
    call :stop
) else (
    echo Invalid parameter. Use start, restart, or stop.
    exit /b 1
)
