# 任务排序工具 - Docker 快速启动脚本 (Windows PowerShell)
# 适用于 Windows PowerShell

Write-Host "🚀 任务排序工具 - Docker 启动中..." -ForegroundColor Green

# 检查 Docker 是否安装
try {
    $dockerVersion = docker --version 2>&1
} catch {
    Write-Host "❌ Docker 未安装，请先安装 Docker Desktop" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Docker 是否运行
try {
    docker info | Out-Null
} catch {
    Write-Host "❌ Docker 未运行，请启动 Docker Desktop" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查 Docker Compose
$composeCmd = ""
try {
    docker-compose --version | Out-Null
    $composeCmd = "docker-compose"
} catch {
    try {
        docker compose version | Out-Null
        $composeCmd = "docker compose"
    } catch {
        Write-Host "❌ Docker Compose 未安装" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}

# 创建数据目录
if (!(Test-Path "data")) {
    New-Item -ItemType Directory -Path "data" | Out-Null
}

# 停止旧容器
Write-Host "📦 停止旧的容器（如有）..." -ForegroundColor Yellow
& $composeCmd down 2>$null

# 构建并启动
Write-Host "🔨 构建 Docker 镜像..." -ForegroundColor Yellow
& $composeCmd build

Write-Host "🏃 启动服务..." -ForegroundColor Green
& $composeCmd up -d

# 等待服务启动
Write-Host "⏳ 等待服务启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 检查服务状态
$services = & $composeCmd ps
if ($services -match "Up") {
    Write-Host "`n✅ 服务启动成功！`n" -ForegroundColor Green
    Write-Host "🌐 访问地址：http://localhost:8501`n" -ForegroundColor Cyan
    Write-Host "📝 常用命令:" -ForegroundColor Yellow
    Write-Host "   查看日志：$composeCmd logs -f"
    Write-Host "   停止服务：$composeCmd down"
    Write-Host "   重启服务：$composeCmd restart"
    Write-Host ""
} else {
    Write-Host "`n❌ 服务启动失败，请查看日志：" -ForegroundColor Red
    & $composeCmd logs
    Read-Host "按回车键退出"
    exit 1
}
