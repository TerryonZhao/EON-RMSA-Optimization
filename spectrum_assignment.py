import numpy as np
import modulation  # 用于计算 FSU 数量


def split_traffic(demand_gbps, link_length_km):
    """
    如果流量超过单个光通道的最大容量，则拆分成多个并行请求。
    :param demand_gbps: 需求流量 (Gbps)
    :param link_length_km: 该流量所经过的最长链路长度 (km)
    :return: 拆分后的请求列表，每个请求的流量 (Gbps)
    """
    max_capacity = modulation.get_max_capacity(link_length_km)  # 获取该链路的最大传输能力
    if demand_gbps > max_capacity:
        num_paths = int(np.ceil(demand_gbps / max_capacity))  # 计算所需的 lightpath 数量
        return [demand_gbps / num_paths] * num_paths  # 拆分成多个 lightpath
    else:
        return [demand_gbps]  # 如果小于最大容量，则不拆分


def first_fit_spectrum_assignment(G, path, demand, spectrum):
    """
    First-Fit 频谱分配算法
    Input:
        - G:        解析出的Topology，用于找出path中的最大link长度，以便确定调制方式
        - path:     routing.py的输出，即找出的最短路径
        - demand：  本次的流量需求，单位：Gbps
        - spectrum: 字典{(u, v): np.ones(320) for u, v in G.edges()}；用于记录某段link的FSU使用情况，在主函数中定义

    Output:
        - i:        FSU的索引
    """
    total_slots = 320  # 总共 320 个 FSU
    path_length_km = sum(G[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1)) # 计算path的长度（确定Modulation）

    num_slots, modulation_used = modulation.compute_required_fsus(demand, path_length_km)

    # 1️⃣ **找到所有链路的可用频谱**
    # Spectrum Continuity (对应第3️⃣步）
    # 考虑所有的link，找出所有link都能用的FSU
    available_slots = np.ones(total_slots)  # 初始化全部可用

    for i in range(len(path) - 1):
        link = (path[i], path[i+1])
        if link in spectrum:
            available_slots *= spectrum[link]

    # 2️⃣ **搜索第一个连续的 num_slots 可用频谱块**
    # Spectrum Contiguity：被分配的FSUs必须是连续的
    for i in range(total_slots - num_slots + 1):
        if np.all(available_slots[i:i+num_slots] == 1):  # 该范围内所有槽位都可用
            # 3️⃣ **在路径上的所有链路上分配该频谱槽**
            for j in range(len(path) - 1):
                link = (path[j], path[j+1])
                spectrum[link][i:i+num_slots] = 0  # 标记已占用
            return i  # 返回起始频谱槽索引

    return -1  # **如果找不到合适的频谱块，返回失败**

