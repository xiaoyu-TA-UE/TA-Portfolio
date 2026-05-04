# -*- coding: utf-8 -*-
"""
linear_algebra.py - 3D 线性代数核心库
版本：2.0 (工业级整合版)
作者：[小宇]
描述：提供完整的 3D 向量与矩阵运算，涵盖图形学基础、坐标空间变换及 TA 业务逻辑。
特点：零依赖、类型提示、防御性编程、自带单元测试。
"""

import math
from typing import List, Tuple, Union

# =============================================================================
# 1. 类型定义 (Type Definitions)
# =============================================================================
Vector3 = Tuple[float, float, float]
Matrix4x4 = List[List[float]]

# 常量定义
MATRIX_SIZE = 4
TOLERANCE = 1e-8  # 浮点数比较容差
EPSILON = 1e-8    # 归一化防错阈值

# =============================================================================
# 2. 向量运算模块 (Vector Mathematics)
# =============================================================================

def vec_add(a: Vector3, b: Vector3) -> Vector3:
    """向量加法"""
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def vec_sub(a: Vector3, b: Vector3) -> Vector3:
    """向量减法 (a 指向 b 的向量)"""
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec_mul(scalar: float, vec: Vector3) -> Vector3:
    """向量数乘"""
    return (scalar * vec[0], scalar * vec[1], scalar * vec[2])

def vec_length(vec: Vector3) -> float:
    """计算向量模长 (欧几里得范数)"""
    return math.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])

def normalize(vec: Vector3) -> Vector3:
    """
    向量归一化
    返回单位向量。若输入为零向量，返回零向量并打印警告。
    """
    length = vec_length(vec)
    if length < EPSILON:
        print("警告: 尝试归一化零向量")
        return (0.0, 0.0, 0.0)
    return (vec[0] / length, vec[1] / length, vec[2] / length)

def dot_product(a: Vector3, b: Vector3) -> float:
    """向量点积"""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

def cross_product(a: Vector3, b: Vector3) -> Vector3:
    """向量叉积"""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    )

def angle_between(a: Vector3, b: Vector3) -> float:
    """
    计算两个向量之间的夹角 (度数)
    包含对零向量的防御性检查。
    """
    len_a = vec_length(a)
    len_b = vec_length(b)
    if len_a < EPSILON or len_b < EPSILON:
        raise ValueError("无法计算零向量的夹角")
    
    cos_theta = dot_product(a, b) / (len_a * len_b)
    # 修正浮点误差，防止 acos 输入超出 [-1, 1]
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return math.degrees(math.acos(cos_theta))

# TA 业务逻辑函数
def is_in_front(player_pos: Vector3, player_forward: Vector3, target_pos: Vector3) -> bool:
    """
    TA业务逻辑：判断目标是否在玩家前方
    利用点积判断方向。
    """
    to_target = vec_sub(target_pos, player_pos)
    # 点积 > 0 代表夹角小于90度，即在前方
    return dot_product(player_forward, to_target) > 0

# =============================================================================
# 3. 矩阵运算模块 (Matrix Mathematics)
# =============================================================================

def identity_matrix() -> Matrix4x4:
    """创建 4x4 单位矩阵"""
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ]

def translation_matrix(tx: float, ty: float, tz: float) -> Matrix4x4:
    """创建 4x4 平移矩阵"""
    mat = identity_matrix()
    mat[0][3] = tx
    mat[1][3] = ty
    mat[2][3] = tz
    return mat

def scale_matrix(sx: float, sy: float, sz: float) -> Matrix4x4:
    """创建 4x4 缩放矩阵"""
    mat = identity_matrix()
    mat[0][0] = sx
    mat[1][1] = sy
    mat[2][2] = sz
    return mat

def rotation_y_matrix(angle_deg: float) -> Matrix4x4:
    """创建绕 Y 轴旋转的 4x4 矩阵"""
    theta = math.radians(angle_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return [
        [c,  0,  s, 0],
        [0,  1,  0, 0],
        [-s, 0,  c, 0],
        [0,  0,  0, 1]
    ]

def multiply_matrices(a: Matrix4x4, b: Matrix4x4) -> Matrix4x4:
    """
    两个 4x4 矩阵相乘
    逻辑：result[i][j] = sum(a[i][k] * b[k][j])
    """
    result = [[0.0 for _ in range(MATRIX_SIZE)] for _ in range(MATRIX_SIZE)]
    for i in range(MATRIX_SIZE):
        for j in range(MATRIX_SIZE):
            for k in range(MATRIX_SIZE):
                result[i][j] += a[i][k] * b[k][j]
    return result

def transform_point(point: Vector3, matrix: Matrix4x4) -> Vector3:
    """
    使用 4x4 矩阵变换一个 3D 点 (模型空间 -> 世界空间)
    原理：齐次坐标乘法 [x, y, z, 1] * Matrix
    """
    x, y, z = point
    # 齐次坐标计算 (w 默认为 1)
    new_x = matrix[0][0]*x + matrix[0][1]*y + matrix[0][2]*z + matrix[0][3]
    new_y = matrix[1][0]*x + matrix[1][1]*y + matrix[1][2]*z + matrix[1][3]
    new_z = matrix[2][0]*x + matrix[2][1]*y + matrix[2][2]*z + matrix[2][3]
    # 保留 4 位小数防止浮点误差显示过长
    return (round(new_x, 4), round(new_y, 4), round(new_z, 4))

# =============================================================================
# 4. 自带测试模块 (Self-Test)
# =============================================================================
def run_tests():
    """运行所有单元测试，验证库的正确性"""
    print("🚀 Linear Algebra Library - Running Self-Tests\n")
    
    # --- 向量测试 ---
    print("🧪 测试 1: 向量运算")
    v1 = (1, 0, 0)
    v2 = (0, 1, 0)
    print(f"  点积 (90°): {dot_product(v1, v2)} (应为 0)")
    print(f"  夹角: {angle_between(v1, v2)}° (应为 90°)")
    
    # --- 矩阵测试 ---
    print("\n🧪 测试 2: 矩阵变换")
    local_point = (1.0, 0.0, 0.0)
    # 构建一个向右移动 5 单位的矩阵
    transform_mat = translation_matrix(5, 0, 0)
    world_point = transform_point(local_point, transform_mat)
    print(f"  局部点 {local_point} 经平移矩阵变换后: {world_point} (应为 (6.0, 0.0, 0.0))")
    
    # --- 业务逻辑测试 ---
    print("\n🧪 测试 3: TA 业务逻辑")
    player_pos = (0, 0, 0)
    player_dir = (1, 0, 0) # 朝向 X 轴正方向
    target_front = (10, 0, 0)
    target_back = (-10, 0, 0)
    print(f"  目标 {target_front} 在玩家前方: {is_in_front(player_pos, player_dir, target_front)} (应为 True)")
    print(f"  目标 {target_back} 在玩家前方: {is_in_front(player_pos, player_dir, target_back)} (应为 False)")

if __name__ == "__main__":
    run_tests()