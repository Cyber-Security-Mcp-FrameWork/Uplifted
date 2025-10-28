```
 __  __     ______     __         __     ______   ______   ______     _____
/\ \/\ \   /\  == \   /\ \       /\ \   /\  ___\ /\__  _\ /\  ___\   /\  __-.
\ \ \_\ \  \ \  _-/   \ \ \____  \ \ \  \ \  __\ \/_/\ \/ \ \  __\   \ \ \/\ \
 \ \_____\  \ \_\      \ \_____\  \ \_\  \ \_\      \ \_\  \ \_____\  \ \____-
  \/_____/   \/_/       \/_____/   \/_/   \/_/       \/_/   \/_____/   \/____/

              [ 企业级安全智能框架 ]
              [ 由 AI Agents + MCP 工具生态系统驱动 ]
```

<div align="center">

[![Version](https://img.shields.io/badge/version-1.0.0-00ff00.svg?style=for-the-badge&logo=github)](https://github.com/Cyber-Security-Mcp-FrameWork/uplifted)
[![License](https://img.shields.io/badge/license-MIT-00ff00.svg?style=for-the-badge)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-00ff00.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![MCP Compatible](https://img.shields.io/badge/MCP-COMPATIBLE-ff0000.svg?style=for-the-badge)](https://github.com/Cyber-Security-Mcp-FrameWork/uplifted)

```ascii
┌─────────────────────────────────────────────────────────────────────────┐
│  "给我一个目标，我会给你一个 0day。"                                    │
│                                                     - Uplifted AI Agent │
└─────────────────────────────────────────────────────────────────────────┘
```

**[`🔬 创新`](#-innovation-highlights) • [`📡 安装`](#-quick-deployment) • [`⚡ 功能`](#-core-capabilities) • [`🎯 利用`](#-use-cases) • [`💀 文档`](#-documentation) • [`🔧 贡献`](#-join-the-resistance)**

</div>

---

## 🎭 这是什么

**Uplifted** = 红队自动化平台 + AI Agent 驱动的攻击性安全测试框架

把最强的 LLM（GPT, Claude, Gemini等）和 MCP 工具生态系统结合，让 AI 成为你的渗透测试员、漏洞研究员、红队成员。通过 MCP 协议接入任意安全工具，自动化执行从侦察到利用的完整攻击链，让你专注于高价值目标和复杂漏洞。

**重要说明**：Uplifted 是基于 REST API 的服务器架构，通过 HTTP API 使用，不提供 SDK。

```python
# 从目标到 Exploit，全自动
import requests

# 创建 Agent
response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "claude-3.5-sonnet",
    "tools": ["subdomain_enum", "port_scanner", "web_scanner", "exploit_db"]
})
agent_id = response.json()['agent_id']

# 执行攻击链
response = requests.post(f'http://localhost:7541/api/v1/agents/{agent_id}/run', json={
    "message": "在 target.com 上找到 0day 漏洞并生成 exploit"
})
# Agent 自动调用你配置的 MCP 工具，完成：
# 信息收集 → 漏洞扫描 → 漏洞验证 → Exploit 生成 → 权限提升
```

### 👥 适用人群

- **🎯 渗透测试人员** - 自动化重复性测试任务，专注于复杂场景
- **🐛 Bug Bounty Hunters** - 批量扫描目标，提高漏洞发现效率
- **🔴 红队成员** - 模拟真实攻击，评估企业防御能力
- **🔬 安全研究人员** - 漏洞研究和 POC 开发的智能助手
- **🛡️ 安全审计师** - 全面的安全评估和合规测试

### 🏗️ 架构概述

**Uplifted 是一个 REST API 服务器，不是 SDK 或命令行工具。**

```
你的代码 (Python/Node.js/任何语言)
        ↓ HTTP API 调用
    Uplifted Server
        ↓
    AI Agent 编排器
        ↓
    MCP 工具生态系统
```

**两种工具接入方式：**

1. **插件系统**（推荐用于复杂工具集）
   - 插件 = 容器，可包含多个工具
   - 示例：`security_scanner` 插件 → 包含 `port_scan`、`vuln_scan`、`exploit` 等工具
   - 通过 MCPPluginBridge 自动注册

2. **独立 MCP 工具**（推荐用于快速集成）
   - 直接连接外部 MCP 服务器
   - 示例：直接使用 `@modelcontextprotocol/server-nmap`
   - 无需创建插件包装

### 🔥 为什么选择 UPLIFTED?

```diff
- 传统渗透：手工操作 + 10个终端 + 100个脚本 + 遗漏某些攻击面 = 💩
+ Uplifted：一个 Agent + 自动化攻击链 + AI 智能决策 = 🚀

测试效率：60-70% ⬆️
漏洞发现率：3-5倍 ⬆️
从侦察到 Exploit：自动化
咖啡消耗：300% ⬆️ (因为你有时间喝了)
```

### 🎯 核心优势

**对于渗透测试人员**:
- ✅ 自动化重复性的侦察和扫描任务
- ✅ AI 自动识别和验证漏洞
- ✅ 生成专业的测试报告

**对于 Bug Bounty Hunters**:
- ✅ 批量处理多个目标
- ✅ 24/7 持续扫描新资产
- ✅ 自动生成 POC 和报告

**对于红队成员**:
- ✅ 模拟 APT 攻击场景
- ✅ 自动化横向移动和权限提升
- ✅ 真实攻击链的完整复现

---

## 🔬 创新亮点

> **这不是又一个安全工具集合，这是安全领域的范式转变**

<table>
<tr><td width="50%">

### 🌟 **首个 MCP 原生安全框架**
```
传统方式：每个工具独立运行
             ↓
      集成困难 + 无法协同

Uplifted：  所有工具统一 MCP 协议
             ↓
      AI 自动调用 + 智能编排
```
将 Model Context Protocol 大规模应用于**网络安全领域**的框架。通过 MCP 标准化协议，AI Agent 可以接入和调用任意安全工具，像人类黑客一样自由组合使用工具。支持连接 MCP 生态系统中数百个现有工具，也可以自行开发定制工具。

</td><td width="50%">

### 🧠 **Agent Swarm 分布式智能**
```
    Agent A        Agent B      Agent C
       ↓              ↓            ↓
   子域枚举        端口扫描     漏洞扫描
       ↓              ↓            ↓
         AI Orchestrator (协调器)
                  ↓
           综合分析 + 决策
```
**多 Agent** 协同架构。不是单个 AI 做所有事情，而是专业分工 + 智能协调。就像一个渗透测试团队，每个 Agent 专注自己的领域。

</td></tr>
<tr><td width="50%">

### ⚡ **Plugin-to-MCP 自动桥接**
```python
# 你的自定义脚本
class MyScanner:
    def scan(self, target):
        return results

# 自动转换为 MCP 工具
bridge.register_plugin(MyScanner)

# AI Agent 立即可用
agent.run("Use MyScanner on target.com")
```
**任何**Python 插件自动转换为 MCP 工具。一行代码，你的脚本就能被 AI 调用。不需要学习 MCP 协议，不需要重写代码。

</td><td width="50%">

### 🎯 **双层 Agent 架构**
```
Level One (无状态)          Level Two (有状态)
     ↓                          ↓
   快速调用                   持续对话
   无记忆                     有记忆
   并发执行                   上下文理解
     ↓                          ↓
   简单任务                   复杂任务
```
根据**任务复杂度**自动选择架构。简单任务用 Level One 秒级响应，复杂任务用 Level Two 深度推理。性能和智能的完美平衡。

</td></tr>
<tr><td width="50%">

### 🔒 **安全加固的 AI Agent**
```bash
[✓] 命令注入防护
[✓] 代码执行沙箱
[✓] 路径遍历保护
[✓] SQL 注入防护
[✓] 反序列化防御
```
**内置**安全防护的 AI Agent 框架。不是让 AI 破坏安全，而是让 AI 在安全的沙箱中工作。

</td><td width="50%">

### 🧬 **智能上下文管理**
```
原始对话：100K tokens
    ↓
自动压缩算法
    ↓
压缩后：8K tokens (保留关键信息)
    ↓
突破 LLM 限制，支持超长对话
```
**自动识别和保留**关键上下文，智能压缩冗余信息。让 AI Agent 能够处理长达数小时的渗透测试任务，不会"失忆"。

</td></tr>
<tr><td width="50%">

### 🌐 **多模型并行验证**
```
      User Task
         ↓
    ┌────┴────┬────────┐
    ↓         ↓        ↓
  GPT-4    Claude   Gemini
    ↓         ↓        ↓
    └────┬────┴────────┘
         ↓
   Consensus Engine
         ↓
    Verified Result
```
**同时**运行多个 LLM，通过共识机制验证结果。降低 AI 幻觉风险，提高判断准确性。就像安全团队的 Peer Review。

</td><td width="50%">

### 📦 **统一配置抽象层**
```python
# 同一个接口，5+ 种格式
config = ConfigManager()
config.load("config.json")      # JSON
config.load("config.toml")      # TOML
config.load("config.ini")       # INI
config.load("config.db")        # SQLite
config.load("config.enc")       # Encrypted
# 环境变量也自动支持
```
**支持 5+ 种**配置格式的统一接口。一套代码，适配所有场景。从开发到生产无缝切换。

</td></tr>
</table>

### 💡 技术创新总结

```
┌──────────────────────────────────────────────────────────────────┐
│ 🏆 7 项技术创新 + 3 项架构创新 = 改变游戏规则的框架              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ MCP 协议在安全领域的首次大规模应用                           │
│  ✅ Agent Swarm 分布式智能架构                                   │
│  ✅ Plugin-to-MCP 自动桥接技术                                   │
│  ✅ 双层 Agent 架构（Level One + Level Two）                     │
│  ✅ Security-Hardened AI Agent 设计                              │
│  ✅ 智能上下文压缩算法                                           │
│  ✅ 多模型并行验证机制                                           │
│  ✅ 统一配置抽象层                                               │
│  ✅ 动态工具注册表                                               │
│  ✅ 实时工具发现和热加载                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**这些创新不是为了创新而创新，而是解决了安全自动化领域的真实痛点。**

---

## ⚡ 核心能力

### 🤖 AI 驱动一切

```python
import requests

# 创建自主决策的 Agent
response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "claude-3.5-sonnet",  # 或 gpt-4, gemini-pro, ollama
    "system_prompt": "你是自主渗透测试 Agent，自行决策工具使用",
    "mode": "autonomous"
})

agent_id = response.json()['agent_id']
print(f"[*] Agent 已创建: {agent_id}")
print("[*] AI 模型加载完成")
print("[*] MCP 工具生态系统已初始化")
print("[*] Agent 就绪，等待你的指令")
```

- **多模型并发** - 同时运行多个 AI 模型，互相验证结果
- **自主决策** - Agent 自己决定用什么工具、怎么用
- **上下文理解** - 理解整个攻击链，不只是单点操作
- **持续学习** - 从每次操作中学习，越用越聪明

### 🔧 MCP 工具生态系统

通过 MCP 协议，Uplifted 可以接入任意安全工具，包括但不限于：

```
┌──────────────────────────────────────────────────────────┐
│ RECON       │ nmap, masscan, amass, subfinder...       │
│             │ 信息收集和目标枚举                        │
├─────────────┼──────────────────────────────────────────┤
│ EXPLOIT     │ metasploit, sqlmap, xsstrike, burp...   │
│             │ 漏洞利用和 Exploit 生成                  │
├─────────────┼──────────────────────────────────────────┤
│ POST-EXPLOIT│ mimikatz, bloodhound, empire...         │
│             │ 权限提升和横向移动                        │
├─────────────┼──────────────────────────────────────────┤
│ OSINT       │ shodan, censys, theHarvester...         │
│             │ 情报收集和目标分析                        │
├─────────────┼──────────────────────────────────────────┤
│ WEB         │ dirsearch, ffuf, nuclei, wpscan...      │
│             │ Web 应用漏洞扫描                         │
├─────────────┼──────────────────────────────────────────┤
│ CUSTOM      │ 你的自定义工具，自动转换为 MCP             │
│             │ 自定义工具自动集成                        │
└──────────────────────────────────────────────────────────┘
```

### 🚀 并行处理架构

```
        ┌─────────────────┐
        │  你的应用代码     │
        │  (HTTP Client)   │
        └────────┬─────────┘
                 │ REST API
    ┌────────────┴────────────┐
    │  UPLIFTED API Server    │
    └────┬─────────────┬──────┘
         │             │
    ┌────┴──┐      ┌──┴────┐
    │Agent 1│      │Agent 2│  ← 并行工作
    └───┬───┘      └───┬───┘
        │ MCP          │ MCP
    ┌───┴──┐       ┌──┴───┐
    │Tool A│       │Tool B│
    └──────┘       └──────┘
```

- **多 Agent 协同** - 通过 API 同时创建和运行多个 Agent
- **任务队列** - 智能任务调度，最大化资源利用
- **异步执行** - 不阻塞，所有操作都是异步的
- **API 驱动** - 任何支持 HTTP 的语言都可以使用


---

## 🎯 使用场景

> **明确定位：攻击性安全测试和红队自动化**

<table>
<tr><td>

### 🔍 渗透测试
```python
# 全自动渗透测试
import requests

response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "claude-3.5-sonnet",
    "tools": ["nmap", "nikto", "sqlmap", "metasploit"]
})
agent_id = response.json()['agent_id']

# 执行全面渗透测试
requests.post(f'http://localhost:7541/api/v1/agents/{agent_id}/run', json={
    "message": "对 target.com 进行完整渗透测试，深度扫描，生成 markdown 报告",
    "context": {"depth": "full", "report_format": "markdown"}
})

# [*] Reconnaissance...
# [*] Vulnerability scanning...
# [*] Exploitation attempts...
# [*] Post-exploitation...
# [*] Report generated: pwned.md
```
**用途**: 企业安全评估、合规测试、定期渗透测试

</td><td>

### 🔴 红队行动
```python
# 红队演练模拟真实攻击
import requests

response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "gpt-4",
    "tools": ["phishing_toolkit", "mimikatz", "bloodhound", "empire"]
})
agent_id = response.json()['agent_id']

