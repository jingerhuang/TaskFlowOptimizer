# 🐳 Docker 部署指南

## 📋 目录

- [快速开始](#快速开始)
- [构建镜像](#构建镜像)
- [运行容器](#运行容器)
- [使用 Docker Compose](#使用-docker-compose)
- [生产环境部署](#生产环境部署)
- [常见问题](#常见问题)

## 🚀 快速开始

### 前置要求

- Docker 20.10+ 
- Docker Compose v2.0+ (可选，但推荐)

### 一键启动（推荐）

使用 Docker Compose 最简单：

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

访问地址：http://localhost:8501

## 🔨 构建镜像

### 方式一：直接构建

```bash
# 构建镜像
docker build -t taskflow-optimizer:latest .

# 查看镜像
docker images | grep taskflow
```

### 方式二：使用 Docker Compose 构建

```bash
# 仅构建不启动
docker-compose build

# 强制重新构建（不使用缓存）
docker-compose build --no-cache
```

## 🏃 运行容器

### 基础运行

```bash
# 运行容器
docker run -d \
  --name taskflow-optimizer \
  -p 8501:8501 \
  taskflow-optimizer:latest
```

### 挂载数据卷（推荐）

```bash
# 挂载本地数据目录
docker run -d \
  --name taskflow-optimizer \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  taskflow-optimizer:latest
```

**Windows PowerShell:**
```powershell
docker run -d `
  --name taskflow-optimizer `
  -p 8501:8501 `
  -v ${PWD}/data:/app/data `
  taskflow-optimizer:latest
```

### 自定义端口

```bash
# 使用 8080 端口
docker run -d \
  --name taskflow-optimizer \
  -p 8080:8501 \
  taskflow-optimizer:latest
```

访问：http://localhost:8080

## 🐋 Docker Compose 详解

### 配置文件说明

`docker-compose.yml` 已包含以下配置：

- **服务名称**: `taskflow-optimizer`
- **端口映射**: 8501:8501
- **数据卷**: ./data:/app/data
- **健康检查**: 30 秒间隔检测
- **自动重启**: unless-stopped

### 常用命令

```bash
# 启动服务
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f taskflow-optimizer

# 重启服务
docker-compose restart

# 停止服务
docker-compose stop

# 停止并删除容器（保留数据卷）
docker-compose down

# 停止并删除容器和数据卷
docker-compose down -v

# 重新构建并启动
docker-compose up -d --build
```

## 🏭 生产环境部署

### 使用 Nginx 反向代理

1. **启用 Nginx 服务**

   取消 `docker-compose.yml` 中 Nginx 部分的注释：

   ```yaml
   services:
     taskflow-optimizer:
       # ... 原有配置
     
     nginx:
       image: nginx:alpine
       container_name: taskflow-nginx
       ports:
         - "80:80"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf:ro
       depends_on:
         - taskflow-optimizer
       restart: unless-stopped
   ```

2. **启动服务**

   ```bash
   docker-compose up -d
   ```

3. **访问**: http://localhost

### 配置 HTTPS（可选）

使用 Let's Encrypt 免费证书：

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  taskflow-optimizer:
    build: .
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: taskflow-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - certbot-data:/var/www/certbot
    depends_on:
      - taskflow-optimizer
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - certbot-data:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"

volumes:
  certbot-data:
```

### 环境变量配置

创建 `.env` 文件：

```bash
# 应用配置
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Nginx 配置
NGINX_HOST=localhost
NGINX_PORT=80

# 时区配置
TZ=Asia/Shanghai
```

在 `docker-compose.yml` 中使用：

```yaml
services:
  taskflow-optimizer:
    env_file:
      - .env
```

## 📊 监控与运维

### 查看资源使用

```bash
# 查看 CPU 和内存使用
docker stats taskflow-optimizer

# 查看容器详情
docker inspect taskflow-optimizer
```

### 进入容器调试

```bash
# 进入容器 shell
docker exec -it taskflow-optimizer bash

# 查看应用进程
docker exec -it taskflow-optimizer ps aux

# 查看日志
docker exec -it taskflow-optimizer tail -f /dev/stdout
```

### 备份数据

```bash
# 备份数据卷
docker run --rm \
  -v taskflow-optimizer_data:/data:ro \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/taskflow-data.tar.gz -C /data .

# 恢复数据卷
docker run --rm \
  -v taskflow-optimizer_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/taskflow-data.tar.gz -C /data
```

## ⚠️ 常见问题

### Q1: Graphviz 无法显示中文

**解决方案**: Dockerfile 已安装文泉驿字体，如仍有问题，在 `.streamlit/config.toml` 中配置：

```toml
[font]
sansSerif = "WenQuanYi Zen Hei"
```

### Q2: 容器启动失败

**排查步骤**:

```bash
# 查看日志
docker-compose logs taskflow-optimizer

# 检查端口占用
netstat -tuln | grep 8501

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

### Q3: 访问速度慢

**优化方案**:

1. 增加容器资源限制
2. 使用本地存储卷
3. 配置 Nginx 缓存

```yaml
# docker-compose.override.yml
version: '3.8'

services:
  taskflow-optimizer:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Q4: 如何更新代码

**方法一**: 重新构建镜像

```bash
docker-compose build --no-cache
docker-compose up -d
```

**方法二**: 挂载代码目录（开发环境）

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  taskflow-optimizer:
    volumes:
      - ./app.py:/app/app.py
      - ./scheduler.py:/app/scheduler.py
```

### Q5: 多用户并发访问

Streamlit 默认支持多用户会话，每个用户有独立的 session_state。

如需更高性能，可考虑：

1. 使用多个容器 + 负载均衡
2. 增加容器资源配额
3. 使用 Redis 共享 session

## 🔒 安全建议

### 1. 启用身份验证

创建 `credentials.toml`:

```toml
[users]
admin = "password_hash"
user1 = "password_hash"
```

在 `.streamlit/config.toml` 中引用：

```toml
[server]
enableStaticServing = false

[auth]
credentialsFile = "/app/credentials.toml"
```

### 2. 配置防火墙

```bash
# 仅允许特定 IP 访问
iptables -A INPUT -p tcp --dport 8501 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 8501 -j DROP
```

### 3. 使用 HTTPS

参考上方的 HTTPS 配置章节。

## 📝 最佳实践

### 1. 镜像优化

- 使用多阶段构建减小镜像体积
- 合并 RUN 指令减少层数
- 使用 .dockerignore 排除不必要文件

### 2. 数据持久化

- 使用命名卷 (named volumes) 而非绑定挂载
- 定期备份重要数据
- 配置自动快照

### 3. 日志管理

```yaml
# docker-compose.yml
services:
  taskflow-optimizer:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. 健康检查

已配置健康检查，可配合 Kubernetes 或 Swarm 使用。

## 🎯 下一步

- [ ] 配置 CI/CD 自动化部署
- [ ] 集成监控系统（Prometheus + Grafana）
- [ ] 实现水平自动扩缩容
- [ ] 添加分布式追踪（Jaeger）

---

**Made with ❤️ using Docker**

*最后更新：2026-03-18*
