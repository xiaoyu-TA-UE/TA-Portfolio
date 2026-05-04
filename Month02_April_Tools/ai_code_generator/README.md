# AI 代码生成工具 (AI Code Generator)

**版本**: 2.0 Final | **作者**: [小宇] | **日期**: 2026年4月

## 📖 简介

通过自然语言描述需求，调用硅基流动 API 让大模型生成符合工业规范的 Maya/UE Python 脚本。

**核心价值**：让 AI 生成代码自动符合编码规范，减少手动修改时间。预设模板降低美术使用门槛。

## 🧩 功能模块

| 模块           | 说明                                                         |
| :------------- | :----------------------------------------------------------- |
| **命令行参数** | 支持 `--prompt`（需求描述）、`--output`（保存路径）、`--template`（预设模板） |
| **系统提示词** | 内置性能 TA 专属规范，生成的代码自动包含显式循环、中文注释、异常处理 |
| **预设模板库** | `freeze`（冻结变换）、`html_report`（HTML报告）、`batch_check`（批量检查） |
| **失败重试**   | API 调用超时或失败时自动重试（最多3次，间隔2秒）             |
| **文件保护**   | 输出文件已存在时自动添加时间戳后缀，防止覆盖                 |

## 🚀 使用方法

### 安装依赖

```bash
pip install requests
```

### 设置 API Key

```bash
# Windows
set SILICONFLOW_API_KEY=你的API密钥
# Mac/Linux
export SILICONFLOW_API_KEY=你的API密钥
```

### 使用预设模板生成代码

```bash
python ai_code_gen.py --template freeze --output freeze_assets.py
```

### 使用需求描述生成代码

```bash
python ai_code_gen.py --prompt "写一个 Maya 批量重命名工具" --output rename_tool.py
```

### 列出所有可用模板

```bash
python ai_code_gen.py --list-templates
```

## 📂 文件结构

```
ai_code_gen_enhanced.py
├── CONFIG              # API参数配置（URL、模型、温度、重试次数）
├── SYSTEM_PROMPT       # 性能TA专属系统提示词（约束AI生成代码风格）
├── PROMPT_TEMPLATES    # 预设提示词模板库
├── call_siliconflow_api()  # 调用硅基流动API（带重试机制）
├── save_generated_code()   # 保存代码到文件
├── main()                  # 命令行参数解析和主控逻辑
└── __name__ == "__main__"
```

## 🔐 安全设计

API Key 通过环境变量 `SILICONFLOW_API_KEY` 读取，**永不硬编码在代码中**。因此可以安全地上传到 GitHub 而不会泄露密钥。

## 📜 代码规范遵循

严格遵循《代码风格生成规范》。`SYSTEM_PROMPT` 中明确要求 AI 生成代码时：

- 使用显式 `for` 循环，禁用 `any()`/`all()`
- 变量名见名知意
- 包含 `try-except` 异常处理
- 关键步骤用中文注释解释性能影响

## 👤 作者

[小宇] - 技术美术(TA)学习者，性能优化、工具流程与AI辅助开发方向。
