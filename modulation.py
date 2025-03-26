import numpy as np

# 定义不同调制格式的参数
MODULATION_FORMATS = [
    {"name": "SC-DP-QPSK", "rate": 100, "bandwidth": 37.5, "max_length": 2000, "cost": 1.5},
    {"name": "SC-DP-16QAM", "rate": 200, "bandwidth": 37.5, "max_length": 700, "cost": 2},
    {"name": "DP-16QAM", "rate": 400, "bandwidth": 75, "max_length": 500, "cost": 3.7}
]

def select_modulation(link_length_km):
    """
    选择适合的调制格式
    :param link_length_km: 链路长度（km）
    :return: 选中的调制格式信息（字典）
    """

    if link_length_km <= 500:
        return MODULATION_FORMATS[2]
    elif link_length_km <= 700:
        return MODULATION_FORMATS[1]
    else:
        return MODULATION_FORMATS[0]

    # for modulation in MODULATION_FORMATS:
    #     if link_length_km <= modulation["max_length"]:
    #         return modulation
    # return MODULATION_FORMATS[0]  # 默认使用 SC-DP-QPSK


def get_max_capacity(link_length_km):
    """
    获取该链路允许的最大 Line Rate (Gbps)
    :param link_length_km: 该流量所经过的最长链路长度 (km)
    :return: 该链路允许的最大光通道容量 (Gbps)
    """
    modulation = select_modulation(link_length_km)  # 选择适合的调制格式
    return modulation["rate"]  # 该调制格式的最大 Line Rate


# efficiency = line rate(Gbps) / bandwidth(GHz)
# required bandwidth(GHz) = demand / efficiency
# FSU_num = required_bandwidth / 12.5
def compute_required_fsus(demand_gbps, link_length_km):
    """
    计算所需 FSU 数量
    :param demand_gbps: 需求流量大小 (Gbps)
    :param link_length_km: 链路长度 (km)
    :return: (所需 FSU 数量, 选定的调制格式名称)
    """
    modulation = select_modulation(link_length_km)  # 选择调制格式
    spectral_efficiency = modulation["rate"] / modulation["bandwidth"]  # Gbps/GHz
    required_bandwidth_ghz = demand_gbps / spectral_efficiency  # 计算所需 GHz
    required_fsus = int(np.ceil(required_bandwidth_ghz / 12.5))  # 计算所需 FSU
    return required_fsus, modulation["name"]
