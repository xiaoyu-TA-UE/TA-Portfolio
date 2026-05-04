# -*- coding: utf-8 -*-
"""
AI Code Generator (AI 代码生成工具)
版本: 2.0 Final (工业级面试版 - 硅基流动 API)
作者: [小宇]
描述:
    专为技术美术(TA)打造的 AI 辅助代码生成工具。
    核心目标：通过自然语言描述需求，由大模型生成符合工业规范的 Maya/UE Python 脚本。
    特点：
    1. 硅基流动 API 集成：稳定、快速、国内无障碍访问。
    2. 命令行参数支持：--prompt（需求描述）、--output（保存路径）、--template（预设模板）。
    3. 内置性能 TA 专属提示词：生成的代码自动包含异常处理、中文注释、显式循环。
    4. 预设模板库：freeze（冻结变换）、html_report（HTML报告生成）、batch_check（批量检查）。
    5. 工业级错误处理：API 调用失败自动重试，文件写入异常友好提示。

使用方法（命令行）:
    # 使用需求描述直接生成代码
    python ai_code_gen.py --prompt "写一个 Maya 批量重命名脚本" --output renamed_script.py

    # 使用预设模板生成代码
    python ai_code_gen.py --template freeze --output freeze_assets.py

    # 不指定输出路径时，自动保存为 generated_script.py
    python ai_code_gen.py --prompt "写一个 Maya 清理场景的脚本"

依赖安装:
    pip install requests
"""

import argparse
import os
import sys
import json
from datetime import datetime

# 尝试导入 requests 库，如果未安装则给出友好提示
try:
    import requests
except ImportError:
    print("❌ 缺少依赖库: requests")
    print("请运行以下命令安装:")
    print("    pip install requests")
    sys.exit(1)


# =============================================================================
# 1. 配置中心 (所有 API 参数和模板在此管理)
# =============================================================================
CONFIG = {
    # 硅基流动 API 配置
    "API_URL": "https://api.siliconflow.cn/v1/chat/completions",
    # 从环境变量读取 API Key，避免硬编码在代码中
    "API_KEY": os.environ.get("SILICONFLOW_API_KEY", "请设置环境变量 SILICONFLOW_API_KEY"),
    "MODEL": "Pro/deepseek-ai/DeepSeek-V3.2",
    "TEMPERATURE": 0.3,     # 较低温度保证代码生成稳定
    "MAX_TOKENS": 2048,     # 最大生成 Token 数
    "REQUEST_TIMEOUT": 60,  # API 请求超时时间（秒）
    "MAX_RETRIES": 3,       # 失败重试次数
    "RETRY_DELAY": 2,       # 重试间隔（秒）

    # 默认输出路径
    "DEFAULT_OUTPUT_FILENAME": "generated_script.py"
}


# =============================================================================
# 2. 性能 TA 专属系统提示词 (System Prompt)
# =============================================================================
SYSTEM_PROMPT = """你是一个资深技术美术（性能优化方向），擅长编写 Maya Python 和 UE Python 脚本。

你的代码必须满足以下工业级规范：
1. 使用显式 for 循环，禁止使用 any()、all()、嵌套列表推导式。
2. 变量名必须见名知意（如 face_count、translate_x），禁用单字母变量（除 x,y,z 临时使用）。
3. 每个函数必须包含 try-except 异常处理，捕获具体异常信息（except Exception as error）。
4. 关键步骤用中文注释解释"为什么这么做对性能有影响"。
5. 所有阈值、路径必须可配置，不硬编码在代码中。
6. 函数返回结果使用 Emoji 前缀（✅ / ⚠️ / ❌）。
7. 每个函数必须有完整的 docstring，说明参数、返回值和性能影响。

输出要求：
- 只返回可运行的 Python 代码块，不要额外解释。
- 代码开头必须包含 # -*- coding: utf-8 -*-。
- 代码必须包含 if __name__ == "__main__": 入口。
"""


