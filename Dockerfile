# 基础 Python 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（包括 Graphviz）
# 使用多个镜像源提高可靠性
RUN set -eux; \
    # 更新软件源列表
    apt-get update; \
    # 安装必要的依赖包
    apt-get install -y --no-install-recommends \
        graphviz=2.42.2-6 \
        libgraphviz-dev=2.42.2-6 \
        fonts-wqy-zenhei=0.9.45-8 \
    ; \
    # 清理缓存，减小镜像体积
    rm -rf /var/lib/apt/lists/*; \
    # 验证安装成功
    dot -V

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .
COPY scheduler.py .

# 复制示例文件（如果存在）
# COPY example_tasks.csv .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# 暴露端口
EXPOSE 8501

# 启动命令
CMD ["streamlit", "run", "app.py"]