def most_used_spectrum_assignment(G, path, demand, spectrum):
    """
    Most-Used 频谱分配算法：
    1) 计算所需的FSU数目
    2) 统计每个FSU在整个网络上的“被使用次数”（usage数组）
    3) 寻找长度为 num_slots 的所有可行连续块，并按照其在 usage 上的总使用度 从高到低 排序
    4) 依次检查是否在 path 所有链路上可用，如可用则分配并返回其起始FSU索引

    Input:
        - G:        解析出的Topology(网络图)，可用于计算 path 长度
        - path:     由routing.py等模块输出的路由（节点列表）
        - demand:   本次的流量需求 (Gbps)
        - spectrum: 字典, 记录各链路的频谱使用情况
                    形如 {(u, v): np.ones(320) for u, v in G.edges()}；
                    其中 1 表示空闲，0 表示已占用
    Output:
        - i:        成功时，返回分配的FSU的起始索引；若无可用分配块，则返回 -1
    """

    # ====== 1. 计算所需FSU数目 ======
    total_slots = 320
    # 计算路径长度
    path_length_km = sum(G[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1))
    # 计算所需FSU数量
    num_slots, modulation_used = modulation.compute_required_fsus(demand, path_length_km)

    # ====== 2. 统计每个FSU在“整个网络”上的使用情况 ======
    # spectrum[link][s] = 1 表示空闲, 0 表示被占用
    # 我们希望得到 usage[s] = 该 slot s 在所有link中被 "使用" 的次数
    usage = np.zeros(total_slots, dtype=float)
    for link, fsu_array in spectrum.items():
        # 1 - fsu_array[s] 表示该slot是否被占用(1占用,0空闲)
        usage += (1 - fsu_array)  # element-wise 相加

    # ====== 3. 对所有“连续 num_slots 大小”的候选区段, 计算其 usage 之和并从高到低排序 ======
    block_usage_list = []
    for start_slot in range(total_slots - num_slots + 1):
        # 计算 [start_slot, start_slot + num_slots) 的 usage 之和
        block_usage_sum = np.sum(usage[start_slot : start_slot + num_slots])
        block_usage_list.append((block_usage_sum, start_slot))

    # 按使用度从高到低排序（“最拥挤”的优先）
    block_usage_list.sort(key=lambda x: x[0], reverse=True)

    # ====== 4. 逐一检查这些区段在 path 上是否都空闲；若空闲则分配并返回 ======
    for block_usage_sum, start_idx in block_usage_list:
        # 检查在 path 上所有link的该区段是否可用
        can_allocate = True
        for i in range(len(path) - 1):
            link = (path[i], path[i+1])
            # 如果有任意一个slot被占用，则无法分配
            if not np.all(spectrum[link][start_idx : start_idx + num_slots] == 1):
                can_allocate = False
                break

        if can_allocate:
            # 执行分配：将该区段标记为占用(0)
            for i in range(len(path) - 1):
                link = (path[i], path[i+1])
                spectrum[link][start_idx : start_idx + num_slots] = 0
            return start_idx  # 成功分配，返回该区段的首位索引

    # 如果遍历完所有区段都无法分配，则返回 -1
    return -1

def best_fit_spectrum_assignment(G, path, demand, spectrum):
    """
    Best-Fit 频谱分配算法
    Input:
        - G:        解析出的Topology，用于找出path中的最大link长度，以便确定调制方式
        - path:     routing.py的输出，即找出的最短路径
        - demand：  本次的流量需求，单位：Gbps
        - spectrum: 字典{(u, v): np.ones(320) for u, v in G.edges()}；用于记录某段link的FSU使用情况，在主函数中定义

    Output:
        - i:        FSU的起始索引
    """
    total_slots = 320  # 总共 320 个 FSU
    path_length_km = sum(G[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1))  # 计算路径长度

    # 计算所需 FSU 数量和调制格式
    num_slots, modulation_used = modulation.compute_required_fsus(demand, path_length_km)

    # 获取所有链路的可用频谱
    available_slots = np.ones(total_slots)  # 初始化全部可用
    for i in range(len(path) - 1):
        link = (path[i], path[i+1])
        if link in spectrum:
            available_slots *= spectrum[link]  # 只保留所有链路均可用的FSU

    # 查找所有连续的可用频谱块
    # 记录所有符合 `num_slots` 条件的可用块 (start_index, 块大小)
    candidate_blocks = []
    start = -1
    length = 0

    for i in range(total_slots):
        if available_slots[i] == 1:
            if start == -1:
                start = i
            length += 1
        else:
            if length >= num_slots:
                candidate_blocks.append((start, length))
            start = -1
            length = 0

    # 如果循环结束时仍有一个可用块
    if length >= num_slots:
        candidate_blocks.append((start, length))

    # 选择最小可用块（Best Fit）
    if not candidate_blocks:
        return -1  # 没有可用的 FSU 块，分配失败

    best_block = min(candidate_blocks, key=lambda x: x[1])  # 选择最小合适的可用块
    start_index = best_block[0]

    # 在路径上的所有链路上分配该频谱块
    for j in range(len(path) - 1):
        link = (path[j], path[j+1])
        spectrum[link][start_index:start_index+num_slots] = 0  # 标记已占用

    return start_index  # 返回分配的起始 FSU 索引