# =============================================================================
# 3. 预设提示词模板库
# =============================================================================
PROMPT_TEMPLATES = {
    "freeze": (
        "写一个 Maya Python 脚本，实现以下功能："
        "1. 获取用户选中的所有网格物体。"
        "2. 检查每个物体的变换是否已冻结（平移归零、缩放归一）。"
        "3. 如果未冻结，自动执行冻结变换操作（Freeze Transformations）。"
        "4. 删除每个物体的构造历史（Delete History）。"
        "5. 在 Maya 视口中显示清理完成的消息提示。"
    ),
    "html_report": (
        "写一个 Maya Python 脚本，实现以下功能："
        "1. 扫描用户选中的所有网格物体。"
        "2. 统计每个物体的面数、顶点数、UV 数量。"
        "3. 检查每个物体的变换是否已冻结。"
        "4. 将检查结果生成为深色主题的 HTML 报告，保存到桌面。"
        "5. HTML 报告需要使用表格展示检查结果，通过/警告/不合格用不同颜色区分。"
    ),
    "batch_check": (
        "写一个 Maya Python 脚本，实现以下功能："
        "1. 遍历场景中所有的网格物体（Mesh）。"
        "2. 对每个物体执行以下检查："
        "   - 面数是否超过 10000。"
        "   - UV 是否在 0-1 范围内。"
        "   - 是否存在非流形几何（Non-Manifold Geometry）。"
        "   - 命名是否符合规范（不能包含中文或空格）。"
        "3. 将不符合规范的资产名称和问题原因打印到控制台。"
        "4. 在控制台输出检查摘要：总扫描数、通过数、不合格数。"
    ),
}


# =============================================================================
# 4. 核心函数：调用硅基流动 API 生成代码
# =============================================================================

