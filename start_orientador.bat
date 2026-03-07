@echo off
chcp 65001 >nul
echo =======================================================
echo          Orientador.IA MVP - Sequência de Arranque
echo (Se estiver no PowerShell, use .\start_orientador.bat)
echo =======================================================
echo.

echo Verificando se o Docker está a correr...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERRO] O Docker nao parece estar a correr. 
    echo Por favor, inicie o Docker Desktop no Windows e tente novamente.
    pause
    exit /b 1
)

echo [1/5] A iniciar todos os servicos (PostgreSQL, Qdrant, Redis, Ollama, Backend, Frontend)...
docker compose up -d
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao iniciar contentores.
    pause
    exit /b 1
)

echo.
echo A aguardar 15 segundos para os servicos inicializarem...
timeout /t 15 /nobreak >nul

echo.
echo [2/5] A verificar/transferir modelos do Ollama...
echo Transferindo qwen3.5:4b (pode demorar)...
docker compose exec ollama ollama pull qwen3.5:4b
echo Transferindo qwen3.5:0.8b...
docker compose exec ollama ollama pull qwen3.5:0.8b
echo Transferindo nomic-embed-text...
docker compose exec ollama ollama pull nomic-embed-text

echo.
echo [3/5] A executar migrações da base de dados (Alembic)...
docker compose exec backend uv run alembic upgrade head
if %errorlevel% neq 0 (
    echo [ERRO] Falha nas migrações da base de dados.
    pause
    exit /b 1
)

echo.
echo [4/5] A fazer o seed das Almas (PostgreSQL + Qdrant)...
docker compose exec backend uv run scripts/seed_almas.py
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao fazer o seed das Almas.
    pause
    exit /b 1
)

echo.
echo [5/5] A executar validacao de sistema E2E...
pushd backend
set PYTHONPATH=.
uv run full_validation_e2e.py
if %errorlevel% neq 0 (
    echo [AVISO] Falha na Validacao E2E do sistema. Reveja as alterações.
    popd
    pause
    exit /b 1
)
popd
if %errorlevel% neq 0 (
    echo [AVISO] Falha nos testes do Backend. Reveja as alterações.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo ✅ Orientador.IA iniciado com sucesso!
echo.
echo Frontend: http://localhost:3000
echo Backend API Docs: http://localhost:8000/docs
echo =======================================================
pause
