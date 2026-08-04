@echo off
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\Users\ASUS\AppData\Local\Google\Chrome\User Data" --disable-blink-features=AutomationControlled --no-first-run --no-default-browser-check
echo Chrome started with CDP on port 9222