import networkx as nx
import network  # 解析网络拓扑
import numpy as np
import modulation
import metrics
import spectrum_assignment  # 频谱分配


def fixed_shortest_path_routing(G, src, dst):
    """ 计算最短路径 (Dijkstra) """
    return nx.shortest_path(G, source=src, target=dst, weight='weight')


def k_shortest_paths_routing(G, src, dst, k=5):
    """ 计算 K 最短路径 (Yen's Algorithm) """
    return list(nx.shortest_simple_paths(G, source=src, target=dst, weight='weight'))[:k]


def highest_loaded_path_routing_avg(G, paths, spectrum_utilization):
    """
    选择“平均负载”最高的路径：
      - 1=空闲, 0=占用
      - 先计算该路径上每条链路已占用的FSU数量，然后求平均值
      - 返回平均负载最高的路径
    """
    max_avg_load = -1
    highest_loaded_path = None

    for path in paths:
        if len(path) < 2:
            # 如果 path 只有1个节点或者为空，跳过
            continue

        total_used_slots = 0
        num_links = len(path) - 1  # 链路条数

        for i in range(num_links):
            link = (path[i], path[i + 1])
            # 如果该link不在字典里，就当做全空闲(np.zeros(320) 意味着没有1也没有0吗？这里可按需求处理)
            fsu_array = spectrum_utilization.get(link, np.ones(320))
            # 已占用FSU数 = 320 - 空闲FSU数
            used_on_link = 320 - np.sum(fsu_array)
            total_used_slots += used_on_link

        # 计算该路径的平均已占用数
        avg_load = total_used_slots / num_links

        if avg_load > max_avg_load:
            max_avg_load = avg_load
            highest_loaded_path = path

    return highest_loaded_path


def least_loaded_path_routing_avg(G, paths, spectrum_utilization):
    """
    选择“平均负载”最低的路径：
      - 1=空闲, 0=占用
      - 计算该路径上每条链路的已占用FSU数量，然后求平均值
      - 返回平均负载最低的路径
    """
    min_avg_load = float('inf')
    least_loaded_path = None

    for path in paths:
        if len(path) < 2:
            continue  # 如果 path 只有1个节点或者为空，跳过

        total_used_slots = 0
        num_links = len(path) - 1  # 链路数

        for i in range(num_links):
            link = (path[i], path[i + 1])
            # 获取该链路的光谱利用信息，默认为全空闲（np.ones(320)）
            fsu_array = spectrum_utilization.get(link, np.ones(320))
            # 已占用FSU数 = 320 - 空闲FSU数
            used_on_link = 320 - np.sum(fsu_array)
            total_used_slots += used_on_link

        # 计算该路径的平均已占用FSU数
        avg_load = total_used_slots / num_links

        if avg_load < min_avg_load:
            min_avg_load = avg_load
            least_loaded_path = path

    return least_loaded_path


def entropy_minimization_path_routing_max(G, paths, spectrum_utilization):
    """
    选择 "最大 Shannon 熵" 最低的路径：
      - 计算每条路径上所有链路的碎片化熵
      - 选择 "最坏情况" 熵最小的路径 (即 max 熵 最小)
    """
    min_max_entropy = float('inf')
    best_path = None

    for path in paths:
        if len(path) < 2:
            continue  # 无效路径，跳过

        entropy_list = []

        for i in range(len(path) - 1):
            link = (path[i], path[i + 1])
            fsu_array = spectrum_utilization.get(link, np.ones(320))  # 获取链路光谱使用情况
            entropy = metrics.calculate_fragmentation_entropy(fsu_array)  # 计算碎片化熵
            entropy_list.append(entropy)

        max_entropy = max(entropy_list)  # 选择该路径中碎片化最严重的链路的熵

        if max_entropy < min_max_entropy:
            min_max_entropy = max_entropy
            best_path = path

    return best_path


