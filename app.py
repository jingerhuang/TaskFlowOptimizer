import streamlit as st
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import logging
from datetime import datetime, timedelta

# 导入自定义的调度模块
from scheduler import (
    schedule_tasks_limited_threads,
    generate_gantt_data,
    calculate_thread_utilization,
    optimize_thread_count
)

# --- 配置日志记录 ---
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- 配置 Matplotlib 中文字体支持 ---
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# --- 页面配置 ---
st.set_page_config(page_title="程序任务流优化器", layout="wide")
st.title("🚀 程序任务流编排与关键路径分析")
st.markdown("""
此工具基于 **关键路径法 (CPM)**。
- **关键路径** (红色)：决定项目最短总耗时的任务链。只有缩短这些任务，总时间才会减少。
- **非关键路径** (蓝色)：拥有“浮动时间”，适当延迟不会影响总工期。
""")

# --- 侧边栏：数据输入 ---
st.sidebar.header("TaskFlowOptimizer")

# 空数据框模板（无默认数据）
empty_df = pd.DataFrame(columns=["id", "duration", "unit", "deps"])

# 时间单位选项列表
TIME_UNIT_OPTIONS = ['ms', 's', 'min', 'h', 'd', 'week', 'month', 'year']

# 使用 Session State 保持数据状态
if 'df' not in st.session_state:
    # 初始化为一个空行，方便用户输入
    st.session_state.df = pd.DataFrame({'id': [''], 'duration': [0], 'unit': ['s'], 'deps': ['']})

# 用于重置文件上传器的计数器
if 'uploader_key' not in st.session_state:
    st.session_state.uploader_key = 0

# 时间单位映射（转换为秒）
TIME_UNIT_TO_SECONDS = {
    'ms': 0.001,      # 毫秒
    's': 1,           # 秒
    'min': 60,        # 分钟
    'h': 3600,        # 小时
    'd': 86400,       # 天
    'week': 604800,   # 周
    'month': 2592000, # 月 (按 30 天计算)
    'year': 31536000  # 年 (按 365 天计算)
}

TIME_UNIT_LABELS = {
    'ms': '毫秒 (ms)',
    's': '秒 (s)',
    'min': '分钟 (min)',
    'h': '小时 (h)',
    'd': '天 (d)',
    'week': '周 (week)',
    'month': '月 (month)',
    'year': '年 (year)'
}

def update_df():
    # 这里简单处理，实际生产中可以用 st.data_editor 直接编辑
    pass

# --- 侧边栏：甘特图设置 ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ 甘特图设置")

# 开始日期选择
use_start_date = st.sidebar.checkbox("📅 使用开始日期", value=False, help="勾选后可选择甘特图的开始时间")
start_date = None
if use_start_date:
    start_date = st.sidebar.date_input(
        "开始日期",
        value=None,
        help="甘特图将从此日期开始绘制"
    )

# --- 有限线程调度设置 ---
st.sidebar.markdown("---")
st.sidebar.subheader("🧵 有限线程调度")

use_limited_threads = st.sidebar.checkbox(
    "启用有限线程模式", 
    value=False, 
    help="启用后可以指定线程数量进行任务最优排列"
)

num_threads = 2
auto_optimize = False

if use_limited_threads:
    thread_mode = st.sidebar.radio(
        "线程模式",
        ["手动指定", "自动优化"],
        index=0,
        help="手动指定：固定线程数；自动优化：分析最佳线程数"
    )
    
    if thread_mode == "手动指定":
        num_threads = st.sidebar.number_input(
            "线程数量",
            min_value=1,
            max_value=20,
            value=2,
            step=1,
            help="同时执行的任务线程数"
        )
    else:
        auto_optimize = True
        max_threads = st.sidebar.number_input(
            "最大线程数（搜索范围）",
            min_value=2,
            max_value=50,
            value=10,
            step=1,
            help="算法将在此范围内寻找最优线程数"
        )

# --- CSV 文件上传功能 ---
st.sidebar.markdown("---")
st.sidebar.subheader("📁 导入 CSV 文件")
uploaded_file = st.sidebar.file_uploader(
    "上传 CSV 文件",
    type=["csv"],
    help="CSV 格式：id, duration, deps",
    key=f"uploader_{st.session_state.uploader_key}"
)

