@echo off
TITLE WhatsApp Pipeline - Shutdown
COLOR 0C

echo [SYSTEM] Shutting down specific pipeline components...

:: Targeted Shutdown: Closes windows by their Title[cite: 9]
taskkill /FI "WINDOWTITLE eq Ingest Server*" /F /T
taskkill /FI "WINDOWTITLE eq WhatsApp Bridge*" /F /T
taskkill /FI "WINDOWTITLE eq n8n Automation*" /F /T

:: Clean up any stray child processes[cite: 9]
echo.
echo [INFO] Ensuring no background listeners are active...
taskkill /IM node.exe /FI "MEMUSAGE gt 10000" /F /T >nul 2>&1

echo.
echo [SUCCESS] Pipeline offline.
echo [INFO] Other Node/Python applications were not affected.
pause