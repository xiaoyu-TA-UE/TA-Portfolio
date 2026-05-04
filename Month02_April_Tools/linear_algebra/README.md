# 3D 线性代数核心库 (linear_algebra.py)

**版本**: 2.0 | **作者**: [小宇] | **日期**: 2026年4月

## 📖 简介

零依赖、带类型提示和单元测试的 3D 数学库。涵盖向量运算、矩阵变换及 TA 业务逻辑。

**特点**：零依赖、类型提示、防御性编程、自带单元测试。

## 🧩 功能模块

### 向量运算

| 函数                              | 说明                               |
| :-------------------------------- | :--------------------------------- |
| `vec_add` / `vec_sub` / `vec_mul` | 向量加法、减法、数乘               |
| `vec_length`                      | 计算模长（欧几里得范数）           |
| `normalize`                       | 归一化（含零向量防御检查）         |
| `dot_product`                     | 点积（判断方向，比反余弦快数百倍） |
| `cross_product`                   | 叉积（求法线方向）                 |
| `angle_between`                   | 计算夹角（含浮点误差修正）         |
| `is_in_front`                     | TA业务逻辑：判断目标是否在玩家前方 |

### 矩阵运算

| 函数                 | 说明                         |
| :------------------- | :--------------------------- |
| `identity_matrix`    | 创建单位矩阵                 |
| `translation_matrix` | 创建平移矩阵                 |
| `scale_matrix`       | 创建缩放矩阵                 |
| `rotation_y_matrix`  | 创建绕Y轴旋转矩阵            |
| `multiply_matrices`  | 矩阵乘法（三重循环实现）     |
| `transform_point`    | 将点从模型空间变换到世界空间 |

## 🚀 使用方法

### 在 Python 环境中

```python
import linear_algebra as la

# 计算两个向量的点积
a = (1, 0, 0)
b = (0, 1, 0)
print(la.dot_product(a, b))  # 0（垂直）

# 判断目标是否在玩家前方
player_pos = (0, 0, 0)
player_dir = (1, 0, 0)
target = (10, 0, 0)
print(la.is_in_front(player_pos, player_dir, target))  # True
```

### 运行自测

```bash
python linear_algebra.py
```

## 📂 文件结构

```
linear_algebra.py
├── Vector3 / Matrix4x4  # 类型别名，提高可读性
├── 向量运算模块          # vec_add, dot_product, cross_product 等
├── 矩阵运算模块          # identity_matrix, multiply_matrices 等
├── TA业务逻辑函数        # is_in_front
├── run_tests()           # 自带单元测试
└── __name__ == "__main__"
```

## 📜 代码规范遵循

严格遵循《代码风格生成规范》：

- 向量运算参数使用全称 `vector_a` / `vector_b`
- 矩阵函数参数使用全称 `translate_x` / `scale_y`
- 零依赖（仅使用 Python 标准库 `math`）
- 类型提示提高可读性

## 👤 作者

[小宇] - 技术美术(TA)学习者，性能优化与工具流程方向。