if uploaded_file is not None:
    try:
        # 读取 CSV 文件
        csv_df = pd.read_csv(uploaded_file, encoding='utf-8')
        
        # 验证必要的列
        required_columns = ['id', 'duration', 'deps']
        missing_cols = [col for col in required_columns if col not in csv_df.columns]
        
        if not missing_cols:
            # 填充空值并转换类型
            csv_df = csv_df.fillna({'id': '', 'duration': 0, 'deps': '', 'unit': 's'})
            csv_df['duration'] = pd.to_numeric(csv_df['duration'], errors='coerce').fillna(0).astype(float)
            csv_df['id'] = csv_df['id'].astype(str).str.strip()
            csv_df['deps'] = csv_df['deps'].astype(str).str.strip()
            # 如果 CSV 没有 unit 列，添加默认值
            if 'unit' not in csv_df.columns:
                csv_df['unit'] = 's'
            else:
                # 清理和验证单位值
                csv_df['unit'] = csv_df['unit'].astype(str).str.strip().fillna('s')
                # 将无效的单位替换为's'
                csv_df.loc[~csv_df['unit'].isin(TIME_UNIT_OPTIONS), 'unit'] = 's'
            
            # 重新排列列顺序为：id, duration, unit, deps
            csv_df = csv_df[['id', 'duration', 'unit', 'deps']]
            
            # 更新 session state
            st.session_state.df = csv_df
            st.sidebar.success(f"✅ 成功导入 {len(csv_df)} 个任务")
        else:
            st.sidebar.error(f"❌ CSV 文件缺少必要的列：{', '.join(missing_cols)}")
            logger.warning(f"CSV 文件缺少列：{missing_cols}")
    except UnicodeDecodeError:
        st.sidebar.error("❌ 文件编码错误，请使用 UTF-8 编码保存 CSV 文件")
        logger.error("CSV 文件编码错误")
    except Exception as e:
        st.sidebar.error(f"❌ 读取 CSV 文件失败：{str(e)}")
        logger.error(f"读取 CSV 失败：{e}")

# 添加重置按钮和示例数据按钮（根据当前是否有数据来决定是否显示）
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ 数据管理")

# 检查当前是否有有效数据
has_valid_data = False
if 'df' in st.session_state:
    current_df = st.session_state.df
    if not current_df.empty:
        # 检查是否有非空的任务 ID
        valid_ids = current_df['id'].dropna().astype(str).str.strip()
        has_valid_data = len(valid_ids[(valid_ids != '') & (valid_ids != 'nan')]) > 0

# 清空所有任务按钮 (始终显示)
if st.sidebar.button("🔄 清空所有任务", use_container_width=True, help="删除所有任务数据，重置为空白状态"):
    st.session_state.df = pd.DataFrame({'id': [''], 'duration': [0], 'unit': ['s'], 'deps': ['']})
    # 重置文件上传器
    st.session_state.uploader_key += 1
    st.rerun()

# 加载示例数据按钮（仅在没有数据时显示）
if not has_valid_data:
    if st.sidebar.button("📝 加载示例数据", use_container_width=True, help="加载预设的示例任务数据"):
        example_data = {
            'id': ['A', 'B', 'C', 'D', 'E', 'F', 'G'],
            'duration': [2, 30, 1, 500, 1.5, 45, 0.5],
            'unit': ['h', 'min', 'd', 'ms', 'h', 'min', 'd'],
            'deps': ['', 'A', 'A', 'B, C', 'D', 'C', 'E, F']
        }
        st.session_state.df = pd.DataFrame(example_data)
        st.rerun()

# 使用可编辑的 DataFrame
try:
    # 确保 session state 中有数据
    if 'df' not in st.session_state or st.session_state.df.empty:
        st.session_state.df = pd.DataFrame({'id': [''], 'duration': [0], 'unit': ['s'], 'deps': ['']})
    
    # 显示提示信息
    st.info("💡 **提示**：依赖关系填写任务 ID (如：A, B)，多个依赖用逗号分隔。")
    
    edited_df = st.data_editor(
        st.session_state.df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn("任务 ID (唯一)", required=True),
            "duration": st.column_config.NumberColumn("耗时", min_value=0, step=1, required=True),
            "unit": st.column_config.SelectboxColumn(
                "单位",
                options=TIME_UNIT_OPTIONS,
                default='s',
                required=True,
                help="选择时间单位：毫秒、秒、分钟、小时、天、周、月、年"
            ),
            "deps": st.column_config.TextColumn("前置依赖 ID (逗号分隔)"),
        },
        key="editor",
        hide_index=True
    )
    # 将编辑后的数据保存回 session state
    st.session_state.df = edited_df
