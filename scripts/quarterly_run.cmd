@echo off
rem quarterly_run.cmd - double-click (Windows) = one quarterly round: uv run atlas quarterly
rem   uses pipeline\config.yaml (input.path = this round's corpus) and the quarter of today
rem   extra options can follow, e.g.  scripts\quarterly_run.cmd --corpus D:\atlas-data\corpus\2026Q4 --release 2026Q4
rem   guide: docs\OPERATIONS.md section 1
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0..\pipeline"
uv run atlas quarterly %*
set CODE=%ERRORLEVEL%
echo.
if %CODE%==0 (echo [quarterly] finished - see runs\ and deploy\) else (echo [quarterly] stopped with exit code %CODE% - read the message above)
pause
exit /b %CODE%
