# Hello World Plugin

一个完整的示例插件，展示 Uplifted 插件系统的核心功能。

## 文件结构

```
hello_world/
├── manifest.json       # 插件清单（元数据）
├── __init__.py        # 插件主类
├── tools.py           # 工具实现
└── README.md          # 本文档
```

## 插件清单 (manifest.json)

插件清单是插件的核心配置文件，定义了：

### 基本信息
- **id**: `com.uplifted.examples.hello_world` - 唯一标识符
- **name**: `Hello World Plugin` - 显示名称
- **version**: `1.0.0` - 语义化版本号
- **description**: 插件描述
- **author**: 作者信息
- **license**: 许可证

### 工具定义
插件提供了两个工具：

#### 1. greet - 问候工具
```json
{
  "name": "greet",
  "description": "Say hello to a user",
  "input_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "language": {"type": "string", "default": "en"}
    },
    "required": ["name"]
  }
}
```

**使用示例**:
```python
result = greet(name="Alice")
# {'greeting': 'Hello, Alice!', 'language': 'en'}

result = greet(name="Bob", language="es")
# {'greeting': '¡Hola, Bob!', 'language': 'es'}
```

#### 2. echo - 回显工具
```json
{
  "name": "echo",
  "description": "Echo back the input message",
  "input_schema": {
    "type": "object",
    "properties": {
      "message": {"type": "string"}
    },
    "required": ["message"]
  }
}
```

**使用示例**:
```python
result = echo(message="Hello, World!")
# {'echo': 'Hello, World!'}
```

### 资源需求
```json
{
  "memory_mb": 64,
  "cpu_cores": 0.1,
  "disk_mb": 10,
  "network_required": false
}
```

### 配置
```json
{
  "config_schema": {
    "type": "object",
    "properties": {
      "default_language": {
        "type": "string",
        "enum": ["en", "es", "fr", "zh"]
      }
    }
  },
  "default_config": {
    "default_language": "en"
  }
}
```

## 插件实现 (__init__.py)

插件主类继承自 `Plugin` 基类，实现四个生命周期方法：

```python
class HelloWorldPlugin(Plugin):
    async def initialize(self) -> bool:
        """初始化插件"""
        # 读取配置
        default_lang = self.get_config_value('default_language', 'en')
        return True

    async def activate(self) -> bool:
        """激活插件，工具可以使用"""
        return True

    async def deactivate(self) -> bool:
        """停用插件"""
        return True

    async def cleanup(self) -> bool:
        """清理资源"""
        return True
```

## 工具实现 (tools.py)

工具函数是普通的 Python 函数：

```python
def greet(name: str, language: str = "en") -> Dict[str, Any]:
    """向用户问好"""
    greetings = {
        'en': f"Hello, {name}!",
        'es': f"¡Hola, {name}!",
        'fr': f"Bonjour, {name}!",
        'zh': f"你好，{name}！"
    }
    greeting = greetings.get(language, greetings['en'])
    return {'greeting': greeting, 'language': language}
```

## 安装和使用

### 1. 安装插件

将插件目录复制到 Uplifted 的插件目录：

```bash
cp -r hello_world ~/.uplifted/plugins/
```

或通过 CLI：

```bash
uplifted plugin install hello_world
```

### 2. 加载插件

插件会在启动时自动加载（如果 `auto_load: true`）。

手动加载：

```bash
uplifted plugin enable com.uplifted.examples.hello_world
```

### 3. 使用工具

通过 API 调用：

```bash
curl -X POST http://localhost:8085/api/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "greet Alice in Spanish",
    "tools": ["com.uplifted.examples.hello_world.greet"]
  }'
```

通过 Python：

```python
from uplifted import Agent

agent = Agent(plugins=["com.uplifted.examples.hello_world"])
result = agent.run("greet Bob in French")
print(result)
```

## 验证插件

验证插件清单：

```python
from uplifted.extensions.plugin_manifest import PluginManifest

manifest = PluginManifest.from_json_file("manifest.json")
errors = manifest.validate()

if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("✓ Manifest is valid")
```

## 开发自己的插件

### 步骤 1: 生成清单模板

```python
from uplifted.extensions.plugin_manifest import generate_manifest_template

manifest = generate_manifest_template(
    plugin_id="com.example.my_plugin",
    plugin_name="My Plugin",
    output_path="my_plugin/manifest.json"
)
```

### 步骤 2: 实现插件类

```python
from uplifted.extensions.plugin_manager import Plugin

class MyPlugin(Plugin):
    async def initialize(self) -> bool:
        # 初始化逻辑
        return True

    async def activate(self) -> bool:
        # 激活逻辑
        return True

    async def deactivate(self) -> bool:
        return True

    async def cleanup(self) -> bool:
        return True
```

### 步骤 3: 实现工具函数

```python
def my_tool(param1: str, param2: int = 0) -> dict:
    """工具描述"""
    # 工具逻辑
    return {"result": "..."}
```

### 步骤 4: 测试插件

```bash
# 验证清单
python -c "from uplifted.extensions.plugin_manifest import PluginManifest; \
           m = PluginManifest.from_json_file('manifest.json'); \
           print(m.validate())"

# 加载插件
uplifted plugin enable com.example.my_plugin

# 测试工具
uplifted tool list | grep my_plugin
```

## 最佳实践

1. **使用反向域名作为插件 ID**
   - ✅ `com.company.plugin_name`
   - ❌ `plugin_name`

2. **遵循语义化版本**
   - `1.0.0` - 主版本.次版本.修订版本

3. **编写完整的文档字符串**
   ```python
   def tool(param: str) -> dict:
       """
       工具描述

       参数:
           param: 参数说明

       返回:
           返回值说明
       """
   ```

4. **提供使用示例**
   - 在 manifest.json 的 tools.examples 中提供

5. **声明所需权限**
   - 明确声明需要的权限，如 `network.access`

6. **设置合理的资源限制**
   - 避免过度消耗系统资源

## 相关文档

- [插件开发指南](../../../docs/plugin-development.md)
- [API 参考](../../../docs/api-reference.md)
- [工具开发指南](../../../docs/tool-development.md)

## 支持

- GitHub Issues: https://github.com/uplifted/uplifted/issues
- 文档: https://uplifted.ai/docs
- 社区: https://discord.gg/uplifted
