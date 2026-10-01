@echo off
setlocal
cd /d "%~dp0"

if not exist "backend\.myenv\Scripts\python.exe" (
  echo Run setup.bat first.
  exit /b 1
)

pushd backend
".myenv\Scripts\python.exe" manage.py check
if errorlevel 1 exit /b 1
".myenv\Scripts\python.exe" manage.py makemigrations --check --dry-run
if errorlevel 1 exit /b 1
".myenv\Scripts\python.exe" manage.py test
if errorlevel 1 exit /b 1
popd

pushd frontend
call npm run lint
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1
popd

echo All verification checks passed.
endlocal
