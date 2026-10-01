@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.12 or newer.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found. Install Node.js 20 or newer.
  exit /b 1
)

if not exist "backend\.env" copy "backend\.env.example" "backend\.env" >nul
if not exist "frontend\.env" copy "frontend\.env.example" "frontend\.env" >nul

if not exist "backend\.myenv\Scripts\python.exe" py -m venv backend\.myenv
if errorlevel 1 exit /b 1

call "backend\.myenv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1

python -m pip install -r "backend\requirements.txt"
if errorlevel 1 exit /b 1

pushd backend
python manage.py migrate --noinput
if errorlevel 1 (
  popd
  exit /b 1
)
popd

pushd frontend
call npm ci
if errorlevel 1 (
  popd
  exit /b 1
)
popd

echo.
echo Setup completed successfully.
echo Run start-dev.bat to start Django and React.
endlocal
