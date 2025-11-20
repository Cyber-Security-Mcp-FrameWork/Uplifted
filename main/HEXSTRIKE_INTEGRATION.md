# HexStrike AI x Uplifted 整合文档

## 概述

本文档介绍如何将 **HexStrike AI**（AI 驱动的网络安全自动化平台）整合到 **Uplifted** 中。

### 什么是 HexStrike AI？

HexStrike AI 是一个强大的 AI 驱动网络安全自动化平台，包含：

- **150+ 专业安全工具**
  - 网络扫描（Nmap, Rustscan, Masscan 等）
  - Web 应用测试（Gobuster, Nuclei, SQLMap 等）
  - 密码破解（Hydra, John, Hashcat 等）
  - 二进制分析（Ghidra, Radare2, GDB 等）
  - 云安全（Prowler, Trivy, Kube-Hunter 等）
  - CTF 工具（Volatility, Steghide, Foremost 等）

- **12+ 专业 AI Agents**
  - Bug Bounty Workflow Manager - 漏洞赏金工作流
  - CTF Workflow Manager - CTF 挑战解决
  - CVE Intelligence Manager - 漏洞情报
  - AI Exploit Generator - 自动化漏洞利用生成
  - Vulnerability Correlator - 攻击链发现
  - Technology Detector - 技术栈识别

### 什么是 Uplifted？

Uplifted 是一个现代化的 AI Agent 框架，提供：

- Level One & Level Two Agent API
- 插件系统
- MCP (Model Context Protocol) 工具支持
- 配置管理
- 完整的 Python SDK

## 整合架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        用户                                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ 使用交互式 CLI
                       │
┌──────────────────────▼──────────────────────────────────────┐
│            hexstrike_integration.py                         │
│            (交互式整合工具)                                  │
│                                                             │
│  • 检查服务状态                                             │
│  • 注册 HexStrike MCP                                       │
│  • 测试整合                                                 │
│  • 列出工具                                                 │
│  • 运行 Agent 示例                                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Uses Uplifted SDK
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   Uplifted Server                           │
│                  (Port 7541)                                │
│                  ← 需要独立启动                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Level One/Two Agents                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MCP Tool Manager                       │   │
│  │  • add_mcp_tool()                                   │   │
│  │  • Manages MCP processes                            │   │
│  └────────────────────┬────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ MCP Protocol (stdio)
                       │
┌──────────────────────▼──────────────────────────────────────┐
│              HexStrike MCP Client                           │
│              (hexstrike_mcp.py)                             │
│                                                             │
│  • FastMCP integration                                      │
│  • Tool registration                                        │
│  • Request forwarding                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTP API (localhost:8888)
                     │
┌────────────────────▼────────────────────────────────────────┐
│              HexStrike Server                               │
│              (hexstrike_server.py)                          │
│              Port 8888                                      │
│              ← 需要独立启动                                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         Intelligent Decision Engine                 │   │
│  │  • Tool Selection AI                                │   │
│  │  • Parameter Optimization                           │   │
│  │  • Attack Chain Discovery                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              12+ AI Agents                          │   │
│  │  • BugBounty Agent                                  │   │
│  │  • CTF Solver Agent                                 │   │
│  │  • CVE Intelligence Agent                           │   │
│  │  • Exploit Generator Agent                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │         150+ Security Tools                         │   │
│  │  • Nmap, Rustscan, Masscan                          │   │
│  │  • Gobuster, Nuclei, SQLMap                         │   │
│  │  • Hydra, John, Hashcat                             │   │
│  │  • Ghidra, Radare2, GDB                             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 整合方式

我们采用 **MCP 工具整合方式**，这是最符合 Uplifted 架构的方案：

1. **Uplifted Server** 和 **HexStrike Server** 作为独立服务运行
2. **hexstrike_integration.py** 提供交互式 CLI 界面
3. 通过 CLI 将 **HexStrike MCP** 注册到 Uplifted
4. **AI Agents** 通过 Uplifted 调用 HexStrike 的所有安全工具

