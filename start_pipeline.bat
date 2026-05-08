@echo off
TITLE WhatsApp Behavioral Pipeline - sequential launch
COLOR 0B

:: 1. Launch n8n
echo [1/4] Launching n8n Workflow Engine...
start "n8n Automation" cmd /k "n8n"
timeout /t 8 /nobreak > nul

:: 2. Launch Ingest
echo [2/4] Launching Ingest Server...
start "Ingest Server" cmd /k "cd /d C:\WhatsappBridge\Ingestion && python ingest.py"
timeout /t 10 /nobreak > nul

:: 3. Run Health Check
echo [3/4] Verifying Handshakes...
python C:\WhatsAppBridge\pipeline_health.py
if %errorlevel% neq 0 (
    echo HANDSHAKE FAILED. Correct errors above before continuing.
    pause
    exit
)

:: 4. Launch Bridge
echo [4/4] Launching WhatsApp Bridge...
start "WhatsApp Bridge" cmd /k "cd /d C:\WhatsappBridge && node listener.js"

echo ===================================================
echo   PIPELINE FULLY CONSOLIDATED & VERIFIED
echo ===================================================
pause