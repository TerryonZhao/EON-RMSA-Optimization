import networkx as nx
import numpy as np

def load_topology(file_path):
    """ 读取网络拓扑，仅提取 NodeA, NodeB, Length 作为边的权重 """
    G = nx.Graph()
    with open(file_path, 'r') as f:
        for line in f:
            if line.startswith("#"):  # 跳过表头
                continue
            parts = line.strip().split()  # 按空格拆分
            if len(parts) < 6:
                continue  # 确保至少有 6 列数据
            node_a, node_b, length = parts[-3:]  # 取后三列
            G.add_edge(int(node_a), int(node_b), weight=float(length))  # 加入图
    return G

def load_traffic(file_path):
    matrix = np.loadtxt(file_path, dtype=int)  # 读取矩阵
    traffic_list = []

    num_nodes = matrix.shape[0]  # 确定节点数

    for i in range(num_nodes):
        for j in range(num_nodes):
            if i != j and matrix[i][j] > 0:  # 过滤对角线和 0 需求
                traffic_list.append((int(i)+1, int(j)+1, 10*int(matrix[i][j]))) # 单位 10 Gbps

    # return sorted(traffic_list, key=lambda x: x[2])  # 从小到大
    return sorted(traffic_list, key=lambda x: x[2], reverse=True) # 从大到小


if __name__ == "__main__":
    G = load_topology("/Users/macbook/Documents/Pycharm/EEN115/Proj/Germany-7nodes/G7-topology.txt")
    traffic_matrix = load_traffic("/Users/macbook/Documents/Pycharm/EEN115/Proj/Germany-7nodes/G7-matrix-1.txt")

    print("网络拓扑节点:", G.nodes)
    print("网络拓扑边:", G.edges)
    print("流量需求:", traffic_matrix)