### 优势

✅ **清晰的服务边界** - 每个服务独立运行和管理
✅ **松耦合架构** - 各组件可独立更新和维护
✅ **简单的整合流程** - 通过交互式 CLI 完成整合
✅ **完整功能保留** - HexStrike 的所有能力完全可用
✅ **标准 MCP 协议** - 使用行业标准通信协议

## 安装和配置

### 前置条件

1. **Python 环境**
   - Python 3.8+
   - 安装基础依赖

2. **目录结构**
   ```
   D:\code\Uplifted\
   ├── server/                    # Uplifted 服务
   └── main/
       ├── sdk/                   # Uplifted SDK
       ├── hexstrike-ai/          # HexStrike AI
       └── hexstrike_integration.py  # 整合工具
   ```

### 安装步骤

#### 1. 安装 HexStrike AI 依赖

```bash
cd D:\code\Uplifted\main\hexstrike-ai
pip install -r requirements.txt
```

#### 2. 启动 Uplifted 服务

```bash
# 终端 1
cd D:\code\Uplifted\server
python -m uplifted.server
```

验证：
```bash
curl http://localhost:7541/status
```

#### 3. 启动 HexStrike Server

```bash
# 终端 2
cd D:\code\Uplifted\main\hexstrike-ai
python hexstrike_server.py
```

验证：
```bash
curl http://localhost:8888/health
```

#### 4. 使用整合工具

```bash
# 终端 3
cd D:\code\Uplifted\main
python hexstrike_integration.py
```

## 使用指南

### 交互式 CLI

运行整合工具后，会看到以下菜单：

```
======================================================================
    HexStrike AI x Uplifted 整合工具
    AI-Powered Cybersecurity Automation Platform
======================================================================

可用操作：
  1. 检查服务状态
  2. 注册 HexStrike MCP
  3. 测试整合
  4. 列出 HexStrike 工具
  5. 运行 Agent 示例
  0. 退出
```

#### 功能说明

**1. 检查服务状态**
- 检查 Uplifted Server 是否运行
- 检查 HexStrike Server 是否运行
- 显示服务地址

**2. 注册 HexStrike MCP**
- 将 HexStrike MCP 注册到 Uplifted
- 首次使用时必须执行此操作
- 注册后可通过 Uplifted Agent 使用 HexStrike 工具

**3. 测试整合**
- 测试服务连接
- 测试工具列表获取
- 验证整合是否成功

**4. 列出 HexStrike 工具**
- 显示所有可用的安全工具
- 按类别分组显示
- 包括网络、Web、密码、二进制、云安全、CTF 等

**5. 运行 Agent 示例**
- 提供多个预设示例场景
- 演示如何使用 HexStrike 工具
- 包括工具查询、安全评估、CTF 分析等

### 编程方式使用

除了交互式 CLI，也可以在 Python 代码中使用：

```python
from hexstrike_integration import HexStrikeIntegration

# 创建整合实例
integration = HexStrikeIntegration(
    uplifted_url="http://localhost:7541",
    hexstrike_server_url="http://localhost:8888"
)

# 检查服务状态
status = integration.check_services()
print(status)  # {'uplifted': True, 'hexstrike': True}

# 注册 MCP 工具（首次使用）
result = integration.register_hexstrike_mcp()
print(result)

# 测试整合
success = integration.test_integration()

# 获取工具列表
tools = integration.get_hexstrike_tools()
print(f"可用工具: {len(tools)}")

# 运行 Agent
result = integration.run_agent(
    prompt="列出所有 hexstrike-ai 网络扫描工具"
)
print(result)
```

## 使用示例

### 示例 1: 首次设置

