import network
import routing
import spectrum_assignment
import modulation
import numpy as np
import metrics
import visualization

def run_rmsa(topology_file, traffic_file):
    """
    运行完整的 RMSA 测试，包括:
    1. 解析网络拓扑
    2. 解析流量需求
    3. 计算 K shortest 路径
    4. 基于不同策略选择路径：
        a. 选择 Max Entropy 最小的路径
        b. 选择 Avg Entropy 最小的路径
        c. 选择负载最高的路径
        d. 选择负载最低的路径
    5. 计算所需 FSU
    6. 进行频谱分配（支持流量拆分）
        a. first fit
        b. best fit
    """

    # 1️⃣ **解析拓扑**
    G = network.load_topology(topology_file)

    # 2️⃣ **解析流量需求**
    traffic_matrix = network.load_traffic(traffic_file)

    # 3️⃣ **初始化 320 个 FSU 频谱**
    spectrum = {}
    for u, v in G.edges():
        spectrum[(u, v)] = np.ones(320)
        spectrum[(v, u)] = np.ones(320)  # 🚀 确保存储双向链路

    results = []

    # 4️⃣ **遍历流量需求，计算路径、拆分流量、分配频谱**
    for src, dst, demand in traffic_matrix:
        print('---------------------------------------')
        # 计算 K 条最短路径
        paths = routing.k_shortest_paths_routing(G, src, dst)

        if not paths:
            print(f"🚨 无法找到从 {src} 到 {dst} 的路径")
            continue
        # ---------------------------- 不同的选择策略 ------------------------------------
        # 选择 Max Entropy 最小的路径
        # path = routing.entropy_minimization_path_routing_max(G, paths, spectrum)

        # 选择 Avg Entropy 最小的路径
        # path = routing.entropy_minimization_path_routing_avg(G, paths, spectrum)

        # # 选择负载最高的路径
        # path = routing.highest_loaded_path_routing_avg(G, paths, spectrum)

        # # 选择负载最低的路径
        path = routing.least_loaded_path_routing_avg(G, paths, spectrum)
        # --------------------------------------------------------------------------------
        # 结合调制方式考虑
        path = routing.mod_aware(G, paths, path)

        # 计算path的长度
        path_length_km = sum(G[path[i]][path[i + 1]]["weight"] for i in range(len(path) - 1))

        # **如果流量超过单通道容量，则拆分**
        sub_requests = spectrum_assignment.split_traffic(demand, path_length_km)

        # 存储该流量的所有 lightpaths
        fsu_starts = []

        for sub_demand in sub_requests:
            # 计算所需 FSU 数量 & 选择调制格式
            num_fsus, modulation_used = modulation.compute_required_fsus(sub_demand, path_length_km)

            # ------------------------------------ 进行频谱分配 ---------------------------------------------
            fsu_start = spectrum_assignment.best_fit_spectrum_assignment(G, path, sub_demand, spectrum)

            # fsu_start = spectrum_assignment.first_fit_spectrum_assignment(G, path, sub_demand, spectrum)
            # ----------------------------------------------------------------------------------------------

            if fsu_start == -1:
                print(f"🚨 流量 {src}->{dst} (拆分后: {sub_demand} Gbps) 失败！无法分配频谱！")
            else:
                fsu_starts.append(fsu_start)
                print(f"✅ 流量 {src}->{dst} (拆分后: {sub_demand} Gbps) 成功！路径: {path}, 调制: {modulation_used}, 需要 {num_fsus} FSU, 频谱起始位置: {fsu_start}")

        # **如果所有子流量都成功分配，则存储结果**
        if fsu_starts:
            results.append((src, dst, demand, path, modulation_used, fsu_starts))

    return results, spectrum

if __name__ == "__main__":
    # **修改文件路径为你的拓扑和流量矩阵**
    topology_file = "/Users/macbook/Documents/Pycharm/EEN115/Proj/Germany-7nodes/G7-topology.txt"
    traffic_file = "/Users/macbook/Documents/Pycharm/EEN115/Proj/Germany-7nodes/G7-matrix-1.txt"

    # topology_file = "/Users/macbook/Documents/Pycharm/EEN115/Proj/Italian-10nodes/IT10-topology.txt"
    # traffic_file = "/Users/macbook/Documents/Pycharm/EEN115/Proj/Italian-10nodes/IT10-matrix-5.txt"

    print("🚀 运行 RMSA 仿真...")
    results, spectrum = run_rmsa(topology_file, traffic_file)

    # 📌 **计算每条链路的最高 FSU**
    link_fsu = metrics.highest_fsu_per_link(spectrum)

    print("\n📊 最高 FSU 索引（每条链路）:")
    for link, max_fsu in link_fsu.items():
        print(f"链路 {link}: 最高 FSU = {max_fsu}")

    # 🚀 计算关键指标
    total_fsus = metrics.total_used_fsus(spectrum)

    max_entropy = max(metrics.calculate_fragmentation_entropy(spectrum)
                      for spectrum in spectrum.values())

    #shannon_H = metrics.calculate_shannon_entropy(spectrum)
    utilization_H = metrics.calculate_network_utilization_entropy(spectrum)

    print("\n📊 仿真完成！")
    print(f"✅ 总使用的 FSU 数量: {total_fsus}")
    print(f"✅ Shannon 熵: {max_entropy:.4f}")
    print(f"✅ 利用率熵: {utilization_H:.4f}")