# -------------------------------------------- Task 5 -------------------------------------------------
def can_reuse_fsu(G, path, fsu_start, shared_spectrum, active_primary_paths):
    """
    检查是否可以复用某个 FSU
    Input:
        - G: 网络拓扑
        - path: 备用路径
        - fsu_start: 备选 FSU 的起始位置
        - num_slots: 该流量所需的 FSU 数量
        - shared_spectrum: 记录哪些 FSU 被哪些流量共享
        - active_primary_paths: 记录主路径流量的占用情况 {流量: [主路径上的链路]}

    Output:
        - True: 可以复用
        - False: 不能复用
    """
    conflicting = False  # 是否有冲突

    for j in range(len(path) - 1):
        link = (path[j], path[j + 1])

        # 如果该链路上没有 `fsu_start`，则无法复用
        if link not in shared_spectrum or fsu_start not in shared_spectrum[link]:
            return False

        # 检查已有共享的流量
        existing_flows = shared_spectrum[link][fsu_start]  # 获取已使用该 FSU 的流量
        for existing_flow in existing_flows:
            # 检查主路径是否重叠（如果主路径冲突，则不能复用）
            if existing_flow in active_primary_paths:
                existing_primary_links = set(active_primary_paths[existing_flow])
                current_primary_links = set(active_primary_paths.get(path, []))  # 获取当前流量的主路径
                if existing_primary_links & current_primary_links:  # 两个路径有交集
                    conflicting = True
                    break

        if conflicting:
            return False  # 发现冲突，不能复用

    return True  # 没有冲突，可以复用


def shared_fit_spectrum_assignment(G, path, demand, spectrum, shared_spectrum, active_primary_paths):
    """
    共享保护的 Best-Fit 频谱分配算法
    Input:
        - G:              网络拓扑
        - path:           备用路径
        - demand:         需要分配的流量需求，单位：Gbps
        - spectrum:       记录所有链路的FSU使用情况 {(u, v): np.ones(320) for u, v in G.edges()}
        - shared_spectrum: 记录备用路径上的FSU共享情况 {(u, v): {fsu_start: [流量1, 流量2]}}
        - active_primary_paths: 记录主路径流量的占用情况 {流量: [主路径上的链路]}

    Output:
        - i:              分配的FSU起始索引，失败返回 -1
    """
    total_slots = 320
    path_length_km = sum(G[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1))

    # 计算所需 FSU 数量和调制格式
    num_slots, modulation_used = modulation.compute_required_fsus(demand, path_length_km)

    # 尝试复用共享 FSU
    for i in range(total_slots - num_slots + 1):  # 遍历所有可能的 FSU 起点
        if can_reuse_fsu(G, path, i, shared_spectrum, active_primary_paths):
            # 复用已有 FSU
            for j in range(len(path) - 1):
                link = (path[j], path[j+1])
                shared_spectrum[link][i].append(demand)  # 记录该 FSU 复用于当前流量
            return i  # 返回复用的 FSU 起始索引

    # 如果没有可复用的 FSU，则执行 Best Fit 方式
    start_index = best_fit_spectrum_assignment(G, path, demand, spectrum)

    if start_index == -1:
        return -1  # 没有可用的 FSU，分配失败

    # 分配 FSU 并更新 `shared_spectrum`
    for j in range(len(path) - 1):
        link = (path[j], path[j+1])
        if link not in shared_spectrum:
            shared_spectrum[link] = {}

        # 初始化 FSU 共享列表
        for k in range(start_index, start_index + num_slots):
            if k not in shared_spectrum[link]:
                shared_spectrum[link][k] = []
            shared_spectrum[link][k].append(demand)  # 记录流量共享情况

    return start_index  # 返回分配的起始 FSU 索引



