import numpy as np
from scipy.stats import entropy


def highest_fsu_per_link(spectrum):
    """ 计算每条链路的最高 FSU 索引 """
    link_fsu = {}
    for link, slots in spectrum.items():
        if np.any(slots == 0):  # 只有被占用的链路才统计
            link_fsu[link] = np.max(np.where(slots == 0))
        else:
            link_fsu[link] = 0  # 如果没有占用，最高 FSU 为 0
    return link_fsu



def total_used_fsus(spectrum):
    """
    计算总共被占用的 FSU 数量
    :param spectrum: 频谱分配表 { (u, v): np.array([...]) }
    :return: 总占用的 FSU 数量
    """
    return sum(np.sum(slots == 0) for slots in spectrum.values())


def calculate_fragmentation_entropy(spectrum_usage):
    """
    Calculate a Shannon Entropy-like metric to reflect fragmentation.
    'spectrum_usage' is an array/list of 0/1, where 1 means 'free' and 0 means 'occupied'.
    This function finds all continuous free blocks and computes an entropy value.
    """
    total_slots = len(spectrum_usage)
    if total_slots == 0:
        return 0.0

    # Step 1: 找出所有连续的空闲块长度
    free_blocks = []
    current_block_length = 0

    for slot in spectrum_usage:
        if slot == 1:  # 空闲
            current_block_length += 1
        else:          # 占用
            if current_block_length > 0:
                free_blocks.append(current_block_length)
                current_block_length = 0

    # 如果最后结尾还是空闲，则需要把最后一个block收尾
    if current_block_length > 0:
        free_blocks.append(current_block_length)

    # 如果没有空闲块或整条都空闲, 熵都可以视为 0
    if len(free_blocks) <= 1:
        # 0个空闲块 => 全部被占用 => 无碎片
        # 1个空闲块 => 全部空闲 => 同样碎片度很低(或者说是一个块)
        return 0.0

    # Step 2: 计算每个空闲块的比例 p_i
    total_free = sum(free_blocks)
    # 若万一 total_free == 0 则直接返回0熵
    if total_free == 0:
        return 0.0

    # p = [block_len / total_free for block_len in free_blocks]
    p = [block_len / 320 for block_len in free_blocks]

    # Step 3: 根据每个 p_i 计算香农熵
    entropy = 0.0
    for pi in p:
        # p_i log2 p_i
        entropy -= pi * np.log2(pi)

    return entropy

# def utilization_entropy(spectrum):
#     """
#     计算利用率熵
#     :param spectrum: 频谱分配表 { (u, v): np.array([...]) }
#     :return: 利用率熵
#     """
#     total_fsus = np.zeros(320)  # 统计每个 FSU 在多少条链路上被占用
#     for slots in spectrum.values():
#         total_fsus += (slots == 0)  # 计算每个 FSU 在多少条链路上被占用
#
#     q = total_fsus / np.sum(total_fsus)  # 计算每个 FSU 的占用概率
#     q = q[q > 0]  # 去除 p=0 的项，避免 log(0)
#     return -np.sum(q * np.log2(q))

def utilization_entropy(spectrum):
    """
    计算利用率熵 (Utilization Entropy)
    公式: UE = Xs / (Ls-1)，其中 Xs 是相邻频谱槽状态变化的总次数

    参数:
        spectrum: 字典 {(u, v): np.array}, 表示每条链路的频谱状态
                 其中0表示空闲，1表示占用

    返回:
        字典 {(u, v): ue值}，每条链路的利用率熵
    """
    result = {}

    for link, slots in spectrum.items():
        # 频谱槽的总数
        Ls = len(slots)

        if Ls <= 1:
            result[link] = 0
            continue

        # 计算状态变化次数 Xs
        Xs = 0
        for i in range(Ls - 1):
            # 异或操作: 相同为0，不同为1
            if slots[i] != slots[i + 1]:
                Xs += 1

        # 计算链路的利用率熵
        UE = Xs / (Ls - 1)
        result[link] = UE

    return result


def calculate_network_utilization_entropy(spectrum):
    """
    计算整个网络的平均利用率熵

    参数:
        spectrum: 字典 {(u, v): np.array}, 表示每条链路的频谱状态

    返回:
        网络平均利用率熵
    """
    link_ue = utilization_entropy(spectrum)
    # print(link_ue)
    if not link_ue:
        return 0
    return sum(link_ue.values()) / len(link_ue)


# ================== 测试示例 ==================
if __name__ == "__main__":
    # 比如下面这段：1 1 1 0 0 1 0 1
    # free_blocks = [3, 1, 1] -> p = [3/5, 1/5, 1/5]
    # 这样可得到相应的熵
    test_spectrum1 = np.array([1,1,1,0,0,1,0,1])
    print("Entropy:", calculate_fragmentation_entropy(test_spectrum1))

    # 全部占用 => 碎片为 0
    test_spectrum2 = np.array([0,0,0,0,0])
    print("Entropy:", calculate_fragmentation_entropy(test_spectrum2))

    # 全部空闲 => 也只有一个大块 => 碎片为 0
    test_spectrum3 = np.array([1,1,1,1,1])
    print("Entropy:", calculate_fragmentation_entropy(test_spectrum3))

    # 多块分散空闲 => 熵会更高
    test_spectrum4 = np.array([1,0,1,0,1,0,1,0])
    print("Entropy:", calculate_fragmentation_entropy(test_spectrum4))
