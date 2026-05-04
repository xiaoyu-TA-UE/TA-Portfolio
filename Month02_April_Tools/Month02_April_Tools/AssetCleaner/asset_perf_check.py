# -*- coding: utf-8 -*-
"""
Asset Performance Checker (资产性能与规范检查工具)
版本: 9.0 Final (工业级面试版)
作者: [小宇]
描述:
    专为技术美术(TA)与美术团队协作打造的资产扫描工具。
    核心目标：在DCC环节提前发现性能问题，生成清晰易懂的报告。
    特点：
    1. 高级深色HTML报告：黑底配色，专业大气。
    2. 智能交互：未选模型时弹窗引导，支持手动选择或一键全场景扫描。
    3. 自定义保存路径：生成报告时可自由选择保存位置和文件名。
    4. 双模式运行：支持Maya内交互使用和命令行批量处理。
    5. 完整规范检查：涵盖面数、顶点、UV、拓扑、变换、空间关系。
    6. 工业级健壮性：单个资产错误不影响整体扫描。

使用方法（命令行）:
    mayapy asset_perf_check.py --check    # 检查模式
    mayapy asset_perf_check.py --clean    # 清理模式
"""

import maya.cmds as cmds
import argparse
import os
import sys
from datetime import datetime

# =============================================================================
# 1. 配置中心 (所有阈值和规则可在此调整)
# =============================================================================
CONFIG = {
    "MAX_FACE_COUNT": 10000,
    "MAX_VERTEX_COUNT": 5000,
    "CHECK_UV_RANGE": True,
    "CHECK_NON_MANIFOLD": True,
    "CHECK_SPACING": True,
    "IGNORE_LIST": ["front", "side", "top", "persp"],
    "MIN_SAFE_DISTANCE": 1.0,
    "DEFAULT_REPORT_NAME": "Asset_Performance_Report",
    "FLOAT_TOLERANCE": 0.001
}

# =============================================================================
# 2. 工具函数：获取用户想要检查的资产
# =============================================================================

def get_target_assets():
    """
    获取用户想要检查的资产列表。

    逻辑优先级：
        1. 如果用户已手动选中模型 → 直接使用选中的模型。
        2. 如果用户未选中任何模型 → 弹出对话框，让用户选择：
           a) “手动选择” → 取消，让用户自行选择。
           b) “一键全场景扫描” → 自动获取场景中所有网格物体。

    Returns:
        list: 需要检查的变换节点列表。如果用户取消操作，返回空列表。
    """
    # 获取当前选中的变换节点
    selection = cmds.ls(selection=True, type="transform") or []
    transforms = []

    # 过滤出网格物体
    for obj in selection:
        try:
            shapes = cmds.listRelatives(obj, shapes=True, path=True) or []
            for shape in shapes:
                if cmds.objectType(shape) == "mesh":
                    transforms.append(obj)
                    break
        except Exception as error:
            print(f"⚠️ 跳过无效节点 {obj}: {error}")

    # 如果用户已经选中了有效网格，直接使用
    if transforms:
        print(f"✅ 已获取用户选中的 {len(transforms)} 个资产。")
        return transforms

    # 用户未选中任何有效网格 → 弹窗引导
    print("ℹ️ 未检测到选中的模型，打开扫描模式选择...")

    choice = cmds.confirmDialog(
        title="资产扫描模式选择",
        message="未检测到选中的模型！\n\n请选择扫描模式：",
        button=["一键全场景扫描", "手动选择（先取消）"],
        defaultButton="一键全场景扫描",
        cancelButton="手动选择（先取消）",
        dismissString="手动选择（先取消）"
    )

    if choice == "一键全场景扫描":
        all_meshes = cmds.ls(type="mesh", long=True) or []
        for mesh in all_meshes:
            try:
                parent = cmds.listRelatives(mesh, parent=True, path=True)
                if parent and parent[0] not in CONFIG["IGNORE_LIST"]:
                    transforms.append(parent[0])
            except Exception:
                continue
        print(f"✅ 已获取全场景模型，共 {len(transforms)} 个。")
        return transforms
    else:
        # 用户选择“手动选择”
        cmds.inViewMessage(
            message="请先在视口中选中需要检查的模型，然后重新运行脚本。",
            fontSize=12,
            fade=True
        )
        print("❌ 用户取消操作。请先选中模型再运行脚本。")
        return []


