"""
有限线程下的任务最优排列模块

基于资源受限项目调度问题 (RCPSP) 的启发式算法
使用贪心算法 + 优先级调度实现有限线程下的最优任务排列
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """已调度的任务信息"""
    task_id: str
    thread_id: int
    start_time: float
    duration: float
    end_time: float
    dependencies: List[str]
    original_duration: float
    unit: str


@dataclass
class ThreadSchedule:
    """线程调度方案"""
    thread_id: int
    tasks: List[ScheduledTask]
    total_time: float


def parse_dependencies(deps_str: str) -> List[str]:
    """解析依赖关系字符串"""
    if pd.isna(deps_str) or deps_str is None:
        return []
    
    deps_str = str(deps_str).strip()
    if not deps_str:
        return []
    
    return [d.strip() for d in deps_str.split(',') if d.strip()]


def topological_sort_with_priority(
    df: pd.DataFrame,
    task_durations: Dict[str, float],
    task_units: Dict[str, str],
    task_deps: Dict[str, List[str]]
) -> List[str]:
    """
    带优先级的拓扑排序
    
    优先级规则：
    1. 依赖数多的任务优先（下游任务多）
    2. 耗时长的任务优先（关键路径思想）
    3. 最早可能开始时间早的优先
    """
    # 构建入度和邻接表
    in_degree = {task_id: 0 for task_id in task_durations.keys()}
    successors = {task_id: [] for task_id in task_durations.keys()}
    
    for task_id, deps in task_deps.items():
        in_degree[task_id] = len(deps)
        for dep in deps:
            if dep in successors:
                successors[dep].append(task_id)
    
    # 计算每个任务的优先级分数
    priority_scores = {}
    for task_id in task_durations.keys():
        # 优先级 = 后继任务数 * 2 + 持续时间权重
        successor_count = len(successors[task_id])
        duration_weight = task_durations[task_id] / max(task_durations.values()) if task_durations.values() else 0
        priority_scores[task_id] = successor_count * 2 + duration_weight
    
    # Kahn 算法进行拓扑排序
    result = []
    available = [task_id for task_id, degree in in_degree.items() if degree == 0]
    
    while available:
        # 按优先级排序，优先级高的先执行
        available.sort(key=lambda x: (-priority_scores[x], -task_durations[x]))
        current = available.pop(0)
        result.append(current)
        
        # 更新后继节点的入度
        for successor in successors[current]:
            in_degree[successor] -= 1
            if in_degree[successor] == 0:
                available.append(successor)
    
    if len(result) != len(task_durations):
        logger.warning("检测到循环依赖或无效依赖")
        return []
    
    return result


def schedule_tasks_limited_threads(
    df: pd.DataFrame,
    num_threads: int = 2,
    start_time: float = 0.0
) -> Tuple[List[ThreadSchedule], Dict[str, ScheduledTask]]:
    """
    有限线程下的任务调度算法
    
    参数:
        df: 包含任务数据的 DataFrame (id, duration, unit, deps)
        num_threads: 可用线程数
        start_time: 开始时间（秒）
    
    返回:
        (thread_schedules, task_mapping)
        thread_schedules: 每个线程的调度方案
        task_mapping: 任务 ID 到 ScheduledTask 的映射
    """
    if num_threads <= 0:
        raise ValueError("线程数必须大于 0")
    
    # 1. 解析任务数据
    task_durations = {}  # task_id -> duration_in_seconds
    task_units = {}  # task_id -> unit
    task_deps = {}  # task_id -> list of dependencies
    original_durations = {}  # task_id -> original_duration
    
    TIME_UNIT_TO_SECONDS = {
        'ms': 0.001,
        's': 1,
        'min': 60,
        'h': 3600,
        'd': 86400,
        'week': 604800,
        'month': 2592000,
        'year': 31536000
    }
    
    for _, row in df.iterrows():
        task_id = str(row['id']).strip()
        if not task_id or pd.isna(row['duration']):
            continue
        
        # 转换持续时间为秒
        unit = str(row.get('unit', 's')).strip()
        if unit not in TIME_UNIT_TO_SECONDS:
            unit = 's'
        
        duration_seconds = float(row['duration']) * TIME_UNIT_TO_SECONDS[unit]
        
        task_durations[task_id] = duration_seconds
        task_units[task_id] = unit
        original_durations[task_id] = float(row['duration'])
        task_deps[task_id] = parse_dependencies(row['deps'])
    
    if not task_durations:
        return [], {}
    
    # 2. 拓扑排序获取执行顺序
    sorted_tasks = topological_sort_with_priority(
        df, task_durations, task_units, task_deps
    )
    
    if not sorted_tasks:
        logger.error("拓扑排序失败")
        return [], {}
    
    # 3. 贪心调度：为每个任务分配最早的可用线程
    thread_end_times = [start_time] * num_threads  # 每个线程的当前结束时间
    task_end_times = {}  # 记录每个任务的结束时间
    task_to_thread = {}  # 记录每个任务分配到哪个线程
    scheduled_tasks = {}  # task_id -> ScheduledTask
    
    for task_id in sorted_tasks:
        duration = task_durations[task_id]
        deps = task_deps[task_id]
        
        # 计算该任务的最早开始时间（依赖约束）
        earliest_start_from_deps = start_time
        for dep in deps:
            if dep in task_end_times:
                earliest_start_from_deps = max(earliest_start_from_deps, task_end_times[dep])
        
        # 找到最早可用的线程（满足依赖约束）
        best_thread = -1
        best_start_time = float('inf')
        
        for thread_id in range(num_threads):
            # 该线程可以开始的时间
            thread_available_time = thread_end_times[thread_id]
            # 实际开始时间是依赖约束和线程可用时间的最大值
            actual_start = max(thread_available_time, earliest_start_from_deps)
            
            if actual_start < best_start_time:
                best_start_time = actual_start
                best_thread = thread_id
        
        # 分配任务到该线程
        task_start = best_start_time
        task_end = task_start + duration
        
        scheduled_task = ScheduledTask(
            task_id=task_id,
            thread_id=best_thread,
            start_time=task_start,
            duration=duration,
            end_time=task_end,
            dependencies=deps,
            original_duration=original_durations[task_id],
            unit=task_units[task_id]
        )
        
        scheduled_tasks[task_id] = scheduled_task
        task_end_times[task_id] = task_end
        task_to_thread[task_id] = best_thread
        thread_end_times[best_thread] = task_end
    
    # 4. 按线程组织调度结果
    thread_schedules = []
    for thread_id in range(num_threads):
        thread_tasks = [
            task for task in scheduled_tasks.values() 
            if task.thread_id == thread_id
        ]
        # 按开始时间排序
        thread_tasks.sort(key=lambda x: x.start_time)
        
        total_time = thread_end_times[thread_id] - start_time if thread_tasks else 0.0
        
        thread_schedule = ThreadSchedule(
            thread_id=thread_id,
            tasks=thread_tasks,
            total_time=total_time
        )
        thread_schedules.append(thread_schedule)
    
    return thread_schedules, scheduled_tasks


def generate_gantt_data(
    thread_schedules: List[ThreadSchedule],
    scheduled_tasks: Dict[str, ScheduledTask]
) -> pd.DataFrame:
    """
    生成甘特图数据
    
    返回包含以下列的 DataFrame:
    - Task: 任务 ID
    - Thread: 线程 ID
    - Start: 开始时间
    - Duration: 持续时间
    - Finish: 结束时间
    - Original_Duration: 原始耗时
    - Unit: 单位
    """
    gantt_data = []
    
    for thread_schedule in thread_schedules:
        for task in thread_schedule.tasks:
            gantt_data.append({
                'Task': task.task_id,
                'Thread': task.thread_id,
                'Start': task.start_time,
                'Duration': task.duration,
                'Finish': task.end_time,
                'Original_Duration': task.original_duration,
                'Unit': task.unit,
                'Dependencies': ', '.join(task.dependencies) if task.dependencies else ''
            })
    
    # 按线程和开始时间排序
    df = pd.DataFrame(gantt_data)
    if not df.empty:
        df = df.sort_values(['Thread', 'Start'], ascending=[True, True]).reset_index(drop=True)
    
    return df


def calculate_thread_utilization(
    thread_schedules: List[ThreadSchedule],
    total_project_time: float
) -> Dict[int, float]:
    """
    计算每个线程的利用率
    
    返回：{thread_id: utilization_percentage}
    """
    utilization = {}
    
    for thread_schedule in thread_schedules:
        if total_project_time <= 0:
            utilization[thread_schedule.thread_id] = 0.0
            continue
        
        # 线程工作时间 = 所有任务持续时间之和
        work_time = sum(task.duration for task in thread_schedule.tasks)
        utilization[thread_schedule.thread_id] = (work_time / total_project_time) * 100
    
    return utilization


def optimize_thread_count(
    df: pd.DataFrame,
    max_threads: int = 10,
    start_time: float = 0.0
) -> Tuple[int, float, List[ThreadSchedule]]:
    """
    自动优化线程数量，找到性价比最高的线程数
    
    通过分析增加线程带来的收益递减点来确定最优线程数
    
    返回：(optimal_threads, total_time, thread_schedules)
    """
    results = []
    
    for num_threads in range(1, max_threads + 1):
        thread_schedules, _ = schedule_tasks_limited_threads(
            df, num_threads, start_time
        )
        
        if not thread_schedules:
            continue
        
        # 计算总完成时间（所有线程中最晚结束的时间）
        total_time = max(
            (ts.total_time for ts in thread_schedules),
            default=0.0
        )
        
        results.append((num_threads, total_time, thread_schedules))
    
    if not results:
        return 1, float('inf'), []
    
    # 找到最优线程数（最短总耗时）
    # 策略：选择能产生最短总耗时的最少线程数
    best_result = min(results, key=lambda x: x[1])
    optimal_threads = best_result[0]
    
    # 如果有多个线程数产生相同的最短时间，选择线程数最少的（节省资源）
    min_time = best_result[1]
    for num_threads, total_time, schedules in results:
        if abs(total_time - min_time) < 0.001:  # 时间基本相同
            optimal_threads = num_threads
            break
    
    # 返回最优结果的调度方案
    for num_threads, total_time, schedules in results:
        if num_threads == optimal_threads:
            return optimal_threads, total_time, schedules
    
    return optimal_threads, results[-1][1], results[-1][2]
