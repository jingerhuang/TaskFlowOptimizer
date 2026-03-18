#!/bin/bash

# 任务排序工具 - Docker 快速启动脚本
# 适用于 Linux/macOS

set -e

echo "🚀 任务排序工具 - Docker 启动中..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker 是否运行
if ! docker info &> /dev/null; then
    echo "❌ Docker 未运行，请启动 Docker 服务"
    exit 1
fi

# 检查 Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    echo "❌ Docker Compose 未安装"
    exit 1
fi

# 创建数据目录
mkdir -p data

# 停止旧容器
echo "📦 停止旧的容器（如有）..."
$COMPOSE_CMD down 2>/dev/null || true

# 构建并启动
echo "🔨 构建 Docker 镜像..."
$COMPOSE_CMD build

echo "🏃 启动服务..."
$COMPOSE_CMD up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
if $COMPOSE_CMD ps | grep -q "Up"; then
    echo ""
    echo "✅ 服务启动成功！"
    echo ""
    echo "🌐 访问地址：http://localhost:8501"
    echo ""
    echo "📝 常用命令:"
    echo "   查看日志：$COMPOSE_CMD logs -f"
    echo "   停止服务：$COMPOSE_CMD down"
    echo "   重启服务：$COMPOSE_CMD restart"
    echo ""
else
    echo "❌ 服务启动失败，请查看日志："
    $COMPOSE_CMD logs
    exit 1
fi
