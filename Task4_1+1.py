import network
import routing
import spectrum_assignment
import modulation
import numpy as np
import metrics
import visualization

def run_rmsa(topology_file, traffic_file):
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

        # ---------------------------------- 选择 routing 策略 -------------------------------------------
        # 选择负载最低的路径 (K shortest + least loaded)
        primary_path = routing.least_loaded_path_routing_avg(G, paths, spectrum)

        # # 计算最短路径 (fixed shortest)
        # primary_path = routing.fixed_shortest_path_routing(G, src, dst)
        # -----------------------------------------------------------------------------------------------

        # 结合调制方式考虑
        primary_path = routing.mod_aware(G, paths, primary_path)

        # 选择backup路径
        backup_path = routing.find_backup_path(G, paths, spectrum, primary_path)

        # 计算path的长度
        primary_path_length = sum(G[primary_path[i]][primary_path[i + 1]]["weight"] for i in range(len(primary_path) - 1))
        backup_path_length = sum(G[backup_path[i]][backup_path[i + 1]]["weight"] for i in range(len(backup_path) - 1))

        # 拆分primary path 流量
        primary_sub_requests = spectrum_assignment.split_traffic(demand, primary_path_length)

        # 拆分backup path流量
        backup_sub_requests = spectrum_assignment.split_traffic(demand, backup_path_length)

        # 存储该流量的所有 lightpaths
        fsu_starts = []

        # ---------------------------------- 先给 primary path 分配频谱 ----------------------------------
        for sub_demand in primary_sub_requests:
            # 计算所需 FSU 数量 & 选择调制格式
            num_fsus, modulation_used = modulation.compute_required_fsus(sub_demand, backup_path_length)

            # 进行频谱分配
            fsu_start = spectrum_assignment.best_fit_spectrum_assignment(G, primary_path, sub_demand, spectrum)

            if fsu_start == -1:
                print(f"🚨 流量 {src}->{dst} (拆分后: {sub_demand} Gbps) 失败！无法分配频谱！")
            else:
                fsu_starts.append(fsu_start)
                print(
                    f"✅ 流量 {src}->{dst} (拆分后: {sub_demand} Gbps) 成功！主路径：{primary_path}, 调制方式: {modulation_used}, 需要 {num_fsus} FSU, 频谱起始位置: {fsu_start}")

        # ---------------------------------- 再给 backup path 分配频谱 ----------------------------------
        for sub_demand in backup_sub_requests:
            # 计算所需 FSU 数量 & 选择调制格式
            num_fsus, modulation_used = modulation.compute_required_fsus(sub_demand, backup_path_length)

            # 进行频谱分配
            fsu_start = spectrum_assignment.best_fit_spectrum_assignment(G, backup_path, sub_demand, spectrum)

            if fsu_start == -1:
                print(f"🚨 流量 {src}->{dst} (拆分后: {sub_demand} Gbps) 失败！无法分配频谱！")
            else:
                fsu_starts.append(fsu_start)
                print(
                    f"✅ 流量 {src}->{dst} (拆分后: {sub_demand} Gbps) 成功！[1+1]备用路径：{backup_path}, 调制方式: {modulation_used}, 需要 {num_fsus} FSU, 频谱起始位置: {fsu_start}")

        # **如果所有子流量都成功分配，则存储结果**
        if fsu_starts:
            results.append((src, dst, demand, backup_path , modulation_used, fsu_starts))

    return results, spectrum

if __name__ == "__main__":
    # **修改文件路径为你的拓扑和流量矩阵**
    topology_file = "/Users/macbook/Documents/Pycharm/EEN115/Proj/Germany-7nodes/G7-topology.txt"
    traffic_file = "/Users/macbook/Documents/Pycharm/EEN115/Proj/Germany-7nodes/G7-matrix-5.txt"

    print("🚀 运行 RMSA 仿真...")
    results, spectrum = run_rmsa(topology_file, traffic_file)

    # 📌 计算每条链路的最高 FSU
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

    print("\n📊 Task4 仿真完成！")
    print(f"✅ 总使用的 FSU 数量: {total_fsus}")
    print(f"✅ Shannon 熵: {max_entropy:.4f}")
    print(f"✅ 利用率熵: {utilization_H:.4f}")
