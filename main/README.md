# Uplifted Main 目录

本目录包含 Uplifted 的客户端组件和可扩展的整合框架。

## 目录结构

```
main/
├── sdk/                          # Uplifted Python SDK
│   ├── __init__.py
│   └── client.py                 # 完整的 API 客户端
│
├── integration/                  # 通用整合框架 ⭐
│   ├── __init__.py
│   ├── base.py                   # 基础整合类
│   └── cli.py                    # 通用交互式 CLI
│
├── integrations/                 # 具体整合实现 ⭐
│   ├── __init__.py
│   └── hexstrike.py              # HexStrike AI 整合
│
├── hexstrike-ai/                 # HexStrike AI 服务
│   ├── hexstrike_server.py
│   ├── hexstrike_mcp.py
│   └── requirements.txt
│
├── cli.py                        # 通用 CLI 入口 ⭐
├── hexstrike_integration.py      # HexStrike 快捷入口（向后兼容）
├── HEXSTRIKE_INTEGRATION.md
└── README.md
```

## 🚀 快速开始

### 1. Uplifted SDK

完整的 Uplifted API 客户端，支持所有 API 端点。

```python
from sdk import UpliftedClient

client = UpliftedClient("http://localhost:7541")

# 检查服务
if client.status():
    print("✅ Uplifted 服务正常")

# 运行 Agent
result = client.run_agent(
    prompt="你好",
    llm_model="openai/gpt-4o"
)
print(result)

client.close()
```

### 2. 使用整合框架

**方式 1: 使用通用 CLI（推荐）**

```bash
# 启动 HexStrike AI 整合
python cli.py hexstrike

# 列出所有可用整合
python cli.py --list

# 未来可以轻松添加其他整合
# python cli.py other_tool
```

**方式 2: 使用快捷入口**

```bash
# 向后兼容的快捷方式
python hexstrike_integration.py
```

**方式 3: 在代码中使用**

```python
from integrations import HexStrikeIntegration
from integration import ConversationalCLI

# 创建整合实例
integration = HexStrikeIntegration()

# 编程方式使用
status = integration.get_service_status()
integration.register_to_uplifted()
tools = integration.get_available_tools()

# 或启动交互式 CLI
cli = ConversationalCLI(integration)
cli.run()
```

## 🎯 整合框架

### 核心设计

框架采用 **基于继承的插件架构**，让添加新整合变得简单：

```python
from integration import BaseIntegration

class YourIntegration(BaseIntegration):
    """您的工具整合"""

    def get_integration_name(self) -> str:
        return "Your Tool Name"

    def get_service_status(self) -> Dict[str, bool]:
        # 检查服务状态
        return {"uplifted": True, "your_service": True}

    def register_to_uplifted(self) -> Dict[str, Any]:
        # 注册到 Uplifted
        return self.uplifted_client.add_mcp_tool(...)

    def get_available_tools(self) -> List[str]:
        # 返回工具列表
        return ["tool1", "tool2"]

    # 可选：自定义更多功能
    def get_tool_categories(self) -> Dict[str, List[str]]:
        return {"分类1": ["关键词1", "关键词2"]}

    def get_example_prompts(self) -> List[str]:
        return ["示例提示词1", "示例提示词2"]
```

### 添加新整合的步骤

**1. 创建整合类** (`integrations/your_tool.py`)

```python
from integration import BaseIntegration

class YourToolIntegration(BaseIntegration):
    def __init__(self, uplifted_url="http://localhost:7541"):
        super().__init__(uplifted_url)
        # 添加您的初始化逻辑

    # 实现必须的方法...
```

**2. 注册到 CLI** (`cli.py`)

```python
from integrations.your_tool import YourToolIntegration

AVAILABLE_INTEGRATIONS = {
    "your_tool": {
        "class": YourToolIntegration,
        "description": "您的工具描述"
    }
}
```

**3. 使用新整合**

```bash
python cli.py your_tool
```

就是这么简单！✨

## 📚 框架 API 参考

### BaseIntegration（基础整合类）

#### 必须实现的方法

| 方法 | 说明 | 返回值 |
|------|------|--------|
| `get_integration_name()` | 获取整合名称 | `str` |
| `get_service_status()` | 检查服务状态 | `Dict[str, bool]` |
| `register_to_uplifted()` | 注册到 Uplifted | `Dict[str, Any]` |
| `get_available_tools()` | 获取工具列表 | `List[str]` |

#### 可选实现的方法

| 方法 | 说明 | 默认值 |
|------|------|--------|
| `get_service_urls()` | 服务地址 | `{"uplifted": url}` |
| `get_startup_commands()` | 启动命令 | `{}` |
| `get_tool_categories()` | 工具分类 | `{}` |
| `get_example_prompts()` | 示例提示词 | `[]` |

#### 通用方法（可直接使用）