except Exception as e:
    logger.error(f"表格加载失败：{e}")
    st.session_state.df = pd.DataFrame({'id': [''], 'duration': [0], 'unit': ['s'], 'deps': ['']})
    edited_df = st.data_editor(
        st.session_state.df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn("任务 ID (唯一)", required=True),
            "duration": st.column_config.NumberColumn("耗时", min_value=0, step=1, required=True),
            "unit": st.column_config.SelectboxColumn(
                "单位",
                options=TIME_UNIT_OPTIONS,
                default='s',
                required=True,
                help="选择时间单位：毫秒、秒、分钟、小时、天、周、月、年"
            ),
            "deps": st.column_config.TextColumn("前置依赖 ID (逗号分隔)"),
        },
        key="editor",
        hide_index=True
    )

def has_valid_tasks(df):
    """检查 DataFrame 中是否有有效的任务数据"""
    try:
        if df is None or df.empty:
            return False
        if 'id' not in df.columns:
            return False
        valid_ids = df['id'].dropna().astype(str).str.strip()
        mask = (valid_ids != '') & (valid_ids != 'nan')
        return len(valid_ids[mask]) > 0
    except Exception as e:
        logger.warning(f"检查任务数据时出错：{e}")
        return False

def convert_duration_to_seconds(duration, unit):
    """将耗时转换为秒，确保单位转换正确"""
    try:
        # 验证单位是否有效
        if unit not in TIME_UNIT_TO_SECONDS:
            logger.warning(f"无效的时间单位：{unit}，使用默认单位 's'")
            unit = 's'
        
        multiplier = TIME_UNIT_TO_SECONDS[unit]
        duration_float = float(duration)
        
        # 确保耗时为正值
        if duration_float < 0:
            logger.warning(f"负数的耗时：{duration_float}，转换为 0")
            duration_float = 0.0
        
        seconds = duration_float * multiplier
        return seconds
    except (ValueError, TypeError) as e:
        logger.warning(f"转换耗时出错：{duration}, {unit}, 错误：{e}")
        return 0.0

