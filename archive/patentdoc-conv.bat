@echo off
setlocal
REM 使い方:
REM   引数なし                     ... GUI アプリを起動
REM   patentdoc-conv.bat C:\path   ... CLI 実行（path 直下に TXT と IMG）

if "%~1"=="" (
  patentdoc-conv --gui
  exit /b %ERRORLEVEL%
)

patentdoc-conv run --dir "%~1"
