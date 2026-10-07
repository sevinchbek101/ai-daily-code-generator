@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 daily_code_agent.py > last-run.log 2>&1
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% NEQ 0 (
        echo XATO: Python 3 topilmadi. README.md bo'yicha Python o'rnating.
        set "AGENT_EXIT=1"
        goto :done
    )
    python daily_code_agent.py > last-run.log 2>&1
)
set "AGENT_EXIT=%ERRORLEVEL%"
if exist last-run.log type last-run.log
:done
echo.
if "%AGENT_EXIT%"=="0" (echo Agent muvaffaqiyatli yakunlandi.) else (echo Agent xato bilan yakunlandi. Kod: %AGENT_EXIT%)
if not defined DAILYCODE_SCHEDULED pause
exit /b %AGENT_EXIT%
