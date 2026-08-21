@echo off
REM ============================================================
REM Day18 Plan C: one-click UI test runner (Windows)
REM Usage: run full UI test suite -> generate Allure report
REM        -> keep history (trend continuity) -> open report
REM Note : API tests already run on server Jenkins CI; UI tests
REM        stay local due to 4G server memory limit.
REM        CI decision record: see docs/ (Chinese filename, Day18)
REM ============================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv\Scripts\python.exe not found. Init venv per README first.
    exit /b 1
)
if not exist ".env" (
    echo [ERROR] .env not found. Copy .env.example first.
    exit /b 1
)

echo [1/4] keep previous report history (Allure trend continuity)
if exist "allure-report\history" (
    if not exist "allure-results" mkdir "allure-results"
    xcopy /e /y /q "allure-report\history" "allure-results\history\" >nul
    echo       history kept
) else (
    echo       first run, no history yet
)

echo [2/4] run full UI test suite (headless; auto-retry 1x on timeout/network, ~105s)
.venv\Scripts\python.exe -m pytest testcases/
set PYTEST_EXIT=%errorlevel%

echo [3/4] generate Allure report (allure-results -> allure-report)
where allure >nul 2>nul
if %errorlevel%==0 (
    allure generate allure-results -o allure-report --clean
) else (
    echo [WARN] allure CLI not found on PATH, skip report generation
)

echo [4/4] open report (Allure is a SPA, serve via local HTTP on port 8123)
start "allure-report-server" cmd /c ".venv\Scripts\python.exe -m http.server 8123 --directory allure-report"
timeout /t 2 >nul
start "" "http://localhost:8123"

echo.
if "%PYTEST_EXIT%"=="0" (
    echo ============ ALL UI TESTS PASSED ============
) else (
    echo ============ SOME TESTS FAILED, see output and report ============
)
exit /b %PYTEST_EXIT%