```bash
# 1. 启动服务（两个终端）
# 终端 1: cd server && python -m uplifted.server
# 终端 2: cd main/hexstrike-ai && python hexstrike_server.py

# 2. 运行整合工具
cd main
python hexstrike_integration.py

# 3. 在 CLI 中操作
# 选择 1 - 检查服务状态（确认两个服务都在运行）
# 选择 2 - 注册 HexStrike MCP（首次使用必须）
# 选择 3 - 测试整合（验证配置正确）
```

### 示例 2: 查看可用工具

```python
from hexstrike_integration import HexStrikeIntegration

integration = HexStrikeIntegration()

# 获取所有工具
tools = integration.get_hexstrike_tools()

# 按类别筛选
network_tools = [t for t in tools if any(k in t.lower() for k in ['nmap', 'scan', 'masscan'])]
web_tools = [t for t in tools if any(k in t.lower() for k in ['gobuster', 'nuclei', 'sqlmap'])]

print(f"网络工具: {len(network_tools)}")
print(f"Web 工具: {len(web_tools)}")
```

### 示例 3: 网络安全评估（需要授权）

```python
from hexstrike_integration import HexStrikeIntegration

integration = HexStrikeIntegration()

# 执行网络扫描（需要授权）
prompt = """
我是安全研究人员，正在对我们公司拥有的系统 192.168.1.100 进行授权安全测试。
请使用 hexstrike-ai 工具进行基础网络扫描：
1. 扫描开放端口
2. 识别服务版本
3. 检测常见漏洞
"""

result = integration.run_agent(prompt=prompt)
print(result)
```

### 示例 4: Web 应用测试（需要授权）

```python
from hexstrike_integration import HexStrikeIntegration

integration = HexStrikeIntegration()

prompt = """
我是安全研究人员，正在对我们公司的网站 https://example.com 进行授权安全测试。
请使用 hexstrike-ai 工具进行 Web 应用安全评估：
1. 目录枚举
2. 技术栈识别
3. 安全头检查
4. 常见漏洞扫描（XSS, SQL注入等）
"""

result = integration.run_agent(prompt=prompt)
print(result)
```

### 示例 5: CTF 挑战分析

```python
from hexstrike_integration import HexStrikeIntegration

integration = HexStrikeIntegration()

prompt = """
这是一个 CTF 二进制挑战：
- 文件：challenge.bin
- 提示：栈溢出漏洞

请使用 hexstrike-ai 的二进制分析工具：
1. 检查二进制安全属性
2. 识别漏洞点
3. 建议利用方法
"""

result = integration.run_agent(prompt=prompt)
print(result)
```

## API 参考

### HexStrikeIntegration 类

#### 构造函数

```python
HexStrikeIntegration(
    uplifted_url: str = "http://localhost:7541",
    hexstrike_server_url: str = "http://localhost:8888",
    hexstrike_dir: Optional[str] = None
)
```

**参数：**
- `uplifted_url`: Uplifted 服务地址
- `hexstrike_server_url`: HexStrike Server 地址
- `hexstrike_dir`: HexStrike AI 目录路径（可选）

#### 主要方法

##### check_services()

检查服务状态。

```python
status = integration.check_services()
# 返回: {'uplifted': True, 'hexstrike': True}
```

##### register_hexstrike_mcp()

将 HexStrike MCP 注册到 Uplifted。

```python
result = integration.register_hexstrike_mcp()
```

##### test_integration()

测试整合是否成功。

```python
success = integration.test_integration()
```

##### get_hexstrike_tools()

获取 HexStrike 提供的所有工具。

```python
tools = integration.get_hexstrike_tools()
# 返回: ['nmap', 'gobuster', 'nuclei', ...]
```

##### run_agent()

通过 Uplifted 运行 Agent。

```python
result = integration.run_agent(
    prompt="你的提示词",
    tools=["tool1", "tool2"],  # 可选
    **kwargs
)
```

## 常见问题

### Q1: 服务启动顺序重要吗？

**A:** 不重要。Uplifted Server 和 HexStrike Server 可以按任意顺序启动，它们是独立的服务。只要在使用整合工具前确保两个服务都在运行即可。

