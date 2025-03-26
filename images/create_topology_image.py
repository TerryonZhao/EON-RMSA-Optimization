import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

def create_germany_topology():
    # 创建一个无向图
    G = nx.Graph()
    
    # 添加节点（德国7节点网络）
    nodes = {
        0: {"name": "Hamburg", "pos": (3, 6)},
        1: {"name": "Berlin", "pos": (5, 5)},
        2: {"name": "Hannover", "pos": (2, 4)},
        3: {"name": "Leipzig", "pos": (4, 3)},
        4: {"name": "Frankfurt", "pos": (2, 2)},
        5: {"name": "Nurnberg", "pos": (4, 1)},
        6: {"name": "Munchen", "pos": (3, 0)}
    }
    
    # 添加节点及其位置
    for node_id, data in nodes.items():
        G.add_node(node_id, pos=data["pos"], name=data["name"])
    
    # 添加边（链路）
    edges = [
        (0, 1, 300), (0, 2, 150), (1, 3, 200),
        (2, 3, 150), (2, 4, 200), (3, 5, 150),
        (4, 5, 200), (4, 6, 200), (5, 6, 150)
    ]
    
    for u, v, weight in edges:
        G.add_edge(u, v, weight=weight)
    
    # 获取节点位置
    pos = nx.get_node_attributes(G, 'pos')
    
    # 绘制图形
    plt.figure(figsize=(10, 8))
    
    # 绘制边，颜色为灰色，线宽与权重成比例
    edge_widths = [0.5 + w/200 for (u, v, w) in G.edges(data='weight')]
    nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color='gray', alpha=0.7)
    
    # 绘制节点，使用浅蓝色
    nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='skyblue', edgecolors='black')
    
    # 添加节点标签（城市名称）
    labels = nx.get_node_attributes(G, 'name')
    nx.draw_networkx_labels(G, pos, labels, font_size=11, font_weight='bold')
    
    # 添加边标签（链路长度）
    edge_labels = nx.get_edge_attributes(G, 'weight')
    edge_labels = {(u, v): f'{w} km' for (u, v), w in edge_labels.items()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=9)
    
    # 设置标题和去除坐标轴
    plt.title("德国7节点网络拓扑 / German 7-node Network Topology", fontsize=16)
    plt.axis('off')
    
    # 保存图片
    plt.savefig('germany_topology.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_simulation_results():
    # 创建模拟的结果数据
    algorithms = ["First-Fit", "Best-Fit", "Most-Used", "Shared Protection"]
    metrics = ["总FSU使用量", "最大熵", "阻塞率"]
    
    # 随机生成一些数据
    np.random.seed(42)
    data = np.random.rand(len(algorithms), len(metrics))
    data[:, 0] = data[:, 0] * 250 + 100  # 总FSU使用量 (100-350)
    data[:, 1] = data[:, 1] * 0.5  # 最大熵 (0-0.5)
    data[:, 2] = data[:, 2] * 0.1  # 阻塞率 (0-0.1)
    
    # 设置绘图样式
    width = 0.2
    x = np.arange(len(metrics))
    
    # 创建子图
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 为每个算法创建柱状图
    for i, alg in enumerate(algorithms):
        offset = (i - len(algorithms)/2 + 0.5) * width
        rects = ax.bar(x + offset, data[i], width, label=alg)
        
        # 在柱子上方添加数字
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3点偏移
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)
    
    # 添加标签和图例
    ax.set_xlabel('性能指标 / Performance Metrics', fontsize=14)
    ax.set_ylabel('数值 / Value', fontsize=14)
    ax.set_title('不同算法的性能比较 / Performance Comparison of Different Algorithms', fontsize=16)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.legend(loc='upper right', fontsize=12)
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig('simulation_results.png', dpi=300, bbox_inches='tight')
    plt.close()

def create_spectrum_visualization():
    # 创建模拟的频谱数据
    num_links = 5
    fsu_slots = 40  # 简化为40个FSU以便可视化
    
    # 生成一些随机的频谱占用数据 (1=空闲, 0=占用)
    np.random.seed(123)
    spectrum_data = np.ones((num_links, fsu_slots))
    
    # 模拟一些连续的频谱占用
    for link in range(num_links):
        # 为每条链路创建2-4个连续占用块
        num_blocks = np.random.randint(2, 5)
        for _ in range(num_blocks):
            start = np.random.randint(0, fsu_slots - 6)
            length = np.random.randint(2, 6)
            spectrum_data[link, start:start+length] = 0
    
    # 创建绘图
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 创建热图
    cmap = plt.cm.Blues
    cmap.set_bad('white')
    cmap.set_over('white')
    cmap.set_under('white')
    
    im = ax.imshow(spectrum_data, aspect='auto', cmap=cmap, vmin=0, vmax=1)
    
    # 添加标签和标题
    link_labels = [f"Link {i+1}" for i in range(num_links)]
    ax.set_yticks(np.arange(num_links))
    ax.set_yticklabels(link_labels)
    
    ax.set_xlabel('频谱槽 / Frequency Slot Units (FSU)', fontsize=14)
    ax.set_ylabel('网络链路 / Network Links', fontsize=14)
    ax.set_title('频谱分配可视化 / Spectrum Assignment Visualization', fontsize=16)
    
    # 添加颜色条
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.set_ticks([0, 1])
    cbar.set_ticklabels(['占用 / Used', '空闲 / Available'])
    
    # 保存图片
    plt.tight_layout()
    plt.savefig('spectrum_visualization.png', dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    create_germany_topology()
    create_simulation_results()
    create_spectrum_visualization()
    print("所有图像已成功创建！ / All images created successfully!") 