def call_siliconflow_api(user_prompt):
    """
    调用硅基流动 API，使用通义千问模型生成 Python 代码。

    Args:
        user_prompt (str): 用户的需求描述文本。

    Returns:
        str: 生成的 Python 代码字符串。
             如果 API 调用失败，返回空字符串。
    """
    # 构建请求头
    headers = {
        "Authorization": f"Bearer {CONFIG['API_KEY']}",
        "Content-Type": "application/json"
    }

    # 构建请求体
    payload = {
        "model": CONFIG["MODEL"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": CONFIG["TEMPERATURE"],
        "max_tokens": CONFIG["MAX_TOKENS"]
    }

    # 带重试机制的 API 调用
    retry_count = 0
    while retry_count < CONFIG["MAX_RETRIES"]:
        try:
            print(f"📡 正在调用硅基流动 API (第 {retry_count + 1} 次)...")

            response = requests.post(
                CONFIG["API_URL"],
                json=payload,
                headers=headers,
                timeout=CONFIG["REQUEST_TIMEOUT"]
            )

            # 检查 HTTP 状态码
            if response.status_code == 200:
                response_data = response.json()
                # 提取生成的代码内容
                generated_code = response_data["choices"][0]["message"]["content"]
                print(f"✅ API 调用成功，生成代码长度: {len(generated_code)} 字符")
                return generated_code

            else:
                print(f"⚠️ API 返回错误状态码: {response.status_code}")
                print(f"   错误信息: {response.text}")

        except requests.exceptions.Timeout:
            print(f"⚠️ API 请求超时 (超过 {CONFIG['REQUEST_TIMEOUT']} 秒)")
        except requests.exceptions.ConnectionError:
            print("⚠️ 网络连接失败，请检查网络状态")
        except Exception as error:
            print(f"⚠️ API 调用异常: {error}")

        # 重试前等待
        retry_count += 1
        if retry_count < CONFIG["MAX_RETRIES"]:
            import time
            print(f"⏳ 等待 {CONFIG['RETRY_DELAY']} 秒后重试...")
            time.sleep(CONFIG["RETRY_DELAY"])

    print(f"❌ API 调用失败，已重试 {CONFIG['MAX_RETRIES']} 次")
    return ""


# =============================================================================
# 5. 工具函数：保存代码到文件
# =============================================================================

def save_generated_code(code, output_path):
    """
    将生成的代码保存到指定文件。
    如果文件已存在，自动添加时间戳后缀防止覆盖。

    Args:
        code (str): 生成的 Python 代码内容。
        output_path (str): 目标文件路径。

    Returns:
        tuple: (是否成功, 实际保存的文件路径, 错误消息)
    """
    try:
        # 如果文件已存在，添加时间戳后缀
        if os.path.exists(output_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name_parts = os.path.splitext(output_path)
            output_path = f"{file_name_parts[0]}_{timestamp}{file_name_parts[1]}"
            print(f"ℹ️ 文件已存在，自动重命名为: {output_path}")

        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(code)

        return True, output_path, ""

    except PermissionError:
        return False, output_path, "没有写入权限，请选择其他保存路径"
    except FileNotFoundError:
        return False, output_path, "保存路径不存在，请检查路径是否正确"
    except Exception as error:
        return False, output_path, f"文件写入失败: {error}"


# =============================================================================
# 6. 主控逻辑与命令行接口
# =============================================================================

def main():
    """主函数入口：解析参数、调用 API、保存代码。"""
    parser = argparse.ArgumentParser(
        description='AI 代码生成工具 - 性能 TA 专属 (硅基流动 API)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 通过需求描述生成代码
  python ai_code_gen.py --prompt "写一个 Maya 批量重命名工具" --output my_tool.py

  # 使用预设模板生成代码
  python ai_code_gen.py --template freeze --output freeze_assets.py

  # 查看所有可用模板
  python ai_code_gen.py --list-templates

  # 不指定输出路径，自动保存为 generated_script.py
  python ai_code_gen.py --prompt "写一个 Maya 清理历史节点的脚本"
        """
    )

    # 定义命令行参数
    parser.add_argument(
        '--prompt',
        type=str,
        help='需求描述文本，例如"写一个 Maya 批量重命名脚本"'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=CONFIG["DEFAULT_OUTPUT_FILENAME"],
        help=f'输出文件的保存路径 (默认: {CONFIG["DEFAULT_OUTPUT_FILENAME"]})'
    )
    parser.add_argument(
        '--template',
        type=str,
        choices=list(PROMPT_TEMPLATES.keys()),
        help='使用预设提示词模板，可用模板: freeze, html_report, batch_check'
    )
    parser.add_argument(
        '--list-templates',
        action='store_true',
        help='列出所有可用的预设模板'
    )

    # 解析参数
    try:
        args = parser.parse_args(sys.argv[1:])
    except SystemExit:
        return

    print("=" * 60)
    print("🚀 AI Code Generator v2.0 Final 启动...")
    print("=" * 60)

    # 列出所有可用模板
    if args.list_templates:
        print("\n📋 预设提示词模板列表:")
        print("-" * 40)
        for template_name, template_prompt in PROMPT_TEMPLATES.items():
            # 截取前 80 个字符作为描述
            description = template_prompt[:80].replace('\n', ' ') + "..."
            print(f"  🏷️  {template_name}: {description}")
        print("\n使用方法: python ai_code_gen.py --template <模板名> --output <输出路径>")
        return

    # 确定最终使用的提示词
    user_prompt = None

    if args.template:
        if args.template in PROMPT_TEMPLATES:
            user_prompt = PROMPT_TEMPLATES[args.template]
            print(f"📝 使用预设模板: {args.template}")
        else:
            print(f"❌ 未知模板: {args.template}")
            print(f"可用模板: {', '.join(PROMPT_TEMPLATES.keys())}")
            return
    elif args.prompt:
        user_prompt = args.prompt
        print(f"📝 使用自定义需求描述")
    else:
        print("❌ 请指定 --prompt 或 --template 参数")
        print("使用 --help 查看详细用法")
        return

    # 调用 API 生成代码
    generated_code = call_siliconflow_api(user_prompt)

    if not generated_code:
        print("❌ 代码生成失败，请检查 API Key 和网络连接。")
        print("💡 提示: 请确保已设置环境变量 SILICONFLOW_API_KEY")
        print("    Windows: set SILICONFLOW_API_KEY=你的API密钥")
        print("    Mac/Linux: export SILICONFLOW_API_KEY=你的API密钥")
        return

    # 保存生成的代码
    success, actual_path, error_message = save_generated_code(generated_code, args.output)

    if success:
        print(f"\n✅ 代码生成成功！")
        print(f"📂 保存路径: {actual_path}")
        print(f"📊 代码长度: {len(generated_code)} 字符")

        # 控制台预览前 200 个字符
        print("\n📋 生成的代码预览 (前 200 字符):")
        print("-" * 40)
        preview = generated_code[:200]
        if len(generated_code) > 200:
            preview += "\n... (剩余内容请打开文件查看)"
        print(preview)
    else:
        print(f"\n❌ 保存失败: {error_message}")

    print("\n" + "=" * 60)
    print("✅ AI Code Generator 执行完毕。")


# =============================================================================
# 7. 脚本入口
# =============================================================================
if __name__ == "__main__":
    main()