# 执行 APT 攻击模拟
requests.post(f'http://localhost:7541/api/v1/agents/{agent_id}/run', json={
    "message": "模拟 APT 攻击：corp-internal 网络",
    "context": {"scenario": "apt-simulation", "stealth": True}
})

# [*] Initial access: Phishing
# [*] Privilege escalation: ✓
# [*] Lateral movement: 5 hosts
# [*] Data exfiltration: Simulated
```
**用途**: 红蓝对抗、攻击模拟、防御能力评估

</td></tr>
<tr><td>

### 🐛 漏洞赏金挖掘
```python
# 自动化漏洞挖掘
import requests

response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "claude-3.5-sonnet",
    "tools": ["subfinder", "httpx", "nuclei", "xsstrike", "sqlmap"]
})
agent_id = response.json()['agent_id']

# 执行自动化漏洞挖掘
requests.post(f'http://localhost:7541/api/v1/agents/{agent_id}/run', json={
    "message": "wildcard.com 的完整漏洞挖掘，主动模式",
    "context": {"automation": "aggressive"}
})

# [*] Subdomain enum: 847 found
# [*] Scanning vulnerabilities...
# [*] XSS found in login.wildcard.com
# [*] SQL injection in api.wildcard.com
# [*] Generating POC...
```
**用途**: HackerOne/Bugcrowd 赏金、批量目标扫描

</td><td>

### 🔬 漏洞研究
```python
# 漏洞研究和 Exploit 开发
import requests