# --- 核心逻辑：关键路径计算 ---
def calculate_critical_path(df):
    G = nx.DiGraph()
    
    # 1. 构建图
    for _, row in df.iterrows():
        # 处理任务 ID，确保是有效的字符串
        id_val = row['id']
        if pd.isna(id_val):
            continue  # 跳过空行
        task_id = str(id_val).strip()
        if not task_id or task_id.lower() == 'nan':
            continue
        
        # 处理耗时，转换为秒
        duration_val = row['duration']
        if pd.isna(duration_val):
            duration = 0.0
        else:
            # 获取时间单位并转换为秒
            unit = row.get('unit', 's')
            if pd.isna(unit) or str(unit).strip() == '':
                unit = 's'
            else:
                unit = str(unit).strip()
            duration = convert_duration_to_seconds(float(duration_val), unit)
        
        # 处理依赖关系，确保是字符串
        deps_val = row['deps']
        if pd.isna(deps_val) or deps_val is None:
            deps_str = ""
        else:
            deps_str = str(deps_val).strip()
        
        G.add_node(task_id, weight=duration, original_duration=duration_val, unit=unit)
        
        if deps_str and deps_str.strip():
            dep_list = [d.strip() for d in deps_str.split(',') if d.strip()]
            for dep in dep_list:
                if dep and dep.lower() != 'nan': # 确保依赖项有效
                    G.add_edge(dep, task_id)
    
    # 检查是否有环
    if not nx.is_directed_acyclic_graph(G):
        logger.error("检测到循环依赖")
        return None, None, "错误：检测到循环依赖！请检查任务逻辑。"
    
    # 检查是否为空图
    if len(G.nodes()) == 0:
        logger.warning("没有有效的任务")
        return None, None, "错误：没有有效的任务！请至少添加一个任务。"

    # 2. 计算最早开始/结束时间 (Forward Pass)
    topo_order = list(nx.topological_sort(G))
    earliest_start = {}
    earliest_finish = {}
    
    for node in topo_order:
        duration = G.nodes[node]['weight']
        predecessors = list(G.predecessors(node))
        
        if not predecessors:
            es = 0
        else:
            es = max(earliest_finish[p] for p in predecessors)
        
        earliest_start[node] = es
        earliest_finish[node] = es + duration

    total_duration = max(earliest_finish.values()) if earliest_finish else 0.0
    if pd.isna(total_duration):
        total_duration = 0.0
    
    # 3. 回溯关键路径 (Backward Pass & Path Tracing)
    # 找到所有终点
    end_nodes = [n for n in G.nodes() if G.out_degree(n) == 0]
    # 假设只有一个最终汇聚点，或者取结束时间最晚的点作为终点
    final_node = max(end_nodes, key=lambda x: earliest_finish[x])
    
    critical_path = []
    current_node = final_node
    
    while current_node:
        critical_path.append(current_node)
        duration = G.nodes[current_node]['weight']
        target_start_time = earliest_finish[current_node] - duration
        
        predecessors = list(G.predecessors(current_node))
        if not predecessors:
            break
            
        # 寻找哪个前驱节点的结束时间正好等于当前节点的开始时间
        next_node = None
        for p in predecessors:
            if abs(earliest_finish[p] - target_start_time) < 0.001:
                next_node = p
                break
        current_node = next_node

    critical_path.reverse()
    
    # 4. 准备绘图数据
    plot_data = []
    for node in G.nodes():
        is_critical = node in critical_path
        original_duration = G.nodes[node].get('original_duration', G.nodes[node]['weight'])
        unit = G.nodes[node].get('unit', 's')
        plot_data.append({
            "Task": node,
            "Start": earliest_start[node],
            "Duration": G.nodes[node]['weight'],
            "Finish": earliest_finish[node],
            "Critical": "是 (瓶颈)" if is_critical else "否",
            "Original_Duration": original_duration,
            "Unit": unit
        })
    
    plot_df = pd.DataFrame(plot_data)
    # 排序以便甘特图显示美观 (按开始时间)
    plot_df = plot_df.sort_values(by="Start")
    
    return G, plot_df, total_duration, critical_path

# --- 主界面展示 ---
# 检查是否有有效任务
tasks_available = has_valid_tasks(edited_df)

if not tasks_available:
    st.info("📝 请在上方添加至少一个任务才能开始分析")
    
# 根据是否有任务来决定按钮状态
if tasks_available:
    if st.button("🔍 开始分析与优化", type="primary", use_container_width=True):
        analyze = True
    else:
        analyze = False
else:
    # 禁用按钮，使用灰色样式
    st.button("🔍 开始分析与优化", type="secondary", disabled=True, use_container_width=True)
    analyze = False