# =============================================================================
# 3. 核心检测函数
# =============================================================================

def check_transform_frozen(transform_node):
    """
    检查物体变换是否已冻结（平移归零，缩放为1）。
    【性能影响】未冻结的变换会导致引擎每帧进行额外的矩阵计算，影响合批（Batching）效率。
    Returns:
        dict: 包含 status, message, advice 的检查结果。
    """
    try:
        # 1. 获取属性 (使用全称变量，见名知意)
        translate_x = cmds.getAttr(f"{transform_node}.translateX")
        translate_y = cmds.getAttr(f"{transform_node}.translateY")
        translate_z = cmds.getAttr(f"{transform_node}.translateZ")
        
        scale_x = cmds.getAttr(f"{transform_node}.scaleX")
        scale_y = cmds.getAttr(f"{transform_node}.scaleY")
        scale_z = cmds.getAttr(f"{transform_node}.scaleZ")

        # 2. 分步、显式地判断每个分量 (禁止 any/all)
        translate_x_ok = abs(translate_x) < CONFIG["FLOAT_TOLERANCE"]
        translate_y_ok = abs(translate_y) < CONFIG["FLOAT_TOLERANCE"]
        translate_z_ok = abs(translate_z) < CONFIG["FLOAT_TOLERANCE"]
        is_translate_zero = translate_x_ok and translate_y_ok and translate_z_ok

        scale_x_ok = abs(scale_x - 1.0) < CONFIG["FLOAT_TOLERANCE"]
        scale_y_ok = abs(scale_y - 1.0) < CONFIG["FLOAT_TOLERANCE"]
        scale_z_ok = abs(scale_z - 1.0) < CONFIG["FLOAT_TOLERANCE"]
        is_scale_one = scale_x_ok and scale_y_ok and scale_z_ok

        # 3. 汇总结果
        if is_translate_zero and is_scale_one:
            return {
                "status": "✅",
                "message": "变换已冻结",
                "advice": "无需操作，变换完美！"
            }
        else:
            details = (
                f"平移({translate_x:.2f},{translate_y:.2f},{translate_z:.2f}) "
                f"缩放({scale_x:.2f},{scale_y:.2f},{scale_z:.2f})"
            )
            return {
                "status": "❌",
                "message": f"变换未冻结。{details}",
                "advice": "请选中模型 -> 修改(Modify) -> 冻结变换(Freeze Transformations)"
            }
    except Exception as error:
        return {
            "status": "⚠️",
            "message": f"属性读取失败: {error}",
            "advice": "该物体可能是特殊节点或锁定状态，请手动检查"
        }


def check_uv_range(mesh):
    """
    检查UV是否在0-1象限内。
    【性能影响】UV越界会导致光照贴图（Lightmap）烘焙失败或产生接缝。
    Returns:
        dict: 包含 status, message, advice 的检查结果。
    """
    try:
        uv_count = cmds.polyEvaluate(mesh, uv=True)
        if uv_count == 0:
            return {
                "status": "❌",
                "message": "无UV信息",
                "advice": "请为模型创建UV (菜单栏: UV > Create UVs)"
            }

        # 查询U和V坐标范围 (真实的UV检查逻辑)
        u_values = cmds.polyEditUV(mesh + '.map[*]', query=True, u=True)
        v_values = cmds.polyEditUV(mesh + '.map[*]', query=True, v=True)

        if not u_values or not v_values:
            return {
                "status": "⚠️",
                "message": "UV 坐标查询失败",
                "advice": "无法判断 UV 是否越界，请手动检查模型 UV"
            }

        # 分步获取U和V的边界值
        u_min = min(u_values)
        u_max = max(u_values)
        v_min = min(v_values)
        v_max = max(v_values)

        if u_min < 0.0 or u_max > 1.0 or v_min < 0.0 or v_max > 1.0:
            detail = f"U[{u_min:.2f}-{u_max:.2f}] V[{v_min:.2f}-{v_max:.2f}]"
            return {
                "status": "❌",
                "message": f"UV越界。{detail}",
                "advice": "请将UV移动至0-1象限内 (UV Editor > Modify > Normalize)"
            }
        else:
            return {
                "status": "✅",
                "message": "UV在0-1范围内",
                "advice": "UV正常"
            }
    except Exception as error:
        return {
            "status": "⚠️",
            "message": f"UV检查错误: {error}",
            "advice": "无法完成UV检查，请手动确认"
        }


def check_non_manifold(mesh):
    """
    检查是否存在非流形几何（如孤立的顶点、边）。
    【性能影响】非流形几何可能导致网格无法正确进行布尔运算、光照烘焙错误和碰撞检测失败。
    Returns:
        dict: 包含 status, message, advice 的检查结果。
    """
    try:
        non_manifold_edges = cmds.polyInfo(mesh, nonManifoldEdge=True) or []
        non_manifold_vertices = cmds.polyInfo(mesh, nonManifoldVertices=True) or []

        # 分步统计数量
        edge_count = 0
        for _ in non_manifold_edges:
            edge_count += 1

        vertex_count = 0
        for _ in non_manifold_vertices:
            vertex_count += 1

        if edge_count > 0 or vertex_count > 0:
            return {
                "status": "❌",
                "message": f"非流形几何: 坏边 {edge_count} 处, 坏点 {vertex_count} 处",
                "advice": "请使用 Mesh > Cleanup 修复非流形几何体"
            }
        return {
            "status": "✅",
            "message": "流形几何正常",
            "advice": "拓扑正常"
        }
    except Exception as error:
        return {
            "status": "⚠️",
            "message": f"拓扑检查失败: {error}",
            "advice": "无法完成非流形检测，请手动检查"
        }


def get_mesh_stats(mesh):
    """获取网格基础统计数据。"""
    try:
        face_count = cmds.polyEvaluate(mesh, face=True)
        vertex_count = cmds.polyEvaluate(mesh, vertex=True)
        return face_count, vertex_count
    except Exception as error:
        print(f"⚠️ 获取网格统计失败 ({mesh}): {error}")
        return 0, 0


def evaluate_asset_status(face_count, transform_status, non_manifold_status):
    """
    综合评估资产状态。任何关键指标不合格即为“不合格”。
    Returns:
        tuple: (综合状态, 状态描述)
    """
    if face_count > CONFIG["MAX_FACE_COUNT"]:
        return "❌", "面数超限"
    if transform_status.startswith("❌"):
        return "❌", "变换未冻结"
    if non_manifold_status.startswith("❌"):
        return "❌", "存在非流形几何"
    return "✅", "符合规范"


