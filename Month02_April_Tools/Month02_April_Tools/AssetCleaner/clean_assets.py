# -*- coding: utf-8 -*-
"""
Maya 资产清理工具 (Asset Cleaner)
版本: 2.0 Final (工业级面试版)
作者: [小宇]
描述:
    专为技术美术(TA)打造的资产标准化清理工具。
    与 asset_perf_check.py 配合使用，形成“检查-修复”闭环。
    核心目标：批量执行安全、无争议、可批量的资产标准化操作。

特点:
    1. 职责明确：只做清理，不做检查。与 asset_perf_check.py 配合使用。
    2. 顺序严谨：冻结变换 → 删除历史 → 重置轴心 → 锁定属性。
    3. 工业级健壮性：每个物体的每步操作独立 try-except，单个报错不影响整体。
    4. 操作反馈：在 Maya 视口和脚本编辑器中同步输出清理统计。

使用场景:
    - 在 Maya 中选中需要清理的模型，直接运行此脚本。
    - 与 asset_perf_check.py 配合：先检查发现问题，再手动选中问题资产运行本脚本修复。

清理顺序说明（不可更改）:
    1. 冻结变换：将位移/旋转/缩放值归零/归一，防止导入引擎后位置错位。
    2. 删除历史：清除所有构造历史节点，包括冻结变换产生的新节点。
    3. 重置轴心：将轴心点移至模型底部中心，便于引擎中放置和对齐。
    4. 锁定属性：锁定变换属性，防止修复后被美术误操作。

与 asset_perf_check.py 的对应关系:
    - asset_perf_check.py 检查到“变换未冻结” → 本工具的 freeze_transform() 修复。
    - asset_perf_check.py 无法自动修复 UV、非流形、面数问题 → 由报告引导美术手动处理。
    - 本工具额外执行删除历史和锁定属性，作为资产标准化的补充操作。
"""

import maya.cmds as cmds


# =============================================================================
# 1. 配置中心 (所有可调整参数在此管理)
# =============================================================================
CONFIG = {
    # 冻结变换选项
    "FREEZE_TRANSLATE": True,   # 是否冻结位移
    "FREEZE_ROTATE": True,      # 是否冻结旋转
    "FREEZE_SCALE": True,       # 是否冻结缩放

    # 轴心点位置：True = 模型底部中心, False = 世界原点
    "PIVOT_TO_BOTTOM": True,

    # 锁定变换属性：True = 清理后锁定，防止误操作
    "LOCK_ATTRIBUTES": True
}


# =============================================================================
# 2. 核心清理函数（每个函数对应一个清理步骤）
# =============================================================================

def freeze_transform(transform_node):
    """
    冻结物体的变换，使位移和旋转归零、缩放归一。
    【对应检查项】asset_perf_check.py 的 check_transform_frozen()。
    【性能影响】未冻结的变换会导致引擎每帧进行额外的矩阵计算，影响合批效率。
    【为什么可以自动修复】冻结变换是标准化操作，安全、可逆（撤销）。

    Args:
        transform_node: 需要冻结变换的物体节点。

    Returns:
        bool: 成功返回 True，失败返回 False。
    """
    try:
        cmds.makeIdentity(
            transform_node,
            apply=True,
            translate=CONFIG["FREEZE_TRANSLATE"],
            rotate=CONFIG["FREEZE_ROTATE"],
            scale=CONFIG["FREEZE_SCALE"],
            normal=0
        )
        return True
    except Exception as error:
        print(f"  ❌ 冻结变换失败 ({transform_node}): {error}")
        return False


def delete_history(transform_node):
    """
    删除物体的构造历史。
    【性能影响】构造历史会增加场景文件大小，并可能导致导出 FBX 时出现意外错误。
    【为什么可以自动修复】删除历史是标准化操作，安全、可逆（撤销）。

    Args:
        transform_node: 需要删除历史的物体节点。

    Returns:
        bool: 成功返回 True，失败返回 False。
    """
    try:
        cmds.delete(transform_node, constructionHistory=True)
        return True
    except Exception as error:
        print(f"  ❌ 删除历史失败 ({transform_node}): {error}")
        return False


def center_pivot(transform_node):
    """
    将物体轴心点移至模型底部中心。
    【性能影响】合理的轴心点位置便于引擎中的放置、对齐和 LOD 切换。
    【为什么可以自动修复】归轴心是标准化操作，安全、可逆（撤销）。

    Args:
        transform_node: 需要调整轴心点的物体节点。

    Returns:
        bool: 成功返回 True，失败返回 False。
    """
    try:
        bounding_box = cmds.exactWorldBoundingBox(transform_node)

        # 分步计算底部中心坐标
        bottom_center_x = (bounding_box[0] + bounding_box[3]) / 2
        bottom_center_y = bounding_box[1]
        bottom_center_z = (bounding_box[2] + bounding_box[5]) / 2

        cmds.xform(
            transform_node,
            pivots=[bottom_center_x, bottom_center_y, bottom_center_z],
            worldSpace=True
        )
        return True
    except Exception as error:
        print(f"  ❌ 归轴心点失败 ({transform_node}): {error}")
        return False