if analyze:
    try:
        result = calculate_critical_path(edited_df)
        
        # 检查结果是否为错误信息
        if len(result) == 3 and isinstance(result[2], str) and "错误" in result[2]:
            st.error(result[2])
        elif len(result) != 4:
            logger.error(f"返回结果格式错误：{result}")
            st.error("未知错误：函数返回了意外格式的结果")
        else:
            G, plot_df, total_time, c_path = result
            
            # 核心指标看板
            col1, col2, col3 = st.columns(3)
            col1.metric("📉 理论最小总耗时", f"{total_time:.2f} 秒")
            col2.metric("🔴 关键路径任务数", f"{len(c_path)} 个")
            col3.metric("📊 总任务数", f"{len(plot_df)} 个")
                        
            st.success(f"关键路径链条：{' ➔ '.join(c_path)}")
            
            # 甘特图展示
            st.subheader("📅 任务编排甘特图 (红色为关键路径)")
            
            color_map = {"是 (瓶颈)": "#FF4B4B", "否": "#4B9BFF"}
            
            # 检查数据是否为空
            if plot_df.empty:
                logger.warning("没有可用的任务数据来生成甘特图")
                st.warning("⚠️ 没有可用的任务数据来生成甘特图")
            else:
                # 按开始时间排序
                plot_df_sorted = plot_df.sort_values(by='Start', ascending=True).reset_index(drop=True)
                
                # 分离关键路径和非关键路径任务
                critical_df = plot_df_sorted[plot_df_sorted['Critical'] == '是 (瓶颈)']
                non_critical_df = plot_df_sorted[plot_df_sorted['Critical'] == '否']
                
                fig = go.Figure()
                
                # 添加非关键路径任务（蓝色）
                if not non_critical_df.empty:
                    # 创建悬停文本，显示原始耗时和单位
                    hover_texts = []
                    for _, row in non_critical_df.iterrows():
                        original_dur = row.get('Original_Duration', row['Duration'])
                        unit = row.get('Unit', 's')
                        unit_label = TIME_UNIT_LABELS.get(unit, unit)
                        hover_texts.append(
                            f"<b>{row['Task']}</b><br>"
                            f"开始：{row['Start']:.2f}秒<br>"
                            f"耗时：{original_dur} {unit_label} ({row['Duration']:.2f}秒)<br>"
                            f"结束：{row['Finish']:.2f}秒"
                        )
                    
                    fig.add_trace(go.Bar(
                        name='否',
                        y=non_critical_df['Task'],
                        x=non_critical_df['Duration'],
                        base=non_critical_df['Start'],
                        orientation='h',
                        marker_color='#4B9BFF',
                        hovertemplate='%{text}<extra></extra>',
                        text=hover_texts
                    ))
                
                # 添加关键路径任务（红色）
                if not critical_df.empty:
                    # 创建悬停文本，显示原始耗时和单位
                    hover_texts = []
                    for _, row in critical_df.iterrows():
                        original_dur = row.get('Original_Duration', row['Duration'])
                        unit = row.get('Unit', 's')
                        unit_label = TIME_UNIT_LABELS.get(unit, unit)
                        hover_texts.append(
                            f"<b>{row['Task']}</b><br>"
                            f"开始：{row['Start']:.2f}秒<br>"
                            f"耗时：{original_dur} {unit_label} ({row['Duration']:.2f}秒)<br>"
                            f"结束：{row['Finish']:.2f}秒"
                        )
                    
                    fig.add_trace(go.Bar(
                        name='是 (瓶颈)',
                        y=critical_df['Task'],
                        x=critical_df['Duration'],
                        base=critical_df['Start'],
                        orientation='h',
                        marker_color='#FF4B4B',
                        hovertemplate='%{text}<extra></extra>',
                        text=hover_texts
                    ))
                
                # 确定 X 轴范围
                max_finish = plot_df_sorted['Finish'].max()
                if start_date:
                    # 如果选择了开始日期，X 轴显示为日期格式
                    from datetime import datetime, timedelta
                    start_datetime = datetime.combine(start_date, datetime.min.time())
                    fig.update_xaxes(
                        range=[start_datetime, start_datetime + timedelta(seconds=max_finish * 1.1)],
                        tickformat='%Y-%m-%d',
                        title='日期'
                    )
                else:
                    # 默认从 0 开始
                    fig.update_xaxes(
                        range=[0, max_finish * 1.1],
                        title='时间（秒）'
                    )
                
                fig.update_layout(
                    title='任务时间轴可视化',
                    xaxis_title='日期' if start_date else '时间（秒）',
                    yaxis_title='任务',
                    barmode='relative',
                    height=400,
                    margin=dict(l=100, r=0, t=30, b=0),
                    showlegend=True
                )
                
                fig.update_yaxes(type='category', autorange='reversed')
                
                st.plotly_chart(fig, use_container_width=True)
            
            # 依赖关系拓扑图
            st.subheader("🕸️ 任务依赖拓扑图")
            fig_ax, ax = plt.subplots(figsize=(12, 8))
            # 使用 Graphviz 的 dot 布局算法
            pos = nx.drawing.nx_pydot.graphviz_layout(G, prog='dot')
            
            # 节点颜色
            node_colors = [color_map["是 (瓶颈)"] if n in c_path else color_map["否"] for n in G.nodes()]
            
            nx.draw_networkx_edges(G, pos, ax=ax, arrowstyle='->', arrowsize=20, edge_color='gray')
            nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, node_size=2000, alpha=0.9)
            
            # 标签包含耗时和单位
            def format_node_label(node):
                node_data = G.nodes[node]
                weight = node_data['weight']
                original_duration = node_data.get('original_duration', weight)
                unit = node_data.get('unit', 's')
                unit_label = TIME_UNIT_LABELS.get(unit, unit)
                return f"{node}\n({original_duration} {unit_label})"
            
            labels = {n: format_node_label(n) for n in G.nodes()}
            nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=10, font_weight='bold', font_family='sans-serif')
            
            ax.set_title("任务依赖关系与关键路径高亮", fontsize=14, fontfamily='sans-serif')
            ax.axis('off')
            plt.tight_layout()
            st.pyplot(fig_ax)
            
            # 详细数据表
            with st.expander("查看详细计算数据"):
                st.dataframe(plot_df.style.applymap(lambda x: 'background-color: #ffe6e6' if x == "是 (瓶颈)" else '', subset=['Critical']))
            
            # ========== 有限线程调度分析 ==========
            if use_limited_threads:
                st.markdown("---")
                st.subheader("🧵 有限线程下的任务最优排列")
                
                try:
                    with st.spinner('正在计算最优调度方案...'):
                        scheduled_tasks = {}  # 初始化变量
                        
                        if auto_optimize:
                            # 自动优化线程数
                            optimal_threads, optimized_time, thread_schedules = optimize_thread_count(
                                edited_df, max_threads, start_time=0.0
                            )
                            st.success(f"✅ 最优线程数：**{optimal_threads}** 个，预计总耗时：**{optimized_time:.2f}** 秒")
                            
                            # 重新计算一次以获取 scheduled_tasks
                            _, scheduled_tasks = schedule_tasks_limited_threads(
                                edited_df, optimal_threads, start_time=0.0
                            )
                            
                            # 显示不同线程数的对比
                            comparison_data = []
                            for test_threads in range(1, min(optimal_threads + 2, max_threads + 1)):
                                test_schedules, _ = schedule_tasks_limited_threads(edited_df, test_threads, 0.0)
                                if test_schedules:
                                    test_total_time = max((ts.total_time for ts in test_schedules), default=0.0)
                                    improvement = ((comparison_data[0]['time'] - test_total_time) / comparison_data[0]['time'] * 100) if comparison_data else 0
                                    comparison_data.append({
                                        'threads': test_threads,
                                        'time': test_total_time,
                                        'improvement': improvement
                                    })
                            
                            if len(comparison_data) > 1:
                                comp_df = pd.DataFrame(comparison_data)
                                fig_comp = go.Figure()
                                fig_comp.add_trace(go.Scatter(
                                    x=comp_df['threads'],
                                    y=comp_df['time'],
                                    mode='lines+markers',
                                    name='总耗时',
                                    line=dict(color='red', width=3)
                                ))
                                fig_comp.update_layout(
                                    title='线程数与总耗时关系图',
                                    xaxis_title='线程数',
                                    yaxis_title='总耗时（秒）',
                                    height=400
                                )
                                st.plotly_chart(fig_comp, use_container_width=True)
                        else:
                            # 使用指定的线程数
                            thread_schedules, scheduled_tasks = schedule_tasks_limited_threads(
                                edited_df, num_threads, start_time=0.0
                            )
                        
                        if thread_schedules:
                            # 计算总完成时间
                            total_completion_time = max(
                                (ts.total_time for ts in thread_schedules),
                                default=0.0
                            )
                            
                            # 显示线程利用率
                            utilization = calculate_thread_utilization(thread_schedules, total_completion_time)
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("⏱️ 总完成时间", f"{total_completion_time:.2f} 秒")
                            with col2:
                                avg_util = sum(utilization.values()) / len(utilization) if utilization else 0
                                st.metric("📊 平均线程利用率", f"{avg_util:.1f}%")
                            
                            # 绘制多线程甘特图
                            gantt_df = generate_gantt_data(thread_schedules, scheduled_tasks)
                            
                            if not gantt_df.empty:
                                st.subheader(f"📅 {num_threads if not auto_optimize else optimal_threads} 个线程的任务调度甘特图")
                                
                                fig_multi_thread = go.Figure()
                                
                                # 为每个线程添加任务条
                                for thread_id in sorted(gantt_df['Thread'].unique()):
                                    thread_data = gantt_df[gantt_df['Thread'] == thread_id]
                                    
                                    # 创建悬停文本
                                    hover_texts = []
                                    for _, row in thread_data.iterrows():
                                        unit_label = TIME_UNIT_LABELS.get(row['Unit'], row['Unit'])
                                        deps_text = f"<br>依赖：{row['Dependencies']}" if row['Dependencies'] else ""
                                        hover_texts.append(
                                            f"<b>{row['Task']}</b><br>"
                                            f"线程 {thread_id}<br>"
                                            f"开始：{row['Start']:.2f}秒<br>"
                                            f"耗时：{row['Original_Duration']} {unit_label} ({row['Duration']:.2f}秒)<br>"
                                            f"结束：{row['Finish']:.2f}秒{deps_text}"
                                        )
                                    
                                    fig_multi_thread.add_trace(go.Bar(
                                        name=f'线程 {thread_id}',
                                        y=[f'T{thread_id}'] * len(thread_data),
                                        x=thread_data['Duration'],
                                        base=thread_data['Start'],
                                        orientation='h',
                                        marker_color=px.colors.qualitative.Set3[thread_id % len(px.colors.qualitative.Set3)],
                                        hovertemplate='%{text}<extra></extra>',
                                        text=hover_texts
                                    ))
                                
                                # X 轴设置
                                if start_date:
                                    start_datetime = datetime.combine(start_date, datetime.min.time())
                                    fig_multi_thread.update_xaxes(
                                        range=[start_datetime, start_datetime + timedelta(seconds=total_completion_time * 1.1)],
                                        tickformat='%Y-%m-%d',
                                        title='日期'
                                    )
                                else:
                                    fig_multi_thread.update_xaxes(
                                        range=[0, total_completion_time * 1.1],
                                        title='时间（秒）'
                                    )
                                
                                fig_multi_thread.update_layout(
                                    title=f'有限线程调度甘特图 ({num_threads if not auto_optimize else optimal_threads} 线程)',
                                    xaxis_title='日期' if start_date else '时间（秒）',
                                    yaxis_title='线程',
                                    barmode='relative',
                                    height=max(300, len(thread_schedules) * 80),
                                    margin=dict(l=50, r=0, t=50, b=0),
                                    showlegend=True
                                )
                                
                                fig_multi_thread.update_yaxes(type='category')
                                
                                st.plotly_chart(fig_multi_thread, use_container_width=True)
                                
                                # 显示每个线程的详细任务列表
                                with st.expander("查看各线程详细任务安排"):
                                    for thread_schedule in thread_schedules:
                                        st.write(f"**线程 {thread_schedule.thread_id}** (总耗时：{thread_schedule.total_time:.2f}秒)")
                                        thread_table = gantt_df[gantt_df['Thread'] == thread_schedule.thread_id][[
                                            'Task', 'Start', 'Duration', 'Finish', 'Original_Duration', 'Unit', 'Dependencies'
                                        ]].copy()
                                        thread_table.columns = ['任务 ID', '开始时间 (秒)', '持续时间 (秒)', '结束时间 (秒)', 
                                                              '原始耗时', '单位', '依赖']
                                        st.dataframe(thread_table, use_container_width=True)
                                
                                # 显示所有任务的调度信息
                                with st.expander("查看所有任务调度详情"):
                                    st.dataframe(gantt_df[[
                                        'Task', 'Thread', 'Start', 'Duration', 'Finish', 
                                        'Original_Duration', 'Unit', 'Dependencies'
                                    ]], use_container_width=True)
                        else:
                            st.warning("⚠️ 无法生成调度方案，请检查任务数据")
                    
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    logger.error(f"有限线程调度计算错误：{e}\n{error_details}")
                    st.error(f"调度计算失败：{str(e)}")

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"分析过程中发生错误：{e}\n{error_details}")
        st.error(f"发生错误：{str(e)}")
        st.warning("💡 请检查任务 ID 是否唯一，以及依赖的 ID 是否存在于列表中。")

# --- 底部说明 ---
st.markdown("---")
st.caption("💡 **优化建议**: 尝试减少红色 (关键路径) 任务的耗时，或者将长任务拆分为可并行的子任务，以缩短总工期。")