def entropy_minimization_path_routing_avg(G, paths, spectrum_utilization):
    """
    选择 "平均Shannon 熵" 最低的路径：
      - 计算每条路径上所有链路的碎片化熵
      - 选择整体熵最低的路径
    """
    min_entropy = float('inf')
    best_path = None

    for path in paths:
        if len(path) < 2:
            # 无效路径，跳过
            continue

        total_entropy = 0
        num_links = len(path) - 1  # 计算链路数量

        for i in range(num_links):
            link = (path[i], path[i + 1])
            # 获取链路上的光谱使用情况，默认为全空闲
            fsu_array = spectrum_utilization.get(link, np.ones(320))
            # 计算该链路的碎片化熵
            entropy = metrics.calculate_fragmentation_entropy(fsu_array)
            total_entropy += entropy

        # 计算整条路径的平均熵（也可以用 max 熵）
        avg_entropy = total_entropy / num_links

        if avg_entropy < min_entropy:
            min_entropy = avg_entropy
            best_path = path

    return best_path


def mod_aware(G, paths, chosen_path):
    """

    :param G:                Topology
    :param paths:            the K shortest path
    :param chosen_path:      chosen path
    :return:                 best_path
    """
    shortest_path = paths[0]

    link_length_km_ll = sum(
        G[chosen_path[i]][chosen_path[i + 1]]["weight"] for i in range(len(chosen_path) - 1))
    link_length_km_shortest = sum(
        G[shortest_path[i]][shortest_path[i + 1]]["weight"] for i in range(len(shortest_path) - 1))

    capacity_highest_loaded = modulation.get_max_capacity(link_length_km_ll)
    capacity_shortest = modulation.get_max_capacity(link_length_km_shortest)

    if capacity_highest_loaded >= capacity_shortest:
        best_path = chosen_path
    else:
        best_path = shortest_path

    return best_path

# ---------------------------------------- Task 4 + Task 5 ------------------------------------------
# 1. 主路径仍然优先选择支持高阶调制（如 16QAM）的路径。
# 2. 备份路径优先选择与主路径不共享链路的路径，而不是优先考虑高阶调制。
# 3. 备份路径仍然不能太长，以避免 FSU 开销过高，但比起调制格式，可靠性更重要。

def find_backup_path(G, paths, spectrum_utilization, primary_path):
    """
    选择一条备用路径（Backup Path）：
    - 避免与主路径共享链路
    - 在候选路径中选择负载最低的

    参数：
        G: 网络拓扑图
        paths: 候选路径列表
        spectrum_utilization: 链路的光谱利用信息
        primary_path: 选择的主路径

    返回：
        备份路径（如果找到），否则 None
    """
    path_loads = []

    for path in paths:
        if len(path) < 2 or path == primary_path:
            continue  # 跳过无效路径或与主路径相同的路径

        # 计算路径负载
        total_used_slots = 0
        num_links = len(path) - 1  # 计算链路数

        for i in range(num_links):
            link = (path[i], path[i + 1])
            fsu_array = spectrum_utilization.get(link, np.ones(320))  # 获取光谱占用情况
            used_on_link = 320 - np.sum(fsu_array)  # 计算已占用的频谱槽
            total_used_slots += used_on_link

        avg_load = total_used_slots / num_links  # 计算路径的平均负载

        # 计算该路径与主路径的共享链路数
        shared_links = count_shared_links(primary_path, path)

        # 仅考虑共享链路数较少的路径
        path_loads.append((path, avg_load, shared_links))

    # 先按共享链路数排序，再按负载排序
    path_loads.sort(key=lambda x: (x[2], x[1]))

    # 选择共享最少 & 负载最小的路径作为备份路径
    backup_path = path_loads[0][0] if path_loads else None

    return backup_path


def count_shared_links(path1, path2):
    """
    计算两条路径的共享链路数
    """
    set1 = set(zip(path1[:-1], path1[1:]))  # 主路径的链路集合
    set2 = set(zip(path2[:-1], path2[1:]))  # 备份路径的链路集合

    common_links = set1.intersection(set2)
    return len(common_links)