response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "gpt-4",
    "tools": ["ghidra", "frida", "afl_fuzzer", "pwntools"]
})
agent_id = response.json()['agent_id']

# 执行漏洞研究
requests.post(f'http://localhost:7541/api/v1/agents/{agent_id}/run', json={
    "message": "分析 app.apk，进行模糊测试",
    "context": {"mode": "fuzzing", "target_file": "app.apk"}
})

# [*] Reverse engineering...
# [*] Fuzzing 1000 test cases...
# [*] Crash detected: heap overflow
# [*] Generating exploit template...
```
**用途**: 0-day 研究、Exploit 开发、漏洞分析

</td></tr>
</table>

### ⚠️ 重要提示 - 合法与道德使用

```
┌──────────────────────────────────────────────────────────────┐
│  ⚖️  仅在授权目标上使用                                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ✅ 已授权的渗透测试                                          │
│  ✅ 你自己的系统和网络                                        │
│  ✅ 漏洞赏金计划（在范围内）                                  │
│  ✅ 安全研究（获得许可）                                      │
│  ✅ CTF 竞赛和训练实验室                                      │
│                                                              │
│  ❌ 未授权访问系统                                            │
│  ❌ 恶意攻击或破坏                                            │
│  ❌ 违反法律法规                                              │
│                                                              │
│  用户有责任遵守所有适用法律。                                 │
│  滥用可能导致刑事起诉。                                       │
└──────────────────────────────────────────────────────────────┘
```

---

## 📡 快速部署

### 🎯 使用方式说明

**Uplifted 是 REST API 服务器，使用方式：**

1. **启动 Uplifted 服务器**（本地或远程）
2. **通过 HTTP API 调用**（任何语言）
3. **无需安装 SDK 或客户端库**

```bash
# 你只需要一个能发 HTTP 请求的工具
curl http://localhost:7541/api/v1/status
```

### ⚡ One-Liner (最快)

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Cyber-Security-Mcp-FrameWork/uplifted/main/install.sh | bash
```