def lock_transform_attributes(transform_node):
    """
    锁定变换属性，防止修复后被误操作。
    这是很多大厂规范的延伸，体现对管线规范的深入理解。

    Args:
        transform_node: 需要锁定属性的物体节点。

    Returns:
        bool: 成功返回 True，失败返回 False。
    """
    try:
        # 锁定位移和缩放属性
        lock_attributes = [
            "translateX", "translateY", "translateZ",
            "scaleX", "scaleY", "scaleZ"
        ]
        for attr in lock_attributes:
            cmds.setAttr(f"{transform_node}.{attr}", lock=True)
        return True
    except Exception as error:
        print(f"  ❌ 锁定属性失败 ({transform_node}): {error}")
        return False


# =============================================================================
# 3. 主清理流程
# =============================================================================

def clean_selected_assets():
    """
    对当前选中的所有物体执行标准化清理。

    清理顺序（不可更改）:
        1. 冻结变换 → 将变换值归零/归一。
        2. 删除历史 → 清除冻结变换产生的新历史节点。
        3. 归轴心点 → 将轴心移至模型底部中心。
        4. 锁定属性 → 防止误操作。

    每个物体独立处理，单个报错不中断整体流程。
    """
    # 获取选中的变换节点
    selection = cmds.ls(selection=True, type="transform") or []

    if not selection:
        cmds.warning("⚠️ 未选中任何物体。请先选择需要清理的模型。")
        cmds.inViewMessage(
            message="⚠️ 未选中任何物体，请先选择需要清理的模型。",
            fontSize=12,
            fade=True
        )
        return

    # 初始化统计变量
    total_count = len(selection)
    freeze_success = 0
    history_success = 0
    pivot_success = 0
    lock_success = 0
    failed_list = []

    print(f"\n🛠️ 开始清理 {total_count} 个资产...\n")

    # 遍历处理每个物体
    for asset in selection:
        print(f"处理: {asset}")
        asset_failed = False

        # 第一步：冻结变换
        if freeze_transform(asset):
            freeze_success += 1
        else:
            failed_list.append(f"{asset} (冻结变换)")
            asset_failed = True

        # 第二步：删除历史
        if delete_history(asset):
            history_success += 1
        else:
            failed_list.append(f"{asset} (删除历史)")
            asset_failed = True

        # 第三步：归轴心点
        if CONFIG["PIVOT_TO_BOTTOM"]:
            if center_pivot(asset):
                pivot_success += 1
            else:
                failed_list.append(f"{asset} (归轴心)")
                asset_failed = True

        # 第四步：锁定变换属性
        if CONFIG["LOCK_ATTRIBUTES"]:
            if lock_transform_attributes(asset):
                lock_success += 1
            else:
                failed_list.append(f"{asset} (锁定属性)")
                asset_failed = True

        if not asset_failed:
            print(f"  ✅ 完成")

    # 构建并输出清理结果摘要
    print(f"\n{'='*50}")
    print(f"📋 清理结果摘要:")
    print(f"  总计: {total_count} 个资产")
    print(f"  冻结变换: {freeze_success}/{total_count}")
    print(f"  删除历史: {history_success}/{total_count}")

    if CONFIG["PIVOT_TO_BOTTOM"]:
        print(f"  归轴心点: {pivot_success}/{total_count}")

    if CONFIG["LOCK_ATTRIBUTES"]:
        print(f"  锁定属性: {lock_success}/{total_count}")

    if failed_list:
        print(f"  ❌ 失败: {len(failed_list)} 项")
        for fail_item in failed_list:
            print(f"      - {fail_item}")

    # 在 Maya 视口显示简要结果
    summary = (
        f"✅ 清理完成 | "
        f"总计: {total_count} | "
        f"冻结: {freeze_success} | "
        f"删历史: {history_success}"
    )
    if failed_list:
        summary += f" | ❌ 失败: {len(failed_list)}"

    cmds.inViewMessage(message=summary, fontSize=12, fade=True)


# =============================================================================
# 4. 脚本入口
# =============================================================================
if __name__ == "__main__":
    print("=" * 50)
    print("🛠️ Asset Cleaner v2.0 Final 启动...")
    print("=" * 50)
    clean_selected_assets()
    print("=" * 50)
    print("✅ Asset Cleaner 执行完毕。")