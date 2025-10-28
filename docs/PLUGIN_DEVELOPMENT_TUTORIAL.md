# Uplifted 插件开发完整教程

本教程将从零开始，逐步引导您开发一个完整的 Uplifted 插件。

## 目录

- [前提条件](#前提条件)
- [插件基础概念](#插件基础概念)
- [快速开始：第一个插件](#快速开始第一个插件)
- [插件元数据和清单](#插件元数据和清单)
- [开发工具](#开发工具)
- [配置管理](#配置管理)
- [测试和调试](#测试和调试)
- [高级功能](#高级功能)
- [最佳实践](#最佳实践)
- [常见问题](#常见问题)
- [参考资料](#参考资料)

---

## 前提条件

在开始之前，请确保您具备以下条件：

### 必需

- **Python 3.10+**
- **Uplifted 已安装**
- 基本的 Python 编程知识
- 对 MCP (Model Context Protocol) 的基本了解（可选但推荐）

### 推荐

- Git 版本控制
- 虚拟环境管理（venv 或 conda）
- 代码编辑器（VS Code, PyCharm 等）

### 安装 Uplifted

```bash
# 克隆仓库
git clone https://github.com/uplifted/uplifted.git
cd uplifted

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install uv
uv pip install -e .
```

---

## 插件基础概念

### 什么是插件？

**插件 (Plugin)** 是 Uplifted 系统的扩展模块，用于：

- 添加新的功能和工具
- 集成外部服务
- 提供安全扫描、渗透测试等专业工具
- 自定义系统行为

### 插件架构

```
Uplifted 核心
    ↓
插件管理器 (PluginManager)
    ↓
MCP 桥接器 (MCPPluginBridge)
    ↓
具体插件 (Your Plugin)
    ↓
工具 (Tools)
```

### 核心组件

1. **PluginManifest**: 插件元数据定义
2. **PluginManager**: 插件生命周期管理
3. **MCPPluginBridge**: 插件到 MCP 工具的桥接
4. **ToolDefinition**: 工具定义标准

### 插件生命周期

```
未加载 → 已加载 → 已激活 → 已停用 → 已卸载
```

---

## 快速开始：第一个插件

让我们创建一个简单的"Hello World"插件。

### Step 1: 创建插件目录

```bash
# 在 plugins 目录下创建新插件
cd plugins
mkdir my_first_plugin
cd my_first_plugin
```

### Step 2: 创建插件清单

创建 `manifest.yaml`:

```yaml
# manifest.yaml
name: my_first_plugin
version: "1.0.0"
description: "我的第一个 Uplifted 插件"
author: "Your Name"
author_email: "your.email@example.com"
license: "MIT"
homepage: "https://github.com/yourname/my_first_plugin"

# API 版本兼容性
min_api_version: "1.0.0"
max_api_version: "2.0.0"

# 依赖（如果需要）
dependencies: []

# 插件入口
entry_point: "main.py"

# 提供的工具
tools:
  - name: "greet"
    description: "向用户问好"
    version: "1.0.0"
    author: "Your Name"

    # MCP 配置
    mcp_config:
      command: "python"
      args:
        - "tools/greet.py"

    # 输入参数 schema
    input_schema:
      type: "object"
      properties:
        name:
          type: "string"
          description: "要问候的名字"
          default: "World"
      required: []

    # 元数据
    metadata:
      category: "utility"
      tags: ["greeting", "example"]
      requires_approval: false
```

### Step 3: 创建插件主文件

创建 `main.py`:

```python
"""
我的第一个 Uplifted 插件

这是一个简单的示例插件，展示基本的插件结构。
"""

import logging
from typing import Dict, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)


class MyFirstPlugin:
    """插件主类"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化插件

        Args:
            config: 插件配置（来自 config.yaml 或 API）
        """
        self.config = config or {}
        self.name = "my_first_plugin"
        self.version = "1.0.0"

        logger.info(f"{self.name} v{self.version} 初始化")

    def activate(self) -> None:
        """
        激活插件

        在插件被激活时调用。可以在这里执行初始化任务：
        - 建立数据库连接
        - 加载模型
        - 初始化外部服务连接
        """
        logger.info(f"{self.name} 已激活")
        # 你的初始化代码...

    def deactivate(self) -> None:
        """
        停用插件

        在插件被停用时调用。应该清理资源：
        - 关闭数据库连接
        - 释放内存
        - 保存状态
        """
        logger.info(f"{self.name} 已停用")
        # 你的清理代码...

    def get_status(self) -> Dict[str, Any]:
        """
        获取插件状态

        Returns:
            包含状态信息的字典
        """
        return {
            "name": self.name,
            "version": self.version,
            "active": True,
            "config": self.config
        }


# 插件工厂函数（必需）
def create_plugin(config: Optional[Dict[str, Any]] = None):
    """
    创建插件实例

    这是插件管理器调用的工厂函数。

    Args:
        config: 插件配置

    Returns:
        插件实例
    """
    return MyFirstPlugin(config)
```

### Step 4: 创建工具脚本

创建 `tools/greet.py`:

```python
#!/usr/bin/env python3
"""
Greet 工具

向用户问好的简单工具。
"""

import json
import sys


def greet(name: str = "World") -> dict:
    """
    向指定的名字问好

    Args:
        name: 要问候的名字

    Returns:
        问候消息
    """
    message = f"Hello, {name}! Welcome to Uplifted!"
    return {
        "message": message,
        "success": True
    }


def main():
    """
    MCP 工具入口点

    从 stdin 读取 JSON 输入，执行工具，输出 JSON 结果。
    """
    try:
        # 读取输入
        input_data = json.load(sys.stdin)

        # 提取参数
        name = input_data.get("name", "World")

        # 执行工具
        result = greet(name)

        # 输出结果
        json.dump(result, sys.stdout)
        sys.stdout.flush()

    except Exception as e:
        # 错误处理
        error_result = {
            "success": False,
            "error": str(e)
        }
        json.dump(error_result, sys.stdout)
        sys.stdout.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 5: 添加配置文件（可选）

创建 `config.yaml`:

```yaml
# 插件配置
greeting_prefix: "Hello"
default_name: "World"
enable_logging: true
```

### Step 6: 测试插件

创建测试脚本 `test_plugin.py`:

```python
"""测试插件"""

import sys
sys.path.insert(0, '../..')  # 添加 Uplifted 到路径

from server.uplifted.extensions import get_global_plugin_manager
from server.uplifted.extensions.plugin_manifest import PluginManifest


def test_plugin():
    """测试插件加载和激活"""

    # 获取插件管理器
    manager = get_global_plugin_manager()

    # 加载插件清单
    manifest = PluginManifest.from_yaml_file("manifest.yaml")
    print(f"✓ 插件清单加载成功: {manifest.name}")

    # 加载插件
    manager.load_plugin("my_first_plugin", ".")
    print(f"✓ 插件已加载")

    # 激活插件
    manager.activate_plugin("my_first_plugin")
    print(f"✓ 插件已激活")

    # 获取状态
    status = manager.get_plugin_status("my_first_plugin")
    print(f"✓ 插件状态: {status}")

    # 测试工具
    from server.uplifted.extensions import get_global_mcp_bridge
    bridge = get_global_mcp_bridge()

    tools = bridge.list_tools()
    print(f"✓ 注册的工具: {tools}")

    print("\n✅ 所有测试通过！")


if __name__ == "__main__":
    test_plugin()
```

运行测试：

```bash
python test_plugin.py
```

### Step 7: 插件目录结构

最终的插件目录结构应该如下：

```
my_first_plugin/
├── manifest.yaml        # 插件清单（必需）
├── main.py              # 插件主文件（必需）
├── config.yaml          # 配置文件（可选）
├── test_plugin.py       # 测试脚本
├── tools/               # 工具目录
│   └── greet.py         # Greet 工具
├── README.md            # 插件文档（推荐）
└── requirements.txt     # Python 依赖（如果需要）
```

---

## 插件元数据和清单

### PluginManifest 详解

`manifest.yaml` 是插件的核心配置文件，定义了插件的所有元数据。

#### 基本信息

```yaml
name: "my_plugin"          # 插件唯一标识符（必需）
version: "1.0.0"            # 版本号，遵循 SemVer（必需）
description: "插件描述"     # 简短描述（推荐）
author: "Your Name"         # 作者名称（推荐）
author_email: "email@example.com"  # 作者邮箱（可选）
license: "MIT"              # 许可证（推荐）
homepage: "https://..."     # 主页 URL（可选）
repository: "https://github.com/..."  # 代码仓库（可选）
```

#### 版本兼容性

```yaml
min_api_version: "1.0.0"    # 最小兼容的 Uplifted API 版本
max_api_version: "2.0.0"    # 最大兼容的 Uplifted API 版本
```

#### 依赖管理

```yaml
dependencies:
  - name: "base_plugin"     # 依赖的其他插件
    version: ">=1.0.0"       # 版本约束（可选）
  - name: "security_lib"
    version: "~=2.0"
```

#### 入口点

```yaml
entry_point: "main.py"      # 插件主文件路径
```

#### 工具定义

```yaml
tools:
  - name: "tool_name"                    # 工具名称（在插件内唯一）
    description: "工具描述"              # 工具功能说明
    version: "1.0.0"                     # 工具版本
    author: "Tool Author"                # 工具作者

    # MCP 配置
    mcp_config:
      command: "python"                  # 执行命令
      args:                              # 命令参数
        - "tools/tool_script.py"
      env:                               # 环境变量（可选）
        TOOL_DEBUG: "true"

    # 输入参数 Schema (JSON Schema 格式)
    input_schema:
      type: "object"
      properties:
        param1:
          type: "string"
          description: "参数1说明"
          default: "默认值"
        param2:
          type: "integer"
          description: "参数2说明"
          minimum: 0
          maximum: 100
      required: ["param1"]              # 必需参数列表

    # 工具元数据
    metadata:
      category: "security"               # 分类
      tags: ["scan", "network"]          # 标签
      requires_approval: true            # 是否需要审批
      timeout: 300                       # 超时时间（秒）
      priority: 1                        # 优先级
```

#### 配置 Schema

```yaml
config_schema:
  type: "object"
  properties:
    api_key:
      type: "string"
      description: "API 密钥"
      secret: true                       # 标记为敏感信息
    max_retries:
      type: "integer"
      description: "最大重试次数"
      default: 3
      minimum: 0
      maximum: 10
    enable_cache:
      type: "boolean"
      description: "启用缓存"
      default: true
  required: ["api_key"]
```

### 验证清单

使用以下代码验证 manifest.yaml：

```python
from server.uplifted.extensions.plugin_manifest import PluginManifest

# 加载并验证
manifest = PluginManifest.from_yaml_file("manifest.yaml")

# 验证
validation_result = manifest.validate()
if validation_result["valid"]:
    print("✓ 清单有效")
else:
    print(f"✗ 验证失败: {validation_result['errors']}")
```

---

## 开发工具

### 创建复杂工具

#### 示例：端口扫描工具

```python
# tools/port_scanner.py
#!/usr/bin/env python3
"""端口扫描工具"""

import json
import sys
import socket
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict


def scan_port(host: str, port: int, timeout: int = 1) -> Dict[str, any]:
    """
    扫描单个端口

    Args:
        host: 目标主机
        port: 端口号
        timeout: 超时时间

    Returns:
        扫描结果
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            # 尝试获取服务横幅
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                sock.connect((host, port))
                banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
                sock.close()
            except:
                banner = None

            return {
                "port": port,
                "status": "open",
                "banner": banner
            }
        else:
            return {
                "port": port,
                "status": "closed"
            }
    except Exception as e:
        return {
            "port": port,
            "status": "error",
            "error": str(e)
        }


def scan_ports(host: str, ports: List[int], workers: int = 10) -> List[Dict]:
    """
    并发扫描多个端口

    Args:
        host: 目标主机
        ports: 端口列表
        workers: 并发线程数

    Returns:
        扫描结果列表
    """
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(scan_port, host, port) for port in ports]
        for future in futures:
            results.append(future.result())

    return results


def main():
    """MCP 工具入口"""
    try:
        # 读取输入
        input_data = json.load(sys.stdin)

        # 提取参数
        host = input_data["host"]
        ports = input_data.get("ports", list(range(1, 1025)))
        workers = input_data.get("workers", 10)

        # 执行扫描
        results = scan_ports(host, ports, workers)

        # 统计
        open_ports = [r for r in results if r["status"] == "open"]

        # 输出结果
        output = {
            "success": True,
            "host": host,
            "total_scanned": len(results),
            "open_ports_count": len(open_ports),
            "open_ports": open_ports,
            "all_results": results
        }

        json.dump(output, sys.stdout)
        sys.stdout.flush()

    except KeyError as e:
        json.dump({
            "success": False,
            "error": f"缺少必需参数: {e}"
        }, sys.stdout)
        sys.exit(1)
    except Exception as e:
        json.dump({
            "success": False,
            "error": str(e)
        }, sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

对应的 manifest.yaml 工具定义：

```yaml
tools:
  - name: "port_scanner"
    description: "TCP 端口扫描工具"
    version: "1.0.0"

    mcp_config:
      command: "python"
      args:
        - "tools/port_scanner.py"

    input_schema:
      type: "object"
      properties:
        host:
          type: "string"
          description: "目标主机 IP 或域名"
        ports:
          type: "array"
          description: "要扫描的端口列表"
          items:
            type: "integer"
            minimum: 1
            maximum: 65535
          default: [21, 22, 23, 25, 80, 443, 3306, 3389, 8080]
        workers:
          type: "integer"
          description: "并发线程数"
          default: 10
          minimum: 1
          maximum: 100
      required: ["host"]

    metadata:
      category: "network"
      tags: ["scanning", "network", "reconnaissance"]
      requires_approval: true
      timeout: 300
```

---

## 配置管理

### 读取配置

插件可以通过多种方式读取配置：

#### 方式 1: 从文件读取

```python
import yaml

class MyPlugin:
    def __init__(self, config=None):
        # 从 config.yaml 读取
        with open("config.yaml", "r") as f:
            self.file_config = yaml.safe_load(f)

        # 合并外部配置
        self.config = {**self.file_config, **(config or {})}
```

#### 方式 2: 使用 Uplifted 配置管理器

```python
from server.uplifted.extensions import get_global_config_manager

class MyPlugin:
    def __init__(self, config=None):
        # 获取全局配置管理器
        config_manager = get_global_config_manager()

        # 读取插件配置
        self.config = config_manager.get(f"plugins.{self.name}", default={})

        # 合并传入的配置
        if config:
            self.config.update(config)
```

#### 方式 3: 环境变量

```python
import os

class MyPlugin:
    def __init__(self, config=None):
        self.config = config or {}

        # 从环境变量读取
        self.api_key = os.getenv("MY_PLUGIN_API_KEY", self.config.get("api_key"))
        self.timeout = int(os.getenv("MY_PLUGIN_TIMEOUT", self.config.get("timeout", 30)))
```

### 加密敏感配置

```python
from server.uplifted.extensions.config_loaders import EncryptedConfigLoader

# 加载加密配置
encrypted_loader = EncryptedConfigLoader("encryption.key")
config = encrypted_loader.load("encrypted_config.enc")

# 获取敏感信息
api_key = config.get("api_key")
```

---

## 测试和调试

### 单元测试

创建 `tests/test_greet.py`:

```python
import unittest
import json
import subprocess


class TestGreetTool(unittest.TestCase):
    """测试 Greet 工具"""

    def test_greet_default(self):
        """测试默认问候"""
        input_data = {}
        result = self._run_tool(input_data)

        self.assertTrue(result["success"])
        self.assertIn("World", result["message"])

    def test_greet_custom_name(self):
        """测试自定义名字"""
        input_data = {"name": "Alice"}
        result = self._run_tool(input_data)

        self.assertTrue(result["success"])
        self.assertIn("Alice", result["message"])

    def _run_tool(self, input_data):
        """运行工具并返回结果"""
        process = subprocess.Popen(
            ["python", "../tools/greet.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        stdout, stderr = process.communicate(
            input=json.dumps(input_data).encode()
        )

        return json.loads(stdout)


if __name__ == "__main__":
    unittest.main()
```

运行测试：

```bash
python -m unittest discover tests
```

### 集成测试

创建 `tests/test_integration.py`:

```python
import sys
sys.path.insert(0, '../..')

from server.uplifted.extensions import (
    get_global_plugin_manager,
    get_global_mcp_bridge
)


def test_plugin_integration():
    """测试插件集成"""

    # 1. 加载插件
    manager = get_global_plugin_manager()
    manager.load_plugin("my_first_plugin", "..")
    assert "my_first_plugin" in manager.list_plugins()

    # 2. 激活插件
    manager.activate_plugin("my_first_plugin")
    status = manager.get_plugin_status("my_first_plugin")
    assert status == "active"

    # 3. 检查工具注册
    bridge = get_global_mcp_bridge()
    tools = bridge.list_tools()
    assert "my_first_plugin.greet" in tools

    # 4. 测试工具元数据
    tool_info = bridge.get_tool_info("my_first_plugin.greet")
    assert tool_info is not None
    assert "input_schema" in tool_info

    print("✅ 集成测试通过")


if __name__ == "__main__":
    test_plugin_integration()
```

### 调试技巧

#### 1. 启用日志

```python
import logging

# 在插件代码中
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告")
logger.error("错误")
```

#### 2. 使用调试器

```python
# 在需要调试的地方插入断点
import pdb; pdb.set_trace()

# 或使用 IPython
import IPython; IPython.embed()
```

#### 3. 工具测试脚本

创建 `debug_tool.py`:

```python
import json
import subprocess


def test_tool_manually():
    """手动测试工具"""

    # 准备输入
    input_data = {
        "name": "Test User"
    }

    # 运行工具
    process = subprocess.Popen(
        ["python", "tools/greet.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = process.communicate(
        input=json.dumps(input_data).encode()
    )

    # 打印结果
    print("=== STDOUT ===")
    print(stdout.decode())

    print("\n=== STDERR ===")
    print(stderr.decode())

    print("\n=== Exit Code ===")
    print(process.returncode)


if __name__ == "__main__":
    test_tool_manually()
```

---

## 高级功能

### 异步工具

使用异步 Python 处理并发：

```python
# tools/async_scanner.py
import asyncio
import json
import sys


async def async_scan(target: str) -> dict:
    """异步扫描"""
    await asyncio.sleep(1)  # 模拟异步操作
    return {"target": target, "result": "scanned"}


async def main_async():
    """异步主函数"""
    try:
        input_data = json.load(sys.stdin)
        targets = input_data.get("targets", [])

        # 并发扫描所有目标
        results = await asyncio.gather(
            *[async_scan(target) for target in targets]
        )

        json.dump({
            "success": True,
            "results": results
        }, sys.stdout)

    except Exception as e:
        json.dump({
            "success": False,
            "error": str(e)
        }, sys.stdout)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main_async())
```

### 状态持久化

```python
import json
from pathlib import Path


class StatefulPlugin:
    """带状态持久化的插件"""

    def __init__(self, config=None):
        self.config = config or {}
        self.state_file = Path("plugin_state.json")
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """加载状态"""
        if self.state_file.exists():
            with open(self.state_file, "r") as f:
                return json.load(f)
        return {}

    def _save_state(self):
        """保存状态"""
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def update_state(self, key: str, value):
        """更新状态"""
        self.state[key] = value
        self._save_state()

    def get_state(self, key: str, default=None):
        """获取状态"""
        return self.state.get(key, default)
```

### 插件间通信

```python
from server.uplifted.extensions import get_global_plugin_manager


class CommunicatingPlugin:
    """支持插件间通信的插件"""

    def __init__(self, config=None):
        self.config = config or {}
        self.manager = get_global_plugin_manager()

    def call_other_plugin(self, plugin_name: str, method: str, *args, **kwargs):
        """调用其他插件的方法"""

        # 获取其他插件实例
        other_plugin = self.manager.get_plugin_instance(plugin_name)

        if other_plugin is None:
            raise ValueError(f"插件 {plugin_name} 不存在或未激活")

        # 调用方法
        if hasattr(other_plugin, method):
            return getattr(other_plugin, method)(*args, **kwargs)
        else:
            raise AttributeError(f"插件 {plugin_name} 没有方法 {method}")
```

### 事件系统

```python
from typing import Callable, Dict, List


class EventEmitter:
    """简单的事件发射器"""

    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}

    def on(self, event: str, callback: Callable):
        """注册事件监听器"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)

    def emit(self, event: str, *args, **kwargs):
        """触发事件"""
        if event in self._listeners:
            for callback in self._listeners[event]:
                callback(*args, **kwargs)


class EventDrivenPlugin(EventEmitter):
    """事件驱动的插件"""

    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}

    def activate(self):
        """激活时触发事件"""
        self.emit("activated", plugin=self)

    def on_scan_complete(self, callback: Callable):
        """注册扫描完成事件"""
        self.on("scan_complete", callback)

    def perform_scan(self, target: str):
        """执行扫描并触发事件"""
        # 扫描逻辑...
        result = {"target": target, "status": "success"}

        # 触发事件
        self.emit("scan_complete", result)

        return result
```

---

## 最佳实践

### 1. 代码组织

**推荐的插件结构**:

```
my_plugin/
├── manifest.yaml           # 插件清单
├── main.py                 # 插件主类
├── config.yaml             # 配置文件
├── README.md               # 文档
├── requirements.txt        # Python 依赖
├── LICENSE                 # 许可证
├── .gitignore              # Git 忽略
│
├── tools/                  # 工具目录
│   ├── __init__.py
│   ├── tool1.py
│   └── tool2.py
│
├── lib/                    # 共享库
│   ├── __init__.py
│   ├── utils.py
│   └── models.py
│
└── tests/                  # 测试
    ├── __init__.py
    ├── test_plugin.py
    └── test_tools.py
```

### 2. 错误处理

**始终处理异常**:

```python
def safe_operation():
    """安全的操作示例"""
    try:
        # 危险操作
        result = risky_function()
        return {"success": True, "data": result}

    except ValueError as e:
        logger.error(f"值错误: {e}")
        return {"success": False, "error": f"Invalid value: {e}"}

    except ConnectionError as e:
        logger.error(f"连接错误: {e}")
        return {"success": False, "error": f"Connection failed: {e}"}

    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        return {"success": False, "error": f"Unexpected error: {e}"}
```

### 3. 参数验证

```python
from typing import Any, Dict


def validate_input(data: Dict[str, Any], schema: Dict[str, Any]) -> tuple[bool, str]:
    """
    验证输入参数

    Args:
        data: 输入数据
        schema: JSON Schema

    Returns:
        (是否有效, 错误消息)
    """
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    # 检查必需参数
    for field in required:
        if field not in data:
            return False, f"缺少必需参数: {field}"

    # 检查类型
    for field, value in data.items():
        if field in properties:
            expected_type = properties[field].get("type")
            if expected_type == "string" and not isinstance(value, str):
                return False, f"参数 {field} 应该是字符串"
            elif expected_type == "integer" and not isinstance(value, int):
                return False, f"参数 {field} 应该是整数"
            # ... 更多类型检查

    return True, ""
```

### 4. 日志记录

```python
import logging

# 配置日志
logger = logging.getLogger(__name__)


class WellLoggedPlugin:
    """良好日志记录的插件"""

    def activate(self):
        logger.info("插件激活")
        logger.debug("激活详情: ...")

    def perform_task(self, task_id: str):
        logger.info(f"开始任务: {task_id}")

        try:
            result = self._do_task(task_id)
            logger.info(f"任务完成: {task_id}")
            return result

        except Exception as e:
            logger.exception(f"任务失败: {task_id}")
            raise
```

### 5. 文档字符串

```python
def complex_function(param1: str, param2: int = 10) -> dict:
    """
    执行复杂操作

    这个函数执行一个复杂的操作，涉及多个步骤...

    Args:
        param1: 第一个参数，应该是有效的字符串
        param2: 第二个参数，默认为 10

    Returns:
        包含结果的字典:
        {
            "success": bool,
            "result": Any,
            "message": str
        }

    Raises:
        ValueError: 如果 param1 无效
        ConnectionError: 如果无法连接到服务

    Example:
        >>> result = complex_function("test", param2=20)
        >>> print(result["success"])
        True
    """
    pass
```

### 6. 版本管理

遵循 **Semantic Versioning (SemVer)**:

- `MAJOR.MINOR.PATCH`
- `MAJOR`: 不兼容的 API 变更
- `MINOR`: 向后兼容的功能新增
- `PATCH`: 向后兼容的 bug 修复

### 7. 安全性

- **永远不要**在代码中硬编码敏感信息
- 使用环境变量或加密配置存储密钥
- 验证所有外部输入
- 限制文件系统访问
- 使用最小权限原则

```python
import os

# ✓ 好的做法
api_key = os.getenv("API_KEY")

# ✗ 不好的做法
api_key = "sk-1234567890abcdef"  # 永远不要这样做！
```

### 8. 性能优化

- 使用缓存减少重复计算
- 异步处理 I/O 密集型操作
- 限制并发数量
- 及时释放资源

```python
from functools import lru_cache


class OptimizedPlugin:

    @lru_cache(maxsize=128)
    def expensive_operation(self, param: str) -> str:
        """使用缓存的昂贵操作"""
        # 复杂计算...
        return result
```

---

## 常见问题

### Q1: 如何调试工具不工作？

**A**:
1. 检查 manifest.yaml 中的 mcp_config
2. 手动运行工具脚本测试输入/输出
3. 查看日志文件
4. 使用 `debug_tool.py` 脚本测试

### Q2: 插件加载失败怎么办？

**A**:
1. 验证 manifest.yaml 格式
2. 检查 entry_point 路径是否正确
3. 确保所有依赖已安装
4. 查看错误日志获取详细信息

### Q3: 如何处理插件依赖？

**A**:
- 在 manifest.yaml 中声明插件依赖
- 在 requirements.txt 中列出 Python 包依赖
- 使用虚拟环境隔离依赖

### Q4: 工具超时怎么办？

**A**:
- 在 metadata 中增加 timeout 值
- 优化工具性能
- 使用异步操作
- 分批处理大量数据

### Q5: 如何发布插件？

**A**:
1. 创建 GitHub 仓库
2. 添加完整的 README
3. 包含示例和文档
4. 发布到 Uplifted 插件市场（未来功能）

---

## 参考资料

### 官方文档

- [Uplifted 官方文档](https://uplifted.ai/docs)
- [配置管理指南](./CONFIG_MANAGEMENT.md)
- [部署指南](./DEPLOYMENT.md)
- [API 使用指南](../examples/API_USAGE.md)

### 代码示例

- [Hello World 插件](../examples/plugins/hello_world/)
- [配置管理示例](../examples/config_management_example.py)
- [服务器集成示例](../examples/server_with_plugins.py)

### 外部资源

- [MCP 协议规范](https://modelcontextprotocol.io)
- [JSON Schema](https://json-schema.org/)
- [Python 异步编程](https://docs.python.org/3/library/asyncio.html)
- [SemVer 规范](https://semver.org/)

### 社区

- GitHub: https://github.com/uplifted/uplifted
- Issues: https://github.com/uplifted/uplifted/issues
- 文档: https://uplifted.ai/docs

---

**最后更新**: 2025-10-28
**版本**: 1.0.0

如有问题，欢迎提交 Issue 或参与社区讨论！