**Windows (PowerShell as Admin):**
```powershell
irm https://raw.githubusercontent.com/Cyber-Security-Mcp-FrameWork/uplifted/main/install.ps1 | iex
```

安装后，Uplifted 将作为后台服务运行，监听端口 7541 和 8086。

### 🐳 Docker (推荐)

```bash
# Clone
git clone https://github.com/Cyber-Security-Mcp-FrameWork/uplifted.git
cd uplifted

# Configure
cp .env.example .env
nano .env  # 添加你的 API keys

# Launch
docker-compose up -d

# Verify
curl http://localhost:7541/status
```

**服务启动后访问：**
- 🌐 **Main API**: `http://localhost:7541` - Agent 管理、任务执行
- 📚 **API 文档**: `http://localhost:7541/docs` - Swagger UI
- 🔧 **Tools Server**: `http://localhost:8086` - 工具管理、MCP 集成

**验证安装：**
```bash
# 检查服务状态
curl http://localhost:7541/status

# 查看 API 文档
open http://localhost:7541/docs  # macOS
start http://localhost:7541/docs  # Windows
xdg-open http://localhost:7541/docs  # Linux
```

### 🔧 手动安装（黑客专用）

<details>
<summary>💀 点击展开黑魔法</summary>

```bash
# 1. Clone the repo
git clone https://github.com/Cyber-Security-Mcp-FrameWork/uplifted.git
cd uplifted

# 2. Setup virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Configure
cp .env.example .env
nano .env  # Add your LLM API keys

# 5. Fire it up
cd server
python run_main_server.py

# 6. Test
curl http://localhost:7541/status
```

</details>

---

## 💻 代码示例

**重要说明**：所有示例都是通过 **HTTP API** 调用，Uplifted 不提供 Python SDK。你可以使用任何支持 HTTP 的语言和工具。

### 示例 1: 创建并配置渗透测试 Agent

**第一步：添加你需要的 MCP 工具**

```python
import requests

# 方式 1: 添加外部 MCP 工具（推荐快速开始）
requests.post('http://localhost:8086/tools/add_mcp_tool', json={
    "name": "nmap",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-nmap"],
    "env": {}
})

requests.post('http://localhost:8086/tools/add_mcp_tool', json={
    "name": "nikto",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-nikto"],
    "env": {}
})

# 方式 2: 加载插件（适合复杂工具集）
# 插件会自动注册其包含的所有工具
requests.post('http://localhost:7541/api/v1/plugins/load', json={
    "plugin_dir": "/path/to/your/plugin"
})
```

**第二步：创建 Agent**

```python
# 创建一个专业的渗透测试 Agent
response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "claude-3-5-sonnet",  # 最强大脑
    "system_prompt": """
    你是一位拥有 10 年经验的精英渗透测试人员。
    你专注于 Web 应用安全、网络渗透和权限提升。
    始终识别最关键的漏洞并提供利用路径。

    可用工具：nmap (端口扫描)、nikto (Web 扫描)
    """
})

agent_id = response.json()['agent_id']
print(f"[+] 渗透测试 Agent 已创建: {agent_id}")
```

### 示例 2: 全自动攻击链执行

```python
# 让 Agent 执行完整的攻击链
response = requests.post(f'http://localhost:7541/api/v1/agents/{agent_id}/run', json={
    "message": """
    目标: example.com
    任务: 完整渗透测试与漏洞利用
    范围: 所有子域名、Web 应用、网络服务

    执行完整攻击链:
    - 资产发现和枚举
    - 漏洞识别和验证
    - 尝试利用
    - 后渗透和权限提升
    - 生成 POC 和利用报告
    """,
    "context": {
        "mode": "autonomous",  # Agent 自主决策
        "max_depth": 3,
        "timeout": 3600,
        "aggressive": True  # 启用主动利用
    }
})

# Agent 会自动执行：
# 1. 子域名枚举和资产发现
# 2. 端口扫描和服务指纹识别
# 3. 漏洞扫描和验证
# 4. 自动尝试利用
# 5. 权限提升和横向移动
# 6. 生成 POC 和利用报告

result = response.json()
print(result['response'])
print(f"[+] 攻击链完成")
print(f"[+] 使用的工具: {', '.join(result['tools_used'])}")
print(f"[+] 成功利用的漏洞: {result['exploits_successful']}")
```

### 示例 3: 自动化 Bug Bounty 扫描

```python
import requests
import time

# 批量扫描多个 Bug Bounty 目标
targets = [
    "target1.com",
    "target2.com",
    "target3.com"
]

for target in targets:
    # 为每个目标创建专门的 Agent
    response = requests.post('http://localhost:7541/api/v1/agents/create', json={
        "model": "gpt-4",
        "system_prompt": f"""
        你是 Bug Bounty Hunter。
        目标: {target}
        重点: XSS、SQLi、SSRF、IDOR、权限提升
        使用所有可用工具进行全面扫描。
        """
    })

    agent_id = response.json()['agent_id']
    print(f"[+] 为 {target} 创建 Agent: {agent_id}")

    # 启动扫描
    scan_result = requests.post(
        f'http://localhost:7541/api/v1/agents/{agent_id}/run',
        json={"message": f"执行完整的漏洞扫描"}
    )

    result = scan_result.json()
    print(f"[+] {target}: 扫描完成")
    print(f"    工具使用: {result.get('tools_used', [])}")
    print(f"    发现问题: {result.get('findings_count', 0)} 个")

    time.sleep(2)  # 避免过快请求
```

### 示例 4: 集成自定义工具

**方式 1：创建简单的 MCP 工具服务器**

