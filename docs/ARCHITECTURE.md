# Uplifted 架构文档

本文档详细描述了 Uplifted 的系统架构、设计决策和核心组件。

## 目录

- [架构概览](#架构概览)
- [分层架构](#分层架构)
- [核心模块](#核心模块)
- [数据流](#数据流)
- [设计决策](#设计决策)
- [扩展性](#扩展性)
- [安全性](#安全性)
- [性能考虑](#性能考虑)
- [未来规划](#未来规划)

---

## 架构概览

Uplifted 采用**分层模块化架构**，将系统划分为清晰的职责层次，每层通过定义良好的接口进行通信。

### 整体架构图

```
┌──────────────────────────────────────────────────────────────┐
│                      客户端层 (Client Layer)                    │
│  - Web UI / CLI / SDK / API Clients                          │
└──────────────────────────────────────────────────────────────┘
                           ↓ HTTP/REST API
┌──────────────────────────────────────────────────────────────┐
│                   API 网关层 (API Gateway Layer)               │
│  - FastAPI Application                                        │
│  - OpenAPI Documentation                                      │
│  - Request Validation                                         │
│  - Rate Limiting                                              │
│  - Authentication & Authorization                             │
└──────────────────────────────────────────────────────────────┘
                           ↓ Internal APIs
┌──────────────────────────────────────────────────────────────┐
│                  服务管理层 (Service Layer)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Plugin API  │  │   Tools API  │  │  System API  │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└──────────────────────────────────────────────────────────────┘
                           ↓ Service Calls
┌──────────────────────────────────────────────────────────────┐
│                 核心业务层 (Core Business Layer)                │
│  ┌──────────────────┐      ┌──────────────────┐              │
│  │ Plugin Manager   │◄────►│  MCP Bridge      │              │
│  └──────────────────┘      └──────────────────┘              │
│  ┌──────────────────┐      ┌──────────────────┐              │
│  │  Config Manager  │      │  Tool Registry   │              │
│  └──────────────────┘      └──────────────────┘              │
└──────────────────────────────────────────────────────────────┘
                           ↓ Data Access
┌──────────────────────────────────────────────────────────────┐
│                  数据访问层 (Data Access Layer)                 │
│  ┌──────────────────┐      ┌──────────────────┐              │
│  │  File Storage    │      │   Database       │              │
│  │  (Plugins, Logs) │      │ (SQLite/Postgres)│              │
│  └──────────────────┘      └──────────────────┘              │
└──────────────────────────────────────────────────────────────┘
                           ↓ External Calls
┌──────────────────────────────────────────────────────────────┐
│                   外部集成层 (External Layer)                   │
│  - AI Providers (OpenAI, Anthropic, etc.)                    │
│  - MCP Tools (External Processes)                            │
│  - External APIs                                             │
└──────────────────────────────────────────────────────────────┘
```

### 关键特性

- **模块化**: 每个组件都是独立的，可以单独测试和替换
- **可扩展**: 通过插件系统轻松扩展功能
- **解耦**: 层之间通过接口通信，减少依赖
- **可测试**: 每层都可以独立测试
- **可维护**: 清晰的职责划分

---

## 分层架构

### 1. 客户端层 (Client Layer)

**职责**: 为用户提供交互界面

**组件**:
- Web UI (未来)
- CLI 工具
- Python SDK
- REST API 客户端

**技术栈**:
- Python (CLI/SDK)
- JavaScript/TypeScript (Web UI - 计划中)

**示例交互**:

```python
# Python SDK 示例
from uplifted import Client

client = Client(api_key="your-key")

# 列出插件
plugins = client.plugins.list()

# 激活插件
client.plugins.activate("security_scanner")

# 调用工具
result = client.tools.call(
    "security_scanner.port_scan",
    {"host": "192.168.1.1", "ports": [80, 443]}
)
```

---

### 2. API 网关层 (API Gateway Layer)

**职责**: 处理 HTTP 请求，提供统一的 API 接口

**核心文件**:
- `server/uplifted/server/api.py` - FastAPI 应用主文件
- `server/uplifted/server/openapi_config.py` - OpenAPI 配置
- `server/uplifted/server/plugins_api.py` - 插件管理 API

**主要功能**:

1. **请求路由**: 将 HTTP 请求路由到正确的处理器
2. **请求验证**: 使用 Pydantic 验证请求参数
3. **响应格式化**: 统一的 JSON 响应格式
4. **错误处理**: 捕获异常并返回友好的错误消息
5. **认证授权**: API 密钥验证（可选）
6. **速率限制**: 防止 API 滥用
7. **OpenAPI 文档**: 自动生成 API 文档

**技术栈**:
- FastAPI 0.104+
- Pydantic 2.0+
- Uvicorn (ASGI server)

**API 端点分组**:

```
/api/v1/plugins/*         # 插件管理
/api/v1/tools/*           # 工具管理
/api/v1/system/*          # 系统状态
/status                   # 健康检查
/docs                     # Swagger UI
/redoc                    # ReDoc
/openapi.json             # OpenAPI schema
```

---

### 3. 服务管理层 (Service Layer)

**职责**: 业务逻辑的 API 封装

**主要服务**:

#### 3.1 Plugin API Service

提供插件管理的 REST API：

- `GET /api/v1/plugins` - 列出所有插件
- `GET /api/v1/plugins/{plugin_id}` - 获取插件详情
- `POST /api/v1/plugins/{plugin_id}/activate` - 激活插件
- `POST /api/v1/plugins/{plugin_id}/deactivate` - 停用插件
- `GET /api/v1/plugins/{plugin_id}/tools` - 获取插件工具列表

#### 3.2 Tools API Service

提供工具查询的 REST API：

- `GET /api/v1/tools` - 列出所有工具
- `GET /api/v1/tools/{tool_name}` - 获取工具详情
- `GET /api/v1/tools/{tool_name}/source` - 查询工具来源插件

#### 3.3 System API Service

提供系统状态的 REST API：

- `GET /api/v1/system/status` - 获取系统状态
- `GET /status` - 健康检查

---

### 4. 核心业务层 (Core Business Layer)

**职责**: 实现核心业务逻辑

#### 4.1 Plugin Manager (插件管理器)

**文件**: `server/uplifted/extensions/plugin_manager.py`

**职责**:
- 加载和卸载插件
- 管理插件生命周期
- 维护插件注册表
- 处理插件依赖

**核心类**:

```python
class PluginManager:
    """插件管理器"""

    def load_plugin(self, plugin_id: str, plugin_dir: str) -> None:
        """加载插件"""

    def activate_plugin(self, plugin_id: str) -> None:
        """激活插件"""

    def deactivate_plugin(self, plugin_id: str) -> None:
        """停用插件"""

    def unload_plugin(self, plugin_id: str) -> None:
        """卸载插件"""

    def list_plugins(self, status: Optional[PluginStatus] = None) -> List[str]:
        """列出插件"""

    def get_plugin_info(self, plugin_id: str) -> Dict[str, Any]:
        """获取插件信息"""
```

**状态机**:

```
       load           activate
UNLOADED ──> LOADED ──> ACTIVE
              ↓           ↓
              └─ INACTIVE ┘
                   ↓
                UNLOADED
```

#### 4.2 MCP Bridge (MCP 桥接器)

**文件**: `server/uplifted/extensions/mcp_bridge.py`

**职责**:
- 将插件工具注册为 MCP 工具
- 管理工具到 MCP 的映射
- 处理工具调用
- 管理工具元数据

**核心类**:

```python
class MCPPluginBridge:
    """MCP 插件桥接器"""

    def register_plugin_tools(self, plugin_id: str, manifest: PluginManifest) -> int:
        """注册插件的所有工具"""

    def unregister_plugin_tools(self, plugin_id: str) -> int:
        """取消注册插件的工具"""

    def list_tools(self, plugin_id: Optional[str] = None) -> List[str]:
        """列出工具"""

    def get_tool_info(self, full_tool_name: str) -> Optional[Dict[str, Any]]:
        """获取工具信息"""

    def get_tool_source_plugin(self, full_tool_name: str) -> Optional[str]:
        """获取工具来源插件"""
```

**工具命名**:

格式: `{plugin_id}.{tool_name}`

示例: `security_scanner.port_scan`

#### 4.3 Config Manager (配置管理器)

**文件**: `server/uplifted/extensions/config_manager.py`

**职责**:
- 加载和保存配置
- 管理配置层次结构
- 提供配置访问接口
- 监听配置变更

**核心接口**:

```python
class ConfigManager:
    """配置管理器"""

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""

    def set(self, key: str, value: Any) -> None:
        """设置配置值"""

    def update(self, config: Dict[str, Any]) -> None:
        """批量更新配置"""

    def get_all(self) -> Dict[str, Any]:
        """获取所有配置"""

    def save(self, path: Optional[str] = None) -> None:
        """保存配置到文件"""

    def reload(self) -> None:
        """重新加载配置"""
```

**配置层次**:

```
1. 默认配置 (代码中定义)
   ↓
2. 配置文件 (config/config.yaml)
   ↓
3. 环境变量 (.env, 系统环境变量)
   ↓
4. 运行时配置 (API 设置)

优先级: 4 > 3 > 2 > 1
```

#### 4.4 Tool Registry (工具注册表)

**文件**: `server/uplifted/extensions/plugin_manifest.py`

**职责**:
- 维护工具定义
- 管理工具元数据
- 验证工具 schema

**核心类**:

```python
class ToolDefinition:
    """工具定义"""

    name: str
    description: str
    version: str
    author: str
    mcp_config: MCPToolConfig
    input_schema: Dict[str, Any]
    metadata: Dict[str, Any]

    def validate(self) -> Dict[str, Any]:
        """验证工具定义"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolDefinition":
        """从字典创建"""
```

---

### 5. 数据访问层 (Data Access Layer)

**职责**: 提供统一的数据访问接口

#### 5.1 File Storage

**用途**:
- 插件文件存储
- 日志文件存储
- 配置文件存储

**目录结构**:

```
uplifted/
├── plugins/          # 插件目录
│   ├── plugin1/
│   └── plugin2/
├── data/             # 数据目录
│   └── uplifted.db   # SQLite 数据库
├── logs/             # 日志目录
│   └── uplifted.log
└── config/           # 配置目录
    └── config.yaml
```

#### 5.2 Database

**支持的数据库**:
- SQLite (默认，开发环境)
- PostgreSQL (推荐，生产环境)

**数据模型**:

```python
# 插件状态表
plugins:
  - id: str (PK)
  - name: str
  - version: str
  - status: str
  - config: json
  - loaded_at: datetime
  - activated_at: datetime

# 工具注册表
tools:
  - id: str (PK)
  - plugin_id: str (FK)
  - name: str
  - full_name: str
  - input_schema: json
  - registered_at: datetime
  - active: bool

# 配置表
configurations:
  - key: str (PK)
  - value: json
  - updated_at: datetime
```

---

### 6. 外部集成层 (External Layer)

**职责**: 与外部系统集成

#### 6.1 AI Providers

**支持的提供商**:
- OpenAI (GPT-3.5, GPT-4, etc.)
- Anthropic (Claude 3, etc.)
- Google (Gemini)
- DeepSeek
- Azure OpenAI
- AWS Bedrock
- OpenRouter

**集成方式**:
- 通过 HTTP API 调用
- 使用官方 SDK
- 环境变量配置 API 密钥

#### 6.2 MCP Tools

**工具执行**:
- 通过子进程调用外部程序
- 使用 stdin/stdout 通信
- JSON 格式的输入输出

**示例流程**:

```
1. API 请求 → 工具调用
2. 查找工具定义
3. 验证输入参数
4. 启动子进程
5. 发送 JSON 输入到 stdin
6. 读取 stdout 的 JSON 输出
7. 返回结果给客户端
```

#### 6.3 External APIs

**集成示例**:
- 威胁情报 API
- 漏洞数据库
- CVE 查询
- IP 地理位置查询

---

## 数据流

### 插件加载流程

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant PluginManager
    participant MCPBridge
    participant Plugin

    Client->>API: POST /api/v1/plugins/{id}/activate
    API->>PluginManager: activate_plugin(id)
    PluginManager->>Plugin: load manifest
    Plugin-->>PluginManager: manifest
    PluginManager->>Plugin: import module
    Plugin-->>PluginManager: plugin instance
    PluginManager->>Plugin: activate()
    Plugin-->>PluginManager: success
    PluginManager->>MCPBridge: register_plugin_tools(id, manifest)
    MCPBridge-->>PluginManager: tools registered
    PluginManager-->>API: activation result
    API-->>Client: 200 OK
```

### 工具调用流程

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant MCPBridge
    participant Tool

    Client->>API: POST /api/v1/tools/{name}/call
    API->>MCPBridge: get_tool_info(name)
    MCPBridge-->>API: tool info
    API->>API: validate input
    API->>MCPBridge: call_tool(name, input)
    MCPBridge->>Tool: start subprocess
    MCPBridge->>Tool: send JSON to stdin
    Tool-->>MCPBridge: JSON result from stdout
    MCPBridge-->>API: tool result
    API-->>Client: 200 OK + result
```

### 配置加载流程

```mermaid
flowchart TD
    A[应用启动] --> B[加载默认配置]
    B --> C[读取 config.yaml]
    C --> D[解析环境变量]
    D --> E[应用 .env 文件]
    E --> F[合并配置]
    F --> G{验证配置}
    G -->|有效| H[配置就绪]
    G -->|无效| I[抛出错误]
    I --> J[应用退出]
```

---

## 设计决策

### 1. 为什么选择 FastAPI？

**优势**:
- 自动生成 OpenAPI 文档
- 强大的类型验证（Pydantic）
- 异步支持（性能优越）
- 开发者体验友好
- 活跃的社区

### 2. 为什么使用插件系统？

**原因**:
- **模块化**: 功能独立开发和测试
- **可扩展**: 无需修改核心代码即可添加功能
- **隔离性**: 插件故障不影响核心系统
- **社区贡献**: 便于第三方开发者贡献

### 3. 为什么选择 MCP 协议？

**原因**:
- **标准化**: 统一的工具调用接口
- **语言无关**: 可以用任何语言编写工具
- **进程隔离**: 工具运行在独立进程
- **安全性**: 限制工具权限

### 4. SQLite vs PostgreSQL？

**决策**:
- 默认使用 **SQLite**（简单部署）
- 生产环境推荐 **PostgreSQL**（高并发）

### 5. 同步 vs 异步？

**决策**:
- API 层使用**异步** (FastAPI/uvicorn)
- 插件可以使用**同步或异步**
- I/O 密集型操作使用异步

---

## 扩展性

### 水平扩展

**负载均衡**:

```
                  Load Balancer
                       ↓
         ┌─────────────┼─────────────┐
         ↓             ↓             ↓
    Instance 1    Instance 2    Instance 3
```

**共享状态**:
- 使用 PostgreSQL 作为共享数据库
- Redis 用于缓存和会话
- 文件系统通过 NFS/S3 共享

### 垂直扩展

**资源调整**:
- 增加 worker 数量
- 增加内存限制
- 使用更强的 CPU

### 插件扩展

**插件可以**:
- 提供新的工具
- 添加新的 API 端点
- 扩展配置选项
- 集成外部服务

### 数据库扩展

**迁移到 PostgreSQL**:

```python
# 修改配置
UPLIFTED__DATABASE__URL=postgresql://user:pass@host:5432/uplifted

# 运行迁移
python -m uplifted.migrations.migrate
```

---

## 安全性

### API 安全

1. **API 密钥认证**:
   ```python
   # 启用 API 密钥
   UPLIFTED__SECURITY__API_KEY_REQUIRED=true
   UPLIFTED__SECURITY__API_KEY=your-secure-key
   ```

2. **HTTPS**: 生产环境必须使用 HTTPS

3. **CORS**: 配置允许的来源
   ```python
   UPLIFTED__SECURITY__CORS_ORIGINS=https://app.example.com
   ```

4. **速率限制**: 防止 API 滥用
   ```python
   UPLIFTED__SECURITY__RATE_LIMIT__ENABLED=true
   UPLIFTED__SECURITY__RATE_LIMIT__REQUESTS_PER_MINUTE=60
   ```

### 插件安全

1. **权限控制**: 插件运行在受限环境
2. **审批机制**: 敏感工具需要审批
3. **资源限制**: 限制 CPU/内存使用
4. **沙盒隔离**: 工具运行在独立进程

### 数据安全

1. **敏感配置加密**: 使用 EncryptedConfigLoader
2. **密钥管理**: 不在代码中硬编码密钥
3. **日志脱敏**: 不记录敏感信息

---

## 性能考虑

### 缓存策略

**多级缓存**:

```
1. 内存缓存 (LRU)
   ↓
2. Redis 缓存
   ↓
3. 数据库
```

### 数据库优化

1. **索引**: 为常查询字段添加索引
2. **连接池**: 复用数据库连接
3. **批量操作**: 减少往返次数

### 异步处理

```python
# 异步 API 端点
@app.get("/api/v1/plugins")
async def list_plugins():
    # 异步操作
    plugins = await plugin_manager.list_plugins_async()
    return plugins
```

### 并发控制

```python
# 限制并发数量
semaphore = asyncio.Semaphore(10)

async def limited_task():
    async with semaphore:
        # 执行任务
        pass
```

---

## 未来规划

### 短期 (3 个月)

- ✅ 插件系统
- ✅ 配置管理
- ✅ 简化部署
- ⏳ 完整文档
- ⏳ 测试覆盖 >80%

### 中期 (6 个月)

- Web UI
- 插件市场
- 更多预构建工具
- Kubernetes 部署
- 分布式任务队列

### 长期 (12 个月)

- 多租户支持
- 企业级功能
- 高级监控
- 机器学习集成
- 自动化工作流

---

## 参考

### 设计模式

- **工厂模式**: 插件创建
- **单例模式**: 全局管理器
- **桥接模式**: MCP 集成
- **策略模式**: 配置加载器

### 架构原则

- **SOLID 原则**
- **DRY (Don't Repeat Yourself)**
- **KISS (Keep It Simple, Stupid)**
- **YAGNI (You Aren't Gonna Need It)**

### 相关文档

- [部署指南](./DEPLOYMENT.md)
- [配置管理](./CONFIG_MANAGEMENT.md)
- [插件开发教程](./PLUGIN_DEVELOPMENT_TUTORIAL.md)
- [API 文档](./API_USAGE.md)

---

**最后更新**: 2025-10-28
**版本**: 1.0.0
**作者**: Uplifted Team

如有架构相关问题，欢迎提交 Issue 讨论！