### Q2: 需要每次都注册 MCP 吗？

**A:** 不需要。MCP 注册是持久化的，只需在首次使用时注册一次。后续使用只需确保两个服务在运行即可。

### Q3: Uplifted 服务启动失败

**问题：** 端口 7541 被占用

**解决方案：**
```bash
# 检查端口占用
netstat -ano | findstr 7541  # Windows
lsof -i :7541                # Linux/Mac

# 终止占用进程或修改 Uplifted 配置使用其他端口
```

### Q4: HexStrike Server 启动失败

**问题：** 端口 8888 被占用或依赖未安装

**解决方案：**
```bash
# 1. 检查端口
netstat -ano | findstr 8888  # Windows

# 2. 安装依赖
cd main/hexstrike-ai
pip install -r requirements.txt

# 3. 查看详细错误
python hexstrike_server.py --debug
```

### Q5: 整合工具无法连接服务

**问题：** CLI 显示服务未运行

**解决方案：**
1. 在 CLI 中选择"1. 检查服务状态"查看详情
2. 确保两个服务都在运行
3. 检查防火墙设置
4. 验证服务地址是否正确

### Q6: 工具执行失败

**问题：** Agent 调用工具时返回错误

**解决方案：**
1. 确保 HexStrike 所需的安全工具已安装（Nmap, Gobuster 等）
2. 检查目标是否可访问
3. 确认是否有必要的权限
4. 查看 HexStrike Server 日志

### Q7: 如何安装安全工具？

HexStrike AI 需要实际的安全工具才能工作。

**Linux (Ubuntu/Debian):**
```bash
# 核心工具
sudo apt install nmap masscan gobuster hydra john
```

**Mac:**
```bash
brew install nmap masscan gobuster hydra john
```

**Windows:**
- 部分工具可通过 Chocolatey 安装
- 建议使用 WSL 或 Linux 虚拟机

### Q8: 法律和道德问题

⚠️ **重要：仅在授权的情况下使用**

**合法使用：**
- ✅ 对自己拥有的系统进行测试
- ✅ 已获得书面授权的渗透测试
- ✅ Bug Bounty 计划（遵守规则）
- ✅ CTF 比赛和安全研究

**禁止使用：**
- ❌ 未经授权的扫描和攻击
- ❌ 恶意使用和数据窃取
- ❌ 违反法律法规的行为

## 故障排除

### 服务连接问题

```python
from hexstrike_integration import HexStrikeIntegration

integration = HexStrikeIntegration()

# 检查详细状态
status = integration.check_services()
print("Uplifted:", "✓" if status['uplifted'] else "✗")
print("HexStrike:", "✓" if status['hexstrike'] else "✗")

# 如果服务未运行，会显示启动命令
```

### MCP 注册问题

```python
try:
    result = integration.register_hexstrike_mcp()
    print("注册成功:", result)
except FileNotFoundError as e:
    print("找不到 MCP 脚本:", e)
except Exception as e:
    print("注册失败:", e)
```

### 查看日志

**Uplifted 日志:**
- 位置：服务终端输出
- 包含 API 请求和错误信息

**HexStrike 日志:**
- 位置：服务终端输出
- 包含工具执行和错误信息

## 性能优化

HexStrike Server 内置智能缓存系统，自动优化重复请求。可以通过 API 查看缓存状态：

```python
import requests

response = requests.get("http://localhost:8888/api/cache/stats")
print(response.json())
```

## 更新日志

### v1.0.0 (2024-11)

- ✅ MCP 工具整合实现
- ✅ 交互式 CLI 工具
- ✅ 服务独立运行架构
- ✅ 完整的使用示例
- ✅ 详细文档

## 许可证

- Uplifted: MIT License
- HexStrike AI: MIT License

---

**整合完成！现在您可以通过 Uplifted 使用 HexStrike AI 的所有强大功能了！** 🎉
