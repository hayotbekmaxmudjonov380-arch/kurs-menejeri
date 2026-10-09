@echo off
chcp 65001 >nul
setlocal
set "APP=C:\Users\HP Victus\OneDrive\Desktop\kurs_uchun_dastur"

netstat -an | find ":5000" | find "LISTENING" >nul
if errorlevel 1 (
  echo Server ishga tushmoqda...
  start "KursManager" cmd /k "cd /d \"%APP%\" && python web/app.py"
  timeout /t 6 /nobreak >nul
) else (
  echo Server allaqachon ishlayapti.
)
start http://127.0.0.1:5000
echo Tayyor: http://127.0.0.1:5000
