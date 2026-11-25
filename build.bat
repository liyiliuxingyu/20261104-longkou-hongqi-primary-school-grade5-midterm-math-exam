@echo off
setlocal
py -3 "%~dp0scripts\build.py" %*
exit /b %ERRORLEVEL%
