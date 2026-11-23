@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python
py -3 configurar_numero.py
goto fin
:python
where python >nul 2>nul
if errorlevel 1 goto falta
python configurar_numero.py
goto fin
:falta
echo Instala Python 3.10 o superior desde python.org y vuelve a abrir este archivo.
:fin
pause