# =============================================================================
# 4. 3D数学应用：资产间距分析
# =============================================================================
def check_asset_spacing(transforms):
    """
    检查资产间的最小距离，防止重叠或过于接近。
    【性能影响】物体重叠会导致深度冲突（Z-fighting），增加Overdraw。
    Returns:
        list: 包含每对资产间距分析结果的列表。
    """
    results = []

    # 遍历所有资产对
    for index_a in range(len(transforms)):
        for index_b in range(index_a + 1, len(transforms)):
            object_a = transforms[index_a]
            object_b = transforms[index_b]
            try:
                # 获取世界空间坐标
                position_a_raw = cmds.xform(object_a, query=True, translation=True, worldSpace=True)
                position_b_raw = cmds.xform(object_b, query=True, translation=True, worldSpace=True)

                position_a = position_a_raw[:3]
                position_b = position_b_raw[:3]

                # 分步计算欧几里得距离 (显式、清晰)
                delta_x = position_b[0] - position_a[0]
                delta_y = position_b[1] - position_a[1]
                delta_z = position_b[2] - position_a[2]
                distance = (delta_x ** 2 + delta_y ** 2 + delta_z ** 2) ** 0.5

                # 根据距离判断风险
                if distance < CONFIG["MIN_SAFE_DISTANCE"]:
                    status = "❌"
                    issue = "资产重叠或距离过近"
                elif distance < CONFIG["MIN_SAFE_DISTANCE"] * 3:
                    status = "⚠️"
                    issue = "距离较近，建议调整"
                else:
                    status = "✅"
                    issue = "距离安全"

                results.append({
                    "资产对": f"{object_a} <-> {object_b}",
                    "距离": round(distance, 2),
                    "状态": status,
                    "问题": issue
                })
            except Exception as error:
                results.append({
                    "资产对": f"{object_a} <-> {object_b}",
                    "状态": "⚠️",
                    "问题": f"计算失败: {error}"
                })
    return results


