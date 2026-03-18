@echo off
REM 任务排序工具 - Docker 快速启动脚本 (Windows PowerShell/CMD)
REM 适用于 Windows 系统

echo 🚀 任务排序工具 - Docker 启动中...

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未安装，请先安装 Docker Desktop
    pause
    exit /b 1
)

REM 检查 Docker 是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker 未运行，请启动 Docker Desktop
    pause
    exit /b 1
)

REM 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    docker compose version >nul 2>&1
    if errorlevel 1 (
        echo ❌ Docker Compose 未安装
        pause
        exit /b 1
    )
    set COMPOSE_CMD=docker compose
) else (
    set COMPOSE_CMD=docker-compose
)

REM 创建数据目录
if not exist data mkdir data

REM 停止旧容器
echo 📦 停止旧的容器（如有）...
%COMPOSE_CMD% down >nul 2>&1

REM 构建并启动
echo 🔨 构建 Docker 镜像...
%COMPOSE_CMD% build

echo 🏃 启动服务...
%COMPOSE_CMD% up -d

REM 等待服务启动
echo ⏳ 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
%COMPOSE_CMD% ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo ❌ 服务启动失败，请查看日志：
    %COMPOSE_CMD% logs
    pause
    exit /b 1
)

echo.
echo ✅ 服务启动成功！
echo.
echo 🌐 访问地址：http://localhost:8501
echo.
echo 📝 常用命令:
echo    查看日志：%COMPOSE_CMD% logs -f
echo    停止服务：%COMPOSE_CMD% down
echo    重启服务：%COMPOSE_CMD% restart
echo.
pause