```python
# my_scanner_server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("my-scanner")

@app.tool()
async def scan_target(target: str, scan_type: str = "quick") -> dict:
    """
    自定义扫描工具

    Args:
        target: 目标地址
        scan_type: 扫描类型 (quick/full)
    """
    # 你的扫描逻辑
    results = {
        "target": target,
        "vulnerabilities": [
            {"type": "XSS", "severity": "high", "location": "/search?q="}
        ]
    }
    return results

if __name__ == "__main__":
    import asyncio
    asyncio.run(stdio_server(app))
```

**方式 2：注册到 Uplifted**

```python
import requests

# 添加你的自定义工具
response = requests.post('http://localhost:8086/tools/add_mcp_tool', json={
    "name": "my_scanner",
    "command": "python",
    "args": ["my_scanner_server.py"],
    "env": {}
})

print(f"工具已注册: {response.json()}")

# 现在可以在 Agent 中使用了
response = requests.post('http://localhost:7541/api/v1/agents/create', json={
    "model": "claude-3.5-sonnet",
    "system_prompt": "使用 my_scanner 工具扫描目标"
})
```

**方式 3：创建完整插件（适合复杂工具集）**

参考文档：[`docs/PLUGIN_DEVELOPMENT_TUTORIAL.md`](./docs/PLUGIN_DEVELOPMENT_TUTORIAL.md)
```

### 示例 5: 使用其他语言调用（Bash/Node.js/Go）

**因为 Uplifted 是 REST API，你可以用任何语言调用！**

**Bash + curl:**
```bash
# 创建 Agent
agent_response=$(curl -s -X POST http://localhost:7541/api/v1/agents/create \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3.5-sonnet",
    "system_prompt": "你是渗透测试专家"
  }')

agent_id=$(echo $agent_response | jq -r '.agent_id')
echo "[+] Agent 创建成功: $agent_id"

# 执行任务
curl -X POST "http://localhost:7541/api/v1/agents/$agent_id/run" \
  -H "Content-Type: application/json" \
  -d '{"message": "扫描 example.com"}'
```

**Node.js:**
```javascript
const axios = require('axios');

async function createAndRunAgent() {
    // 创建 Agent
    const createResponse = await axios.post('http://localhost:7541/api/v1/agents/create', {
        model: 'claude-3.5-sonnet',
        system_prompt: '你是渗透测试专家'
    });

    const agentId = createResponse.data.agent_id;
    console.log(`[+] Agent 创建成功: ${agentId}`);

    // 执行任务
    const runResponse = await axios.post(
        `http://localhost:7541/api/v1/agents/${agentId}/run`,
        { message: '扫描 example.com' }
    );

    console.log('[+] 结果:', runResponse.data);
}

createAndRunAgent();
```

**Go:**
```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "net/http"
)

type CreateAgentRequest struct {
    Model        string `json:"model"`
    SystemPrompt string `json:"system_prompt"`
}

func main() {
    // 创建 Agent
    reqBody, _ := json.Marshal(CreateAgentRequest{
        Model:        "claude-3.5-sonnet",
        SystemPrompt: "你是渗透测试专家",
    })

    resp, _ := http.Post(
        "http://localhost:7541/api/v1/agents/create",
        "application/json",
        bytes.NewBuffer(reqBody),
    )
    defer resp.Body.Close()

    var result map[string]interface{}
    json.NewDecoder(resp.Body).Decode(&result)

    agentId := result["agent_id"].(string)
    fmt.Printf("[+] Agent 创建成功: %s\n", agentId)
}
```

---

## 🏗️ 架构详解

### 系统架构

```
┌───────────────────────────────────────────────────────────────┐
│                你的应用 (任何语言)                              │
│         Python | Node.js | Go | Bash | Curl                  │
└──────────────────────────┬────────────────────────────────────┘
                           │ HTTP/REST API
                           ↓
┌───────────────────────────────────────────────────────────────┐
│                     🌐 Uplifted REST API                      │
│              (FastAPI + WebSocket + Swagger)                  │
│                                                               │
│  • Main Server:  http://localhost:7541 (Agent 管理)          │
│  • Tools Server: http://localhost:8086 (工具管理)            │
└──────────────────────────┬────────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────────┐
│                   ⚙️  Service Manager                         │
│        Process Lifecycle | Health Check | Port Cleanup        │
└──────────────────────────┬────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
┌─────────────▼──────────┐   ┌─────────▼──────────────┐
│   🤖 Agent Orchestrator │   │   🔧 Tool Integrator   │
│                         │   │                        │
│  • Level One (Calls)    │◄──┤  • MCP Ecosystem       │
│  • Level Two (Agents)   │   │  • Plugin System       │
│  • Parallel Processing  │   │  • Dynamic Registry    │
│  • Memory Management    │   │  • Tool Discovery      │
└─────────────┬───────────┘   └─────────┬──────────────┘
              │                         │
┌─────────────▼─────────────────────────▼──────────────┐
│              📚 Model Registry                        │
│   OpenAI | Anthropic | Google | Ollama | DeepSeek   │
└───────────────────────────────────────────────────────┘
```

### 工具系统架构

```
工具接入方式 1: 插件系统
┌─────────────────────────────────┐
│  Plugin: security_scanner       │
│  ├── Tool: port_scan            │
│  ├── Tool: vuln_scan            │
│  └── Tool: exploit_search       │
└─────────┬───────────────────────┘
          │ MCPPluginBridge
          │ 自动注册
          ↓
     MCP Tool Registry

工具接入方式 2: 独立 MCP 工具
┌─────────────────────────────────┐
│  External MCP Server            │
│  (如 @mcp/server-nmap)          │
└─────────┬───────────────────────┘
          │ 直接连接
          │ POST /tools/add_mcp_tool
          ↓
     MCP Tool Registry