# =============================================================================
# 5. 报告生成系统 (深色高级主题)
# =============================================================================
def generate_html_report(asset_data, spacing_data, save_path):
    """生成深色主题的专业HTML报告。"""
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>资产性能规范检查报告</title>
    <style>
        /* 深色主题 - 高级专业风格 */
        body {{
            font-family: 'Microsoft YaHei', 'Segoe UI', 'Helvetica Neue', sans-serif;
            margin: 30px;
            background: #1a1a2e;
            color: #e0e0e0;
        }}
        .container {{
            background: #16213e;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: #00d2ff;
            border-bottom: 2px solid #0f3460;
            padding-bottom: 12px;
            font-size: 28px;
            letter-spacing: 2px;
        }}
        h2 {{
            color: #53a8b6;
            margin-top: 30px;
            padding-bottom: 8px;
            border-bottom: 1px dashed #0f3460;
            font-size: 20px;
        }}
        .summary {{
            background: linear-gradient(135deg, #0f3460, #1a1a2e);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #00d2ff;
        }}
        .summary h3 {{
            color: #00d2ff;
            margin-top: 0;
        }}
        .summary p {{
            margin: 8px 0;
            font-size: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
            background: #1a1a2e;
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background-color: #0f3460;
            color: #00d2ff;
            padding: 14px 15px;
            text-align: left;
            font-weight: 600;
            font-size: 14px;
            letter-spacing: 1px;
            white-space: nowrap;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #0f3460;
            color: #c8d6e5;
            font-size: 13px;
        }}
        tr:hover {{
            background-color: rgba(0, 210, 255, 0.05);
        }}
        .status-pass {{
            background-color: rgba(39, 174, 96, 0.15);
            color: #2ecc71;
            font-weight: bold;
        }}
        .status-warning {{
            background-color: rgba(241, 196, 15, 0.15);
            color: #f1c40f;
            font-weight: bold;
        }}
        .status-fail {{
            background-color: rgba(231, 76, 60, 0.15);
            color: #e74c3c;
            font-weight: bold;
        }}
        .suggestion {{
            font-size: 0.85em;
            color: #95a5a6;
            margin-top: 3px;
            font-style: italic;
        }}
        .footer-text {{
            color: #7f8c8d;
            font-size: 0.85em;
        }}
        strong {{
            color: #ecf0f1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 资产性能与规范检查报告</h1>
        <p><strong>生成时间：</strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <h3>📈 扫描概览</h3>
            <p>📦 共扫描资产：<strong>{len(asset_data)}</strong> 个</p>
            <p>✅ 符合规范：<strong>{sum(1 for a in asset_data if a['综合状态'].startswith('✅'))}</strong> 个</p>
            <p>⚠️ 需优化：<strong>{sum(1 for a in asset_data if a['综合状态'].startswith('⚠️'))}</strong> 个</p>
            <p>❌ 不合格：<strong>{sum(1 for a in asset_data if a['综合状态'].startswith('❌'))}</strong> 个</p>
        </div>

        <h2>1. 资产详情检查</h2>
        <table>
            <thead>
                <tr>
                    <th>资产名称</th>
                    <th>面数</th>
                    <th>顶点数</th>
                    <th>变换状态</th>
                    <th>UV状态</th>
                    <th>拓扑状态</th>
                    <th>综合状态</th>
                    <th>优化建议</th>
                </tr>
            </thead>
            <tbody>
    """
    # 填充资产检查数据
    for data in asset_data:
        row_class = {
            "✅": "status-pass",
            "⚠️": "status-warning",
            "❌": "status-fail"
        }.get(data['综合状态'][0], "")

        html_content += f"""
                <tr class="{row_class}">
                    <td><strong>{data['名称']}</strong></td>
                    <td>{data['面数']}</td>
                    <td>{data['顶点数']}</td>
                    <td>{data['变换状态']} <div class="suggestion">{data['变换建议']}</div></td>
                    <td>{data['UV状态']} <div class="suggestion">{data['UV建议']}</div></td>
                    <td>{data['拓扑状态']} <div class="suggestion">{data['拓扑建议']}</div></td>
                    <td><strong>{data['综合状态']}</strong></td>
                    <td>{data['最终建议']}</td>
                </tr>
        """
    html_content += """</tbody></table>"""

    # 填充空间分析数据
    if spacing_data:
        html_content += """
        <h2>2. 资产间距分析（防止重叠）</h2>
        <table>
            <thead>
                <tr>
                    <th>资产对</th>
                    <th>距离</th>
                    <th>状态</th>
                    <th>说明</th>
                </tr>
            </thead>
            <tbody>
        """
        for item in spacing_data:
            row_class = {
                "✅": "status-pass",
                "⚠️": "status-warning",
                "❌": "status-fail"
            }.get(item.get("状态", ""), "")
            html_content += f"""
                <tr class="{row_class}">
                    <td>{item.get('资产对', 'N/A')}</td>
                    <td>{item.get('距离', 'N/A')}</td>
                    <td>{item.get('状态', 'N/A')}</td>
                    <td>{item.get('问题', 'N/A')}</td>
                </tr>
            """
        html_content += """</tbody></table>"""

    # 页脚
    html_content += f"""
        <hr style="border-color: #0f3460; margin-top: 40px;">
        <p class="footer-text" style="text-align: center;">
            Asset Performance Checker v9.0 Final | 技术美术(TA)工具链 | 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
    """
    try:
        with open(save_path, 'w', encoding='utf-8') as file:
            file.write(html_content)
        return True
    except Exception as error:
        print(f"❌ 报告保存失败: {error}")
        return False


# =============================================================================
# 6. 主控逻辑与命令行接口
# =============================================================================
def main():
    """主函数入口：解析参数、获取资产、执行检查、生成报告。"""
    parser = argparse.ArgumentParser(description='Maya资产性能检查工具 (面试作品集标准)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='仅执行检查并生成报告')
    group.add_argument('--clean', action='store_true', help='执行检查后自动清理资产')

    # 在Maya环境中正确解析参数
    try:
        args, _ = parser.parse_known_args(sys.argv[1:])
    except SystemExit:
        args = parser.parse_args([])

    print("=" * 60)
    print("🚀 Asset Performance Checker v9.0 Final 启动...")
    print("=" * 60)

    # 1. 获取目标资产（包含弹窗交互逻辑）
    transforms = get_target_assets()
    if not transforms:
        print("⚠️ 没有可检查的资产，脚本退出。")
        return

    # 2. 用户自定义保存路径（弹窗选择，取消则使用桌面默认路径）
    report_path = None

    # 弹出文件保存对话框，让用户自定义路径和文件名
    try:
        selected_path = cmds.fileDialog2(
            caption="请选择报告保存位置并输入文件名",
            fileFilter="HTML Files (*.html)",
            dialogStyle=2  # 保存模式
        )
        if selected_path:
            report_path = selected_path[0]
            # 确保文件后缀为 .html
            if not report_path.lower().endswith('.html'):
                report_path += '.html'
    except Exception:
        pass

    # 如果用户取消选择，自动使用桌面默认路径
    if not report_path:
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(
            desktop_path,
            f"{CONFIG['DEFAULT_REPORT_NAME']}_{timestamp}.html"
        )
        print(f"ℹ️ 未选择自定义路径，使用默认保存位置: {report_path}")
    else:
        print(f"📂 用户指定保存路径: {report_path}")

    # 3. 执行全面检查
    report_data = []
    print(f"🔍 正在扫描 {len(transforms)} 个资产...")

    for transform_node in transforms:
        try:
            # 获取网格节点
            shapes = cmds.listRelatives(transform_node, shapes=True, path=True) or []
            mesh_shape = None
            for shape in shapes:
                if cmds.objectType(shape) == "mesh":
                    mesh_shape = shape
                    break

            if not mesh_shape:
                continue

            # 执行各项检查
            face_count, vertex_count = get_mesh_stats(mesh_shape)
            transform_check = check_transform_frozen(transform_node)

            if CONFIG["CHECK_UV_RANGE"]:
                uv_check = check_uv_range(mesh_shape)
            else:
                uv_check = {"status": "✅", "message": "已跳过", "advice": ""}

            if CONFIG["CHECK_NON_MANIFOLD"]:
                topo_check = check_non_manifold(mesh_shape)
            else:
                topo_check = {"status": "✅", "message": "已跳过", "advice": ""}

            # 综合评估
            overall_status, overall_reason = evaluate_asset_status(
                face_count,
                transform_check["status"],
                topo_check["status"]
            )

            # 生成最终建议
            if overall_status == "✅":
                final_advice = "良好，可直接提交。"
            elif "面数" in overall_reason:
                final_advice = "请使用减面工具或检查LOD级别。"
            elif "变换" in overall_reason:
                final_advice = transform_check["advice"]
            elif "非流形" in overall_reason:
                final_advice = topo_check["advice"]
            else:
                final_advice = "请根据具体警告项进行优化。"

            # 组装检查结果
            report_data.append({
                "名称": transform_node,
                "面数": face_count,
                "顶点数": vertex_count,
                "变换状态": transform_check["status"],
                "变换建议": transform_check["advice"],
                "UV状态": uv_check["status"],
                "UV建议": uv_check["advice"],
                "拓扑状态": topo_check["status"],
                "拓扑建议": topo_check["advice"],
                "综合状态": f"{overall_status} {overall_reason}",
                "最终建议": final_advice
            })

        except Exception as error:
            print(f"⚠️ 扫描资产 {transform_node} 时出错，已跳过: {error}")
            continue

    # 4. 执行3D空间分析
    if CONFIG["CHECK_SPACING"]:
        spacing_results = check_asset_spacing(transforms)
    else:
        spacing_results = []

    # 5. 生成HTML报告
    if generate_html_report(report_data, spacing_results, report_path):
        print(f"\n✅ 报告已生成: {report_path}")
        print(f"📊 共扫描资产: {len(report_data)} 个")

        # 控制台文本摘要
        print("\n📋 控制台检查摘要:")
        for item in report_data:
            print(f"  {item['名称']} -> {item['综合状态']} | 面数: {item['面数']}")

        # 自动打开报告
        try:
            os.startfile(report_path)
        except Exception:
            print(f"💡 请手动打开报告: {report_path}")
    else:
        print("❌ 报告生成失败。")

    print("=" * 60)
    print("✅ Asset Performance Checker 执行完毕。")


# =============================================================================
# 7. 脚本入口
# =============================================================================
if __name__ == "__main__":
    main()