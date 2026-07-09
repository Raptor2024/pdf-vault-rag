@echo off
title PDF to Markdown converter
echo ============================================================
echo  Converting every PDF in "PDF Inbox" to Markdown,
echo  then updating the search index.
echo.
echo  Large scanned books can take a LONG time (up to an hour
echo  each). Leave this window open - progress prints below.
echo  You can keep using your computer meanwhile.
echo ============================================================
echo.
"%~dp0venv\Scripts\python.exe" -u "%~dp0pdf_to_md.py" "%~dp0..\PDF Inbox"
if errorlevel 1 goto :err
echo.
echo ------------- updating search index -------------
"%~dp0venv\Scripts\python.exe" -u "%~dp0build_index.py"
if errorlevel 1 goto :err
echo.
echo ============================================================
echo  ALL DONE. Converted notes are in:
echo  _pdf_imports (in your vault)
echo  You can now move the PDFs out of PDF Inbox (they were
echo  not changed). Press any key to close.
echo ============================================================
pause >nul
exit /b

:err
echo.
echo  Something went wrong - read the message above this line.
echo  Nothing in your vault was harmed. Press any key to close.
pause >nul
