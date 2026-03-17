import streamlit as st
import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import logging

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
st.sidebar.header("1. 定义任务")
st.sidebar.info("💡 提示：依赖关系填写任务 ID (如：A, B)，多个依赖用逗号分隔。", icon="💡")

# 空数据框模板（无默认数据）
empty_df = pd.DataFrame(columns=["id", "duration", "deps"])

# 使用 Session State 保持数据状态
if 'df' not in st.session_state:
    # 初始化为一个空行，方便用户输入
    st.session_state.df = pd.DataFrame({'id': [''], 'duration': [0], 'deps': ['']})

def update_df():
    # 这里简单处理，实际生产中可以用 st.data_editor 直接编辑
    pass

# --- CSV 文件上传功能 ---
st.sidebar.markdown("---")
st.sidebar.subheader("📁 导入 CSV 文件")
uploaded_file = st.sidebar.file_uploader(
    "上传 CSV 文件",
    type=["csv"],
    help="CSV 格式：id, duration, deps"
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
            csv_df = csv_df.fillna({'id': '', 'duration': 0, 'deps': ''})
            csv_df['duration'] = pd.to_numeric(csv_df['duration'], errors='coerce').fillna(0).astype(int)
            csv_df['id'] = csv_df['id'].astype(str).str.strip()
            csv_df['deps'] = csv_df['deps'].astype(str).str.strip()
            
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

# 添加重置按钮
if st.sidebar.button("🔄 清空所有任务", use_container_width=True):
    st.session_state.df = pd.DataFrame({'id': [''], 'duration': [0], 'deps': ['']})
    st.rerun()

# 使用可编辑的 DataFrame
try:
    edited_df = st.data_editor(
        st.session_state.df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn("任务 ID (唯一)", required=True),
            "duration": st.column_config.NumberColumn("耗时 (秒)", min_value=0, step=1),
            "deps": st.column_config.TextColumn("前置依赖 ID (逗号分隔)"),
        },
        key="editor",
        hide_index=True
    )
    st.session_state.df = edited_df
except Exception as e:
    logger.error(f"表格加载失败：{e}")
    st.session_state.df = pd.DataFrame({'id': [''], 'duration': [0], 'deps': ['']})
    edited_df = st.data_editor(
        st.session_state.df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "id": st.column_config.TextColumn("任务 ID (唯一)", required=True),
            "duration": st.column_config.NumberColumn("耗时 (秒)", min_value=0, step=1),
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
        
        # 处理耗时，确保是数字
        duration_val = row['duration']
        if pd.isna(duration_val):
            duration = 0.0
        else:
            duration = float(duration_val)
        
        # 处理依赖关系，确保是字符串
        deps_val = row['deps']
        if pd.isna(deps_val) or deps_val is None:
            deps_str = ""
        else:
            deps_str = str(deps_val).strip()
        
        G.add_node(task_id, weight=duration)
        
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
        plot_data.append({
            "Task": node,
            "Start": earliest_start[node],
            "Duration": G.nodes[node]['weight'],
            "Finish": earliest_finish[node],
            "Critical": "是 (瓶颈)" if is_critical else "否"
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
                    fig.add_trace(go.Bar(
                        name='否',
                        y=non_critical_df['Task'],
                        x=non_critical_df['Duration'],
                        base=non_critical_df['Start'],
                        orientation='h',
                        marker_color='#4B9BFF',
                        hovertemplate='<b>%{y}</b><br>开始：%{base}<br>耗时：%{x}<br>结束：%{customdata}<extra></extra>',
                        customdata=non_critical_df['Finish']
                    ))
                
                # 添加关键路径任务（红色）
                if not critical_df.empty:
                    fig.add_trace(go.Bar(
                        name='是 (瓶颈)',
                        y=critical_df['Task'],
                        x=critical_df['Duration'],
                        base=critical_df['Start'],
                        orientation='h',
                        marker_color='#FF4B4B',
                        hovertemplate='<b>%{y}</b><br>开始：%{base}<br>耗时：%{x}<br>结束：%{customdata}<extra></extra>',
                        customdata=critical_df['Finish']
                    ))
                
                fig.update_layout(
                    title='任务时间轴可视化',
                    xaxis_title='时间（秒）',
                    yaxis_title='任务',
                    barmode='relative',
                    height=400,
                    margin=dict(l=100, r=0, t=30, b=0),
                    showlegend=True
                )
                
                fig.update_xaxes(range=[0, plot_df_sorted['Finish'].max() * 1.1])
                fig.update_yaxes(type='category')
                
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
            
            # 标签包含耗时
            labels = {n: f"{n}\n({G.nodes[n]['weight']}s)" for n in G.nodes()}
            nx.draw_networkx_labels(G, pos, labels=labels, ax=ax, font_size=10, font_weight='bold', font_family='sans-serif')
            
            ax.set_title("任务依赖关系与关键路径高亮", fontsize=14, fontfamily='sans-serif')
            ax.axis('off')
            plt.tight_layout()
            st.pyplot(fig_ax)
            
            # 详细数据表
            with st.expander("查看详细计算数据"):
                st.dataframe(plot_df.style.applymap(lambda x: 'background-color: #ffe6e6' if x == "是 (瓶颈)" else '', subset=['Critical']))

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"分析过程中发生错误：{e}\n{error_details}")
        st.error(f"发生错误：{str(e)}")
        st.warning("💡 请检查任务 ID 是否唯一，以及依赖的 ID 是否存在于列表中。")

# --- 底部说明 ---
st.markdown("---")
st.caption("💡 **优化建议**: 尝试减少红色 (关键路径) 任务的耗时，或者将长任务拆分为可并行的子任务，以缩短总工期。")