```

**关键概念：**

| 概念 | 说明 | 示例 |
|------|------|------|
| **插件 (Plugin)** | 完整的扩展包，包含多个工具 | `security_scanner` 插件 |
| **工具 (Tool)** | 具体的功能实现 | `port_scan` 工具 |
| **MCP Server** | 提供工具的外部服务 | `@mcp/server-nmap` |
| **工具命名** | 格式：`{source}.{tool_name}` | `nmap.port_scan` |

**数据流:**
```
HTTP 请求 → API 验证 → Agent 编排器 → 工具选择 → LLM 决策 →
MCP 工具调用 → 结果聚合 → HTTP 响应
```

完整架构文档: [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md)

---

## 💀 文档

### 📖 核心文档

```bash
docs/
├── ARCHITECTURE.md                  # 🏗️  系统架构设计
├── DEPLOYMENT.md                    # 🚀 部署和安装指南
├── OPERATIONS_GUIDE.md              # 🔧 运维和监控手册
├── TESTING_GUIDE.md                 # 🧪 测试指南
├── PLUGIN_DEVELOPMENT_TUTORIAL.md   # 🔌 插件开发教程
└── CONFIG_MANAGEMENT.md             # ⚙️  配置管理

examples/
├── API_USAGE.md                     # 📡 API 使用示例（必读！）
└── server_with_plugins.py           # 🔧 插件集成示例
```

**推荐阅读顺序：**
1. [`examples/API_USAGE.md`](./examples/API_USAGE.md) - **了解如何通过 API 使用**
2. [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) - 理解架构设计
3. [`docs/PLUGIN_DEVELOPMENT_TUTORIAL.md`](./docs/PLUGIN_DEVELOPMENT_TUTORIAL.md) - 开发自定义工具


### 🌐 API 参考

启动服务后访问：
- **Swagger UI**: http://localhost:7541/docs
- **ReDoc**: http://localhost:7541/redoc

```bash
# 导出 API 规范
curl http://localhost:7541/openapi.json > api-spec.json
```

---

## 🧪 测试与质量

```bash
# 运行全部测试
pytest tests/ -v

# 单元测试
pytest tests/unit/ -v

# 集成测试
pytest tests/integration/ -v

# 覆盖率报告
pytest --cov=server/uplifted --cov-report=html tests/
open htmlcov/index.html
```

### 📊 指标

```
┌─────────────────┬──────────┬──────────┬────────┐
│ 指标            │ 当前     │ 目标     │ 状态   │
├─────────────────┼──────────┼──────────┼────────┤
│ 测试覆盖率      │ 85%      │ 80%      │ ✅ ⬆️  │
│ 单元测试        │ 110+     │ 100+     │ ✅ ✓   │
│ 集成测试        │ 40+      │ 30+      │ ✅ ⬆️  │
│ 代码质量        │ A+       │ A        │ ✅ ⬆️  │
└─────────────────┴──────────┴──────────┴────────┘
```

完整测试指南: [`docs/TESTING_GUIDE.md`](./docs/TESTING_GUIDE.md)

---

## 🔧 加入我们

欢迎所有形式的贡献！bug fixes、new features、docs improvements、甚至是 typo fixes。

### 🚀 快速贡献

```bash
# 1. Fork & Clone
git clone https://github.com/YOUR_USERNAME/uplifted.git
cd uplifted

# 2. Create feature branch
git checkout -b feature/badass-feature

# 3. Make your changes
# ... code code code ...

# 4. Commit with style
git add .
git commit -m "feat: add badass feature that does X"

# 5. Push
git push origin feature/badass-feature

# 6. Create Pull Request
# Visit GitHub and create PR
```

### 📜 贡献指南

- 🐛 [报告 Bug](https://github.com/Cyber-Security-Mcp-FrameWork/uplifted/issues/new?template=bug_report.md)
- 💡 [请求功能](https://github.com/Cyber-Security-Mcp-FrameWork/uplifted/issues/new?template=feature_request.md)
- 📖 [改进文档](./CONTRIBUTING.md)
- 🔧 [提交代码](./CONTRIBUTING.md)

完整贡献指南: [`CONTRIBUTING.md`](./CONTRIBUTING.md)

---

## 📊 项目状态

```
版本:        v1.0.0 (生产就绪)
状态:        🟢 活跃开发中
维护:        ✅ 是
安全:        🔒 已加固
```

### 🎯 路线图 - 从框架到生态系统

```
┌─────────────────────────────────────────────────────────────────┐
│  "今天的工具是明天的生态系统，                                   │
│   未来属于自主安全智能。"                                        │
└─────────────────────────────────────────────────────────────────┘
```

#### 🚀 阶段 1: 智能放大器 (2025 Q4)

**主题**: 让 AI Agent 更聪明、更易用、更强大

<table>
<tr><td width="50%">

**🎨 Web UI 与可视化编排**
```
┌──────────────────────────────┐
│  Drag & Drop Workflow Builder │
│  ┌─────┐  ┌─────┐  ┌─────┐  │
│  │Agent│─▶│Tool │─▶│ LLM │  │
│  └─────┘  └─────┘  └─────┘  │
│  Real-time Attack Tracking   │
└──────────────────────────────┘
```
- 可视化 Agent 攻击流设计器
- 实时攻击进度跟踪和日志查看
- Agent 攻击效率分析和优化建议
- 拖拽式创建复杂攻击链工作流

</td><td width="50%">

**🧠 记忆与上下文增强**
```python
# Agent 持久化记忆
agent.memory.save("target.com", {
    "subdomains": [...],
    "vulnerabilities": [...],
    "attack_surface": [...]
})

# 跨会话记忆
agent.recall("target.com")
# 自动恢复上次分析状态
```
- 长期记忆存储（Vector DB）
- 跨会话上下文恢复
- 自动知识图谱构建
- 历史经验学习和应用

</td></tr>
<tr><td width="50%">

**📊 高级分析与报告**
```python
import requests

# 生成高级分析报告
requests.post('http://localhost:7541/api/v1/reports/generate', json={
    "format": "pdf",
    "template": "executive",
    "agent_id": agent_id
})

