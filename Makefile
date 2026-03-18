# TaskFlowOptimizer - Makefile
# 用于快速构建和管理 Docker 容器

.PHONY: help build up down restart logs clean shell health

# 默认目标
help:
	@echo "TaskFlowOptimizer - Docker 管理命令"
	@echo ""
	@echo "可用命令:"
	@echo "  make build      - 构建 Docker 镜像"
	@echo "  make up         - 启动服务（后台运行）"
	@echo "  make down       - 停止并删除容器"
	@echo "  make restart    - 重启服务"
	@echo "  make logs       - 查看日志（实时）"
	@echo "  make clean      - 清理所有容器和镜像"
	@echo "  make shell      - 进入容器 Shell"
	@echo "  make ps         - 查看容器状态"
	@echo "  make health     - 检查服务健康状态"
	@echo "  make rebuild    - 重新构建并启动"
	@echo ""

# 构建镜像
build:
	docker-compose build

# 启动服务
up:
	docker-compose up -d
	@echo "服务已启动，访问：http://localhost:8501"

# 停止服务
down:
	docker-compose down

# 重启服务
restart:
	docker-compose restart

# 查看日志
logs:
	docker-compose logs -f taskflow-optimizer

# 清理所有
clean:
	docker-compose down -v
	docker rmi taskflow-optimizer:latest 2>/dev/null || true
	@echo "清理完成"

# 进入容器 Shell
shell:
	docker-compose exec taskflow-optimizer bash

# 查看容器状态
ps:
	docker-compose ps

# 健康检查
health:
	@echo "检查服务健康状态..."
	@docker-compose ps | grep -q "Up" && echo "✅ 服务运行正常" || echo "❌ 服务未运行"

# 重新构建并启动
rebuild:
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "服务已重启，访问：http://localhost:8501"

# 开发模式（挂载代码）
dev:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "开发模式已启动，代码变更将自动重载"
