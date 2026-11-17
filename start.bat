@echo off
rem Starts Spotify Sound Companion (API + frontend) in one window.
rem Open http://127.0.0.1:5173 when both are ready. Ctrl+C stops both.
cd /d "%~dp0frontend"
if not exist node_modules (
  echo Installing frontend dependencies first...
  call npm install || exit /b 1
)
npm run dev