# [*] Generating executive report...
# [*] Charts: ✓ Timeline: ✓
# [*] Risk matrix: ✓
# [*] Report: executive-2025-Q4.pdf
```
- 自动生成专业级安全报告
- 多种报告模板（技术/管理/合规）
- 数据可视化和趋势分析
- 导出多种格式（PDF/HTML/Markdown）

</td><td width="50%">

**🔧 工具市场与评分**
```
┌─────────────────────────┐
│ 🔥 Trending Tools       │
├─────────────────────────┤
│ ⭐⭐⭐⭐⭐ Advanced XSS  │
│ ⭐⭐⭐⭐☆ SQLI Pro      │
│ ⭐⭐⭐⭐⭐ Port Scanner  │
└─────────────────────────┘
```
- 社区驱动的工具市场
- 工具评分和评论系统
- 一键安装和更新机制
- 工具使用统计和推荐

</td></tr>
</table>

**核心目标**: 降低使用门槛，提升 Agent 智能水平，完善生态系统基础设施

---

#### 🧬 阶段 2: 自主进化 (2026 Q1)

**主题**: AI Agent 自主学习、进化和协作

<table>
<tr><td width="50%">

**🎯 强化学习引擎**
```python
# Agent 从实战中学习
trainer = RLTrainer(agent)
trainer.train_on_ctf()  # CTF 训练
trainer.train_on_bugbounty()  # 漏洞挖掘训练

# Agent 性能持续提升
agent.success_rate  # 45% → 78% → 92%
```
- 基于强化学习的攻击策略优化
- 从成功/失败案例中自动学习
- 动态调整工具选择和参数
- A/B 测试不同策略效果

</td><td width="50%">

**👥 多 Agent 协作**
```
    [Coordinator Agent]
           ↓
    ┌──────┼──────┐
    ↓      ↓      ↓
[Recon] [Scan] [Exploit]
    ↓      ↓      ↓
  Results Fusion & Decision
```
- 多 Agent 自动任务分配
- Agent 之间知识共享
- 协同决策和冲突解决
- 群体智能涌现

</td></tr>
<tr><td width="50%">

**🌐 分布式 Agent 网络**
```
Region 1 ────┐
             ├──→ Global Agent Pool
Region 2 ────┤
             └──→ Load Balancing
Region 3 ────┘
```
- 全球分布式 Agent 节点
- 智能负载均衡和调度
- 地理位置感知的任务分配
- 容错和自动恢复机制

</td><td width="50%">

**🔐 对抗性 Agent 训练**
```
[Red Agent]  vs  [Blue Agent]
     ↓              ↓
  Attack        Defense
     ↓              ↓
   Both agents learn and improve
```
- 红蓝对抗训练模式
- 攻防博弈自动进化
- 生成对抗性测试用例
- 提升 Agent 鲁棒性

</td></tr>
</table>

**核心目标**: 实现 Agent 自主学习和进化，构建协作式智能网络

---

#### 🏢 阶段 3: 企业级 (2026 Q2-Q3)

**主题**: 满足企业级需求的安全、合规和管理

<table>
<tr><td width="50%">

**🔒 企业安全与合规**
```python
import requests

# 合规检查
response = requests.post('http://localhost:7541/api/v1/compliance/check', json={
    "standard": "SOC2"
})
# [✓] Access Control
# [✓] Data Encryption
# [✓] Audit Logging
# [✓] 98% Compliant

# 自动生成审计报告
requests.post('http://localhost:7541/api/v1/audit/generate', json={
    "year": 2026
})
```
- SOC2/ISO27001/GDPR 合规检查
- 自动化审计日志收集
- 合规报告自动生成
- 风险评估和改进建议

</td><td width="50%">

**👥 多租户与 RBAC**
```
Organization A
  ├─ Team 1 (Admin)
  ├─ Team 2 (Analyst)
  └─ Team 3 (Read-only)

Organization B
  └─ Complete Isolation
```
- 企业级多租户架构
- 细粒度角色权限控制
- 资源配额和限流
- 租户数据完全隔离

</td></tr>
<tr><td width="50%">

**🔐 SSO 与身份联邦**
```
[LDAP] [SAML] [OAuth2] [OIDC]
            ↓
    Unified Auth Gateway
            ↓
    Uplifted Platform
```
- 主流 SSO 协议支持
- 与企业 IAM 系统集成
- MFA 多因素认证
- Session 管理和审计

</td><td width="50%">

**📈 平台监控与告警**
```
Metrics → Prometheus
         ↓
Alerts → PagerDuty/Slack
         ↓
Dashboard → Grafana
```
- 平台运行状态监控
- Agent 任务完成告警
- 与 Slack/Teams 集成通知
- 攻击任务执行报告

</td></tr>
</table>

**核心目标**: 满足大型企业的安全、合规和管理需求

---

#### ☁️ 阶段 4: 云原生与规模化 (2026 Q4)

**主题**: 云原生架构和全球规模化部署

<table>
<tr><td width="50%">

**☁️ Kubernetes 原生部署**
```yaml
# Helm 一键部署
$ helm install uplifted uplifted/chart
  --set replicas=10
  --set autoscaling.enabled=true

# 自动扩缩容
[*] Current load: 85%
[*] Scaling up: 10 → 25 pods
```
- K8s Operator 自动化运维
- Helm Charts 一键部署
- 水平自动扩缩容
- 滚动更新零停机

</td><td width="50%">

**🌍 全球 CDN 与边缘计算**
```
User (Tokyo) ──→ Edge Node (Tokyo)
                     ↓
User (London) ──→ Edge Node (London)
                     ↓
              Central Coordinator
```
- 全球边缘节点部署
- 就近访问低延迟
- 边缘计算减少带宽
- 智能路由和故障转移

</td></tr>
<tr><td width="50%">

**🔄 服务网格集成**
```
[Agent A] ─┐
           ├─ Istio Service Mesh
[Agent B] ─┤    • mTLS
           ├─   • Traffic Control
