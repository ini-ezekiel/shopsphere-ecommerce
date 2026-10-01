@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.myenv\Scripts\python.exe" (
  echo Run setup.bat first.
  exit /b 1
)

start "ShopSphere API" /D "%~dp0backend" cmd /k ".myenv\Scripts\python.exe manage.py runserver"
start "ShopSphere Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo Django and Vite are starting in separate windows.
echo Storefront: http://127.0.0.1:5173
echo Django admin: http://127.0.0.1:8000/admin/
endlocal
