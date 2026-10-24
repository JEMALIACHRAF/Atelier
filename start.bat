@echo off
title Atelier - launcher
setlocal EnableDelayedExpansion

echo.
echo ========================================
echo   ATELIER - demarrage
echo ========================================
echo.

cd /d "%~dp0"

echo [1/4] Verification Python...
python --version 2>nul
if errorlevel 1 goto no_python
echo       OK

echo.
echo [2/4] Verification Node.js...
node --version 2>nul
if errorlevel 1 goto no_node
echo       OK

echo.
if exist ".env" goto skip_env_copy
echo [SETUP] Creation .env depuis .env.example...
copy /y .env.example .env >nul
:skip_env_copy

echo.
echo [3/4] Verification Claude Code CLI...
where claude >nul 2>&1
if errorlevel 1 goto install_claude
echo       OK, deja installe
goto install_python_deps

:install_claude
echo       Pas installe. Installation en cours, patientez 1 a 2 minutes...
call npm install -g @anthropic-ai/claude-code
if errorlevel 1 goto npm_fail
echo.
echo ============================================================
echo  Claude Code vient d'etre installe.
echo  AVANT de continuer, ouvrez un AUTRE terminal cmd et tapez:
echo.
echo       claude login
echo.
echo  Connectez-vous avec votre compte Claude Pro, puis relancez
echo  ce start.bat.
echo ============================================================
goto end

:install_python_deps
echo.
echo [4/4] Installation dependances Python...
python -m pip install --quiet --upgrade pip 2>nul
python -m pip install --quiet -r requirements.txt
if errorlevel 1 goto pip_fail
echo       OK

echo.
echo ========================================
echo   Lancement du backend
echo ========================================
echo.
echo Ouverture du navigateur sur http://localhost:7777 ...
start "" http://localhost:7777

echo.
echo Backend demarre. Fermez cette fenetre pour tout arreter.
echo.
python -m uvicorn backend.main:app --host 127.0.0.1 --port 7777

echo.
echo [INFO] Le backend s'est arrete.
goto end

:no_python
echo.
echo [ERREUR] Python non trouve dans votre PATH.
echo.
echo Installez Python 3.11+ depuis:
echo       https://www.python.org/downloads/
echo.
echo IMPORTANT: cochez "Add Python to PATH" pendant l'installation.
goto end

:no_node
echo.
echo [ERREUR] Node.js non trouve dans votre PATH.
echo.
echo Installez Node 20+ LTS depuis:
echo       https://nodejs.org/
goto end

:npm_fail
echo.
echo [ERREUR] Installation de Claude Code via npm a echoue.
echo.
echo Essayez manuellement dans un terminal:
echo       npm install -g @anthropic-ai/claude-code
goto end

:pip_fail
echo.
echo [ERREUR] Installation des dependances Python a echoue.
echo.
echo Essayez manuellement:
echo       python -m pip install -r requirements.txt
goto end

:end
echo.
echo ========================================
echo  Appuyez sur une touche pour fermer...
echo ========================================
pause >nul
endlocal