[Agent C] ─┘    • Observability
```
- Istio/Linkerd 服务网格
- 自动 mTLS 加密通信
- 流量管理和灰度发布
- 分布式追踪和可观测性

</td><td width="50%">

**💾 多云与混合部署**
```python
import requests

# 多云部署
requests.post('http://localhost:7541/api/v1/deployment/multi-cloud', json={
    "regions": {
        "aws": "us-east-1",
        "gcp": "asia-east1",
        "azure": "westeurope"
    }
})

# [✓] 3 regions deployed
```
- AWS/GCP/Azure 统一部署
- 混合云和私有云支持
- 跨云数据同步
- 灾难恢复和备份

</td></tr>
</table>

**核心目标**: 实现云原生架构，支持全球规模化部署

---

#### 🌌 阶段 5: 终极愿景 (2027+)

**主题**: 构建自主进化的全球安全智能网络

```
┌──────────────────────────────────────────────────────────────────┐
│              自主安全智能网络                                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🧠 集体智能                                                     │
│     ↳ 10,000+ Agent 节点的分布式攻击网络                        │
│     ↳ 实时漏洞情报共享和自动利用                                │
│     ↳ 全球协同的 0-day 挖掘和 Exploit 开发                      │
│                                                                  │
│  🔮 预测性利用                                                   │
│     ↳ 基于 AI 的攻击路径预测和自动化                            │
│     ↳ 0-day 漏洞自动发现和 Exploit 生成                         │
│     ↳ 攻击链优化和成功率预测                                    │
│                                                                  │
│  🤝 人机混合智能                                                 │
│     ↳ AI 作为渗透测试员的"智能助手"                             │
│     ↳ 自动执行 80% 的重复性测试任务                             │
│     ↳ 人类专注于 20% 的高级攻击和复杂利用                       │
│                                                                  │
│  🌍 开放攻击性安全公地                                           │
│     ↳ 全球最大的开源攻击知识库                                  │
│     ↳ 社区驱动的 Exploit 和工具生态                             │
│     ↳ 去中心化的漏洞情报网络                                    │
│                                                                  │
│  ⚡ 量子就绪架构                                                 │
│     ↳ 抗量子密码学算法集成                                      │
│     ↳ 量子计算加速的漏洞分析                                    │
│     ↳ 面向未来的安全架构                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**终极目标**:
- 让每个安全团队都能拥有 AI 渗透测试专家
- 让安全评估从手工测试变为自动化攻击链
- 让全球安全社区共同挖掘和利用漏洞
- 让人类和 AI 协同突破每一个防御边界

---

### 📊 开发时间线

```
2025 Q4: ████████████████░░░░  80% (Intelligence Amplifier)
2026 Q1: ████████░░░░░░░░░░░░  40% (Autonomous Evolution)
2026 Q2: ████░░░░░░░░░░░░░░░░  20% (Enterprise Grade - Part 1)
2026 Q3: ██░░░░░░░░░░░░░░░░░░  10% (Enterprise Grade - Part 2)
2026 Q4: ░░░░░░░░░░░░░░░░░░░░   0% (Cloud Native & Scale)
2027+  : ░░░░░░░░░░░░░░░░░░░░   0% (The Ultimate Vision)
```

### 🎯 如何贡献

每个阶段都需要社区的力量：

- **🔧 开发者**: 贡献新工具、插件和 Agent 算法
- **🎨 设计师**: 参与 UI/UX 设计和用户体验优化
- **📝 文档作者**: 完善文档、教程和最佳实践
- **🧪 测试者**: 参与测试、报告 Bug、提供反馈
- **🎓 教育者**: 创建培训材料和安全课程
- **💼 企业用户**: 提供真实需求和使用场景

> **这份路线图不仅仅是一个计划，更是一份承诺。**
>
> **我们不是在造一个工具，我们在创造一个能够改变网络安全行业的生态系统。**
>
> **加入我们。未来是自主的、智能的、安全的。**

### 📝 更新日志

查看完整更新日志: [`CHANGELOG.md`](./CHANGELOG.md)

---

## 🌟 社区

### 💬 获取帮助

- 📖 [文档](./docs/)
- 💬 [GitHub 讨论区](https://github.com/Cyber-Security-Mcp-FrameWork/uplifted/discussions)
- 🐛 [问题追踪](https://github.com/Cyber-Security-Mcp-FrameWork/uplifted/issues)
- 📧 [安全问题](mailto:security@uplifted.ai)

### 🎓 学习资源

- [`用户指南`](./server/docs/user_guide.md) - 用户完全指南
- [`开发者指南`](./server/docs/developer_guide.md) - 开发者文档
- [`API 参考`](./server/docs/api/) - API 完整参考
- [`示例`](./examples/) - 代码示例集

---

## 📄 许可证

本项目采用 [MIT 许可证](./LICENSE)。

```
MIT 许可证 - 简单来说:
✅ 商业使用
✅ 修改
✅ 分发
✅ 私人使用
❌ 责任
❌ 保证
```

---

## 🙏 致谢

感谢所有贡献者！

**技术驱动:**
- [Anthropic](https://www.anthropic.com/) - Claude AI
- [OpenAI](https://openai.com/) - GPT 模型
- [Google](https://deepmind.google/) - Gemini
- [MCP 社区](https://github.com/modelcontextprotocol) - 工具协议

---

<div align="center">

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  "最好的防御是由 AI 驱动的进攻。"                           │
│                                                            │
│              由黑客打造 💀 为黑客服务                        │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**[⬆ 返回顶部](#)**

[![GitHub Stars](https://img.shields.io/github/stars/Cyber-Security-Mcp-FrameWork/uplifted?style=social)](https://github.com/Cyber-Security-Mcp-FrameWork/uplifted)
[![Twitter Follow](https://img.shields.io/twitter/follow/uplifted_ai?style=social)](https://twitter.com/uplifted_ai)

</div>
