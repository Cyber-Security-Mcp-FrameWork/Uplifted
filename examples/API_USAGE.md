# Plugin and Tool Management API Usage Guide

完整的 API 使用指南，展示如何查询和管理插件、工具。

## 目录

- [基础信息](#基础信息)
- [插件管理 API](#插件管理-api)
- [工具管理 API](#工具管理-api)
- [系统状态 API](#系统状态-api)
- [使用示例](#使用示例)

## 基础信息

**Base URL**: `http://localhost:7541`

**API 前缀**: `/api/v1`

**API 文档**: `http://localhost:7541/docs` (Swagger UI)

## 插件管理 API

### 1. 列出所有插件

获取系统中所有已注册的插件列表。

```http
GET /api/v1/plugins
```

**查询参数**:
- `status` (可选): 按状态过滤 (`active`, `loaded`, `inactive`, `error`)

**响应示例**:
```json
[
  {
    "name": "com.uplifted.examples.hello_world",
    "version": "1.0.0",
    "description": "Hello World example plugin",
    "author": "Uplifted Team",
    "status": "active",
    "dependencies": []
  }
]
```

**使用示例**:

```bash
# 获取所有插件
curl http://localhost:7541/api/v1/plugins

# 只获取激活的插件
curl http://localhost:7541/api/v1/plugins?status=active
```

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("http://localhost:7541/api/v1/plugins")
    plugins = response.json()
    print(f"Found {len(plugins)} plugins")
```

### 2. 获取插件详情

获取特定插件的详细信息。

```http
GET /api/v1/plugins/{plugin_id}
```

**路径参数**:
- `plugin_id`: 插件 ID（如 `com.uplifted.examples.hello_world`）

**响应示例**:
```json
{
  "name": "com.uplifted.examples.hello_world",
  "version": "1.0.0",
  "description": "Hello World example plugin",
  "author": "Uplifted Team",
  "status": "active",
  "dependencies": [],
  "config_schema": {
    "type": "object",
    "properties": {
      "default_language": {
        "type": "string",
        "enum": ["en", "es", "fr", "zh"]
      }
    }
  },
  "min_api_version": "1.0.0",
  "max_api_version": "2.0.0",
  "tools_count": 2
}
```

**使用示例**:

```bash
curl http://localhost:7541/api/v1/plugins/com.uplifted.examples.hello_world
```

```python
plugin_id = "com.uplifted.examples.hello_world"
response = await client.get(f"http://localhost:7541/api/v1/plugins/{plugin_id}")
plugin = response.json()
print(f"{plugin['name']} provides {plugin['tools_count']} tools")
```

### 3. 获取插件的工具列表

获取特定插件提供的所有工具。

```http
GET /api/v1/plugins/{plugin_id}/tools
```

**响应示例**:
```json
[
  "com.uplifted.examples.hello_world.greet",
  "com.uplifted.examples.hello_world.echo"
]
```

**使用示例**:

```bash
curl http://localhost:7541/api/v1/plugins/com.uplifted.examples.hello_world/tools
```

## 工具管理 API

### 4. 列出所有工具

获取系统中所有已注册的工具。

```http
GET /api/v1/tools
```

**查询参数**:
- `plugin_id` (可选): 按插件 ID 过滤
- `active_only` (可选, 默认 `true`): 只显示激活的工具

**响应示例**:
```json
[
  {
    "name": "com.uplifted.examples.hello_world.greet",
    "plugin_id": "com.uplifted.examples.hello_world",
    "description": "Say hello to a user",
    "input_schema": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "language": {"type": "string", "default": "en"}
      },
      "required": ["name"]
    },
    "registered_at": "2025-10-28T10:30:00",
    "active": true
  }
]
```

**使用示例**:

```bash
# 获取所有工具
curl http://localhost:7541/api/v1/tools

# 获取特定插件的工具
curl "http://localhost:7541/api/v1/tools?plugin_id=com.uplifted.examples.hello_world"

# 包括未激活的工具
curl "http://localhost:7541/api/v1/tools?active_only=false"
```

```python
# 获取所有工具
response = await client.get("http://localhost:7541/api/v1/tools")
tools = response.json()

for tool in tools:
    print(f"Tool: {tool['name']}")
    print(f"  Plugin: {tool['plugin_id']}")
    print(f"  Description: {tool['description']}")
```

### 5. 获取工具详情

获取特定工具的详细信息。

```http
GET /api/v1/tools/{tool_name}
```

**路径参数**:
- `tool_name`: 工具名称（全名或短名，如果唯一）

**响应示例**:
```json
{
  "name": "com.uplifted.examples.hello_world.greet",
  "plugin_id": "com.uplifted.examples.hello_world",
  "description": "Say hello to a user",
  "input_schema": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "language": {"type": "string", "default": "en"}
    },
    "required": ["name"]
  },
  "registered_at": "2025-10-28T10:30:00",
  "active": true,
  "entry_point": "hello_world.tools.greet",
  "mcp_command": "python",
  "mcp_args": ["-m", "hello_world.tools.greet"],
  "requires_approval": false
}
```

**使用示例**:

```bash
# 使用全名
curl http://localhost:7541/api/v1/tools/com.uplifted.examples.hello_world.greet

# 使用短名（如果唯一）
curl http://localhost:7541/api/v1/tools/greet
```

### 6. 查询工具来源

查询工具由哪个插件提供。

```http
GET /api/v1/tools/{tool_name}/source
```

**响应示例**:
```json
{
  "plugin_id": "com.uplifted.examples.hello_world",
  "tool_name": "com.uplifted.examples.hello_world.greet"
}
```

**使用示例**:

```bash
curl http://localhost:7541/api/v1/tools/greet/source
```

```python
response = await client.get("http://localhost:7541/api/v1/tools/greet/source")
source = response.json()
print(f"Tool 'greet' is provided by plugin: {source['plugin_id']}")
```

## 系统状态 API

### 7. 获取系统状态

获取插件系统的概览状态。

```http
GET /api/v1/system/status
```

**响应示例**:
```json
{
  "plugin_count": 5,
  "active_plugin_count": 3,
  "total_tools": 12,
  "active_tools": 10,
  "mcp_available": true
}
```

**使用示例**:

```bash
curl http://localhost:7541/api/v1/system/status
```

### 8. 获取详细统计

获取完整的系统统计信息，包括所有插件和工具的详细数据。

```http
GET /api/v1/system/statistics
```

**响应示例**:
```json
{
  "plugin_count": 5,
  "active_plugin_count": 3,
  "plugins": {
    "com.uplifted.examples.hello_world": {
      "status": "active",
      "version": "1.0.0",
      "description": "Hello World example plugin"
    }
  },
  "mcp_stats": {
    "total_tools": 12,
    "active_tools": 10,
    "total_plugins": 5,
    "tools_by_plugin": {
      "com.uplifted.examples.hello_world": 2
    }
  },
  "mcp_available": true
}
```

## 使用示例

### Python 异步客户端

```python
import httpx
import asyncio

async def explore_plugins():
    """探索所有插件和工具"""
    async with httpx.AsyncClient() as client:
        base_url = "http://localhost:7541/api/v1"

        # 1. 获取系统状态
        response = await client.get(f"{base_url}/system/status")
        status = response.json()
        print(f"System Status:")
        print(f"  Plugins: {status['active_plugin_count']}/{status['plugin_count']}")
        print(f"  Tools: {status['active_tools']}/{status['total_tools']}")

        # 2. 列出所有插件
        response = await client.get(f"{base_url}/plugins")
        plugins = response.json()

        for plugin in plugins:
            print(f"\nPlugin: {plugin['name']} v{plugin['version']}")

            # 3. 获取插件的工具
            response = await client.get(
                f"{base_url}/plugins/{plugin['name']}/tools"
            )
            tools = response.json()

            print(f"  Tools ({len(tools)}):")
            for tool_name in tools:
                # 4. 获取工具详情
                response = await client.get(f"{base_url}/tools/{tool_name}")
                tool = response.json()
                print(f"    - {tool['description']}")

# 运行
asyncio.run(explore_plugins())
```

### JavaScript/TypeScript 客户端

```typescript
import axios from 'axios';

const BASE_URL = 'http://localhost:7541/api/v1';

async function explorePlugins() {
  // 获取系统状态
  const statusResponse = await axios.get(`${BASE_URL}/system/status`);
  console.log('System Status:', statusResponse.data);

  // 获取所有插件
  const pluginsResponse = await axios.get(`${BASE_URL}/plugins`);
  const plugins = pluginsResponse.data;

  for (const plugin of plugins) {
    console.log(`\nPlugin: ${plugin.name} v${plugin.version}`);

    // 获取插件的工具
    const toolsResponse = await axios.get(
      `${BASE_URL}/plugins/${plugin.name}/tools`
    );
    const tools = toolsResponse.data;

    console.log(`  Tools (${tools.length}):`);
    for (const toolName of tools) {
      // 获取工具详情
      const toolResponse = await axios.get(`${BASE_URL}/tools/${toolName}`);
      console.log(`    - ${toolResponse.data.description}`);
    }
  }
}

explorePlugins();
```

### cURL 脚本

```bash
#!/bin/bash
# explore_plugins.sh - 探索所有插件和工具

BASE_URL="http://localhost:7541/api/v1"

echo "=== System Status ==="
curl -s "$BASE_URL/system/status" | jq

echo -e "\n=== All Plugins ==="
curl -s "$BASE_URL/plugins" | jq

echo -e "\n=== All Tools ==="
curl -s "$BASE_URL/tools" | jq

echo -e "\n=== Tools by Plugin ==="
for plugin_id in $(curl -s "$BASE_URL/plugins" | jq -r '.[].name'); do
  echo -e "\nPlugin: $plugin_id"
  curl -s "$BASE_URL/plugins/$plugin_id/tools" | jq
done
```

### 监控脚本

```python
import httpx
import asyncio
from datetime import datetime

async def monitor_plugin_system():
    """实时监控插件系统状态"""
    async with httpx.AsyncClient() as client:
        base_url = "http://localhost:7541/api/v1"

        while True:
            try:
                # 获取系统状态
                response = await client.get(f"{base_url}/system/status")
                status = response.json()

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"[{timestamp}] Status Check:")
                print(f"  Active Plugins: {status['active_plugin_count']}")
                print(f"  Active Tools: {status['active_tools']}")
                print(f"  MCP Available: {status['mcp_available']}")

                # 检查是否有错误状态的插件
                response = await client.get(f"{base_url}/plugins?status=error")
                error_plugins = response.json()

                if error_plugins:
                    print(f"  ⚠️  {len(error_plugins)} plugins in ERROR state!")
                    for plugin in error_plugins:
                        print(f"    - {plugin['name']}")

            except Exception as e:
                print(f"  ✗ Monitoring error: {e}")

            # 每 30 秒检查一次
            await asyncio.sleep(30)

# 运行监控
asyncio.run(monitor_plugin_system())
```

## 错误处理

所有 API 端点遵循标准 HTTP 状态码：

- `200 OK`: 请求成功
- `404 Not Found`: 插件/工具未找到
- `500 Internal Server Error`: 服务器错误
- `503 Service Unavailable`: MCP 桥接器不可用

**错误响应示例**:
```json
{
  "detail": "Plugin com.example.nonexistent not found"
}
```

## 最佳实践

1. **使用工具的全名**，避免歧义（虽然短名在唯一时也支持）
2. **定期检查系统状态**，监控插件和工具的健康状态
3. **错误处理**：始终处理 `404` 和 `503` 错误
4. **批量查询**：先获取列表，再根据需要查询详情
5. **缓存**：插件信息相对稳定，可以适当缓存

## 相关文档

- [插件开发指南](../examples/plugins/hello_world/README.md)
- [服务器启动示例](./server_with_plugins.py)
- [API 架构文档](../server/uplifted/server/plugins_api.py)
