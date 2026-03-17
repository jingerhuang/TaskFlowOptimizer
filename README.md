# 🚀 程序任务流编排与关键路径分析工具

基于**关键路径法 (CPM)**的任务流分析与优化工具，帮助您识别瓶颈任务、优化任务编排，从而缩短项目总工期。

## 📋 目录

- [功能特性](#-功能特性)
- [运行效果](#-运行效果)
- [安装与运行](#-安装与运行)
- [使用方法](#-使用方法)
- [CSV 文件格式](#csv-文件格式)
- [技术栈](#-技术栈)
- [注意事项](#-注意事项)

## ✨ 功能特性

- **🎯 关键路径识别**：自动识别决定项目最短工期的关键任务链（红色标识）
- **📊 甘特图可视化**：直观展示任务时间安排与并行关系
- **🕸️ 拓扑图分析**：清晰呈现任务依赖关系
- **⚡ 浮动时间计算**：识别非关键路径任务的灵活调度空间
- **📁 CSV 导入**：支持批量任务数据导入
- **🔍 循环依赖检测**：自动检测并提示逻辑错误

## 🎨 运行效果

### 核心概念
- **关键路径（红色）**：决定项目最短总耗时的任务链，只有缩短这些任务才能减少总时间
- **非关键路径（蓝色）**：拥有"浮动时间"，适当延迟不会影响总工期

### 界面展示
- **任务编辑区**：可动态添加/编辑任务的交互式表格
- **数据分析**：一键计算关键路径与最优工期
- **可视化图表**：Plotly 甘特图 + NetworkX 拓扑图双重视角

## 🛠️ 安装与运行

### 前置要求

- **Python**: 3.12 或更高版本
- **Graphviz**: 用于拓扑图布局（必需）

### 安装步骤

#### 1. 安装 Graphviz

**Windows 系统：**
```powershell
# 使用 Chocolatey 包管理器
choco install graphviz

# 或手动安装：
# 1. 访问 https://graphviz.org/download/#windows
# 2. 下载并安装 Windows 版本
# 3. 将 Graphviz 添加到系统 PATH 环境变量
```

**Linux 系统：**
```bash
# Ubuntu/Debian
sudo apt-get install graphviz

# CentOS/RHEL
sudo yum install graphviz
```

**macOS 系统：**
```bash
brew install graphviz
```

#### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

或者手动安装：
```bash
pip install streamlit networkx pandas plotly matplotlib
```

#### 3. 运行应用

```bash
streamlit run app.py
```

应用将在浏览器中自动打开，默认地址为 `http://localhost:8501`

## 📖 使用方法

### 方法一：手动输入任务

1. 在侧边栏的表格中输入任务信息
2. 每行包含三个字段：
   - **任务 ID**：唯一标识符（如 A, B, C）
   - **耗时**：任务执行时间（秒）
   - **前置依赖**：前置任务 ID，多个用逗号分隔
3. 点击"🔍 开始分析与优化"按钮

### 方法二：导入 CSV 文件

1. 准备符合格式的 CSV 文件（见下文）
2. 在侧边栏点击"上传 CSV 文件"
3. 选择文件后自动解析并显示

### 示例任务

| id | duration | deps |
|----|----------|------|
| A | 5 | |
| B | 3 | A |
| C | 4 | A |
| D | 2 | B, C |

这个例子中：
- 任务 A 无依赖，首先执行
- 任务 B 和 C 都依赖 A，可以并行执行
- 任务 D 依赖 B 和 C，需等两者都完成后才能开始

**关键路径**：A → C → D（总耗时 11 秒）

## 📄 CSV 文件格式

CSV 文件应包含以下三列：

```csv
id,duration,deps
A,5,
B,3,A
C,4,A
D,2,"B, C"
```

### 格式说明

- **id**：任务唯一标识（字符串）
- **duration**：任务耗时（数字，单位：秒）
- **deps**：前置依赖 ID，多个依赖用逗号分隔（字符串）
- 空行和空值会被自动忽略
- 支持 UTF-8 编码

## 💻 技术栈

### 核心框架
- **[Streamlit](https://streamlit.io/)**：Web 应用框架
- **[Pandas](https://pandas.pydata.org/)**：数据处理与分析
- **[NetworkX](https://networkx.org/)**：图论算法与依赖建模
- **[Plotly](https://plotly.com/python/)**：交互式甘特图
- **[Matplotlib](https://matplotlib.org/)**：静态拓扑图渲染

### 系统依赖
- **Graphviz**：图形可视化布局引擎

### Python 版本
- Python 3.12+

## ⚠️ 注意事项

### 常见错误与解决方案

#### 1. Graphviz 未安装
```
ExecutableNotFound: failed to execute ['dot', '-Kdot', ...]
```
**解决方案**：安装 Graphviz 并确保添加到系统 PATH

#### 2. 循环依赖检测
```
错误：检测到循环依赖！请检查任务逻辑。
```
**解决方案**：检查任务依赖关系，确保不存在环形依赖（如 A→B→C→A）

#### 3. 无效任务 ID
```
💡 请检查任务 ID 是否唯一，以及依赖的 ID 是否存在于列表中。
```
**解决方案**：
- 确保所有任务 ID 唯一
- 确保依赖的 ID 在任务列表中存在
- 避免使用空 ID 或 'nan'

### 中文字体支持

应用已配置中文字体支持（SimHei/Microsoft YaHei），如遇字体问题：

**Windows**：无需额外配置  
**Linux**：安装中文字体
```bash
sudo apt-get install fonts-wqy-zenhei
```

**macOS**：通常无需配置

## 🎯 优化建议

1. **聚焦关键路径**：优先优化红色标识的关键任务
2. **任务拆分**：将长耗时关键任务拆分为可并行的子任务
3. **资源倾斜**：将更多资源投入到关键路径任务
4. **依赖优化**：重新设计依赖关系，增加并行度

## 📝 更新日志

### v1.0.0
- ✨ 初始版本发布
- 🎯 关键路径计算与可视化
- 📊 甘特图与拓扑图展示
- 📁 CSV 导入功能
- 🔍 循环依赖检测

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个工具！

## 📄 许可证

本项目采用 MIT 许可证

---

**开发者提示**：如有问题或建议，欢迎反馈！
