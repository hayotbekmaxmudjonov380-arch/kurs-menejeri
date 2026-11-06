@echo off
title Kurs Manager - yangilanish chiqarish
echo ==================================================
echo    Kurs Manager - yangilanish chiqarish
echo    (3 ta build -^> GitHub Release -^> updates.json)
echo ==================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\release.ps1" %*
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo.
  echo ==================================================
  echo    XATO bilan tugadi. Yuqoridagi xabarni oqing.
  echo ==================================================
)
echo.
pause
exit /b %RC%