| 方法 | 说明 |
|------|------|
| `check_uplifted_status()` | 检查 Uplifted 状态 |
| `run_agent(prompt, ...)` | 运行 Uplifted Agent |
| `test_integration()` | 测试整合 |

### ConversationalCLI（交互式 CLI）

自动提供的功能：
- ✅ 问答式交互界面
- ✅ 服务状态检查
- ✅ 注册管理
- ✅ 整合测试
- ✅ 工具列表
- ✅ Agent 请求处理
- ✅ 中英文命令支持

## 🔧 HexStrike AI 整合

### 前置条件

**启动服务：**

```bash
# 终端 1: 启动 Uplifted
cd D:\code\Uplifted\server
python -m uplifted.server

# 终端 2: 启动 HexStrike
cd D:\code\Uplifted\main\hexstrike-ai
python hexstrike_server.py

# 终端 3: 运行整合工具
cd D:\code\Uplifted\main
python cli.py hexstrike
```

### 交互式使用

```
您> 状态
✓ Uplifted 服务正常
✓ HexStrike Server 正常

您> 注册
✓ HexStrike AI 注册成功！

您> 工具
找到 150 个安全工具
🔍 网络扫描:
  • nmap
  • rustscan
  ...

您> 列出所有网络扫描工具
正在处理您的请求...
Agent 响应：...

您> 退出
再见！
```

### 编程方式使用

```python
from integrations import HexStrikeIntegration

integration = HexStrikeIntegration(
    uplifted_url="http://localhost:7541",
    hexstrike_server_url="http://localhost:8888"
)

# 检查状态
status = integration.get_service_status()

# 注册
integration.register_to_uplifted()

# 获取工具
tools = integration.get_available_tools()

# 运行 Agent
result = integration.run_agent("扫描 example.com")
```

## 💡 使用场景

### 场景 1: 通过 SDK 使用 Uplifted

```python
from sdk import UpliftedClient

client = UpliftedClient("http://localhost:7541")

# 使用 GPT-4
result = client.run_agent(
    prompt="分析代码安全问题",
    llm_model="openai/gpt-4o"
)
```

### 场景 2: 整合外部工具

```python
# 1. 创建整合类
class MyToolIntegration(BaseIntegration):
    def get_integration_name(self):
        return "My Tool"
    # ... 实现其他方法

# 2. 注册到 CLI
AVAILABLE_INTEGRATIONS["mytool"] = {
    "class": MyToolIntegration,
    "description": "My Tool Integration"
}

# 3. 使用
# python cli.py mytool
```

### 场景 3: AI 驱动的安全测试

```python
from integrations import HexStrikeIntegration

integration = HexStrikeIntegration()
integration.register_to_uplifted()

result = integration.run_agent(
    prompt="""
    我是安全研究人员，已获得授权测试 example.com。
    请执行全面的安全评估。
    """
)
```

## 📦 依赖安装

```bash
# 基础依赖
pip install httpx cloudpickle requests

# HexStrike 依赖
cd main/hexstrike-ai
pip install -r requirements.txt
```

## 🆘 常见问题

### Q: 如何添加新的工具整合？

A: 只需三步：
1. 在 `integrations/` 创建新文件
2. 继承 `BaseIntegration` 并实现必需方法
3. 在 `cli.py` 中注册

### Q: 旧的 hexstrike_integration.py 还能用吗？

A: 可以！保留了向后兼容性，但建议使用新的 `cli.py hexstrike`。

### Q: 如何自定义 CLI 行为？

A: 继承 `ConversationalCLI` 类并覆盖相应方法。

### Q: 框架支持哪些整合方式？

A: 目前支持 MCP 工具整合，未来可扩展支持插件、REST API 等方式。

## 📖 文档

- **整合框架**: `integration/base.py` 和 `integration/cli.py` 中的文档字符串
- **HexStrike 整合**: [HEXSTRIKE_INTEGRATION.md](./HEXSTRIKE_INTEGRATION.md)
- **SDK 文档**: `sdk/client.py` 中的文档字符串

## 🎉 总结

**新架构的优势：**
- ✅ **可扩展** - 添加新整合只需几分钟
- ✅ **模块化** - 整合逻辑和 CLI 完全分离
- ✅ **可复用** - 通用 CLI 支持所有整合
- ✅ **易维护** - 清晰的代码结构
- ✅ **向后兼容** - 保留原有入口

**快速开始命令：**

```bash
# 列出可用整合
python cli.py --list

# 使用 HexStrike AI
python cli.py hexstrike

# 添加您自己的整合
# 1. 创建 integrations/your_tool.py
# 2. 继承 BaseIntegration
# 3. 注册到 cli.py
# 4. python cli.py your_tool
```

**现在您可以轻松扩展 Uplifted 的能力了！** 🚀
