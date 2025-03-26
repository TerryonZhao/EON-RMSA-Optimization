import matplotlib.pyplot as plt

def plot_highest_fsu_distribution(link_fsu):
    """
    绘制最高 FSU 索引的分布直方图
    :param link_fsu: 每条链路的最高 FSU 字典 { (u,v): highest_used_fsu }
    """
    fsu_values = list(link_fsu.values())

    plt.figure(figsize=(8, 5))
    plt.hist(fsu_values, bins=20, edgecolor="black", alpha=0.7)
    plt.xlabel("Highest Used FSU Index")
    plt.ylabel("Number of Links")
    plt.title("Highest FSU Distribution Across Links")
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    plt.show()
