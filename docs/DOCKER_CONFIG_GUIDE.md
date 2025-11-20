# Docker 配置管理完整指南

本文档详细说明如何在 Docker 环境中管理 Uplifted 的配置。

## 📋 目录

1. [配置方式概览](#配置方式概览)
2. [环境变量配置](#环境变量配置)
3. [配置文件管理](#配置文件管理)
4. [敏感信息管理](#敏感信息管理)
5. [配置优先级](#配置优先级)
6. [实际操作示例](#实际操作示例)
7. [最佳实践](#最佳实践)

---

## 配置方式概览

Uplifted 支持多种配置方式，按优先级从高到低排列：

```
1. 环境变量 (最高优先级)
   ├─ Docker run -e 参数
   ├─ docker-compose.yml environment 段
   └─ .env 文件

2. 配置文件
   ├─ /config/config.yaml (容器内)
   └─ ./config/config.yaml (宿主机挂载)

3. 默认值 (最低优先级)
   └─ 代码内置默认配置
```

---

## 环境变量配置

### 方式 1：使用 `.env` 文件（推荐）

#### 步骤 1：创建 `.env` 文件

```bash
# 复制示例文件
cp .env.example .env

# 编辑配置
nano .env  # 或使用你喜欢的编辑器
```

#### 步骤 2：填写必需的配置

```bash
# .env 文件最小配置
UPLIFTED_ENV=production

# 至少配置一个 AI Provider
OPENAI_API_KEY=sk-your-key-here
# 或
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

#### 步骤 3：启动服务

```bash
# docker-compose 会自动读取 .env 文件
docker-compose up -d
```

#### `.env` 文件的优势

✅ **安全**：不会被提交到 Git（已在 .gitignore 中）
✅ **简单**：一个文件管理所有配置
✅ **灵活**：开发/测试/生产环境可以使用不同的 .env 文件
✅ **自动加载**：docker-compose 自动读取

---

### 方式 2：在 docker-compose.yml 中配置

适合**非敏感**配置：

```yaml
services:
  uplifted:
    environment:
      - UPLIFTED_ENV=production
      - UPLIFTED__SERVER__PORT=7541
      # 敏感信息使用 .env 文件
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

---

### 方式 3：Docker run 命令行参数

适合**临时测试**：

```bash
docker run -d \
  -e UPLIFTED_ENV=development \
  -e OPENAI_API_KEY=sk-test-key \
  -p 7541:7541 -p 8086:8086 \
  uplifted:latest
```

---

## 配置文件管理

### 使用 Volume 挂载配置文件

#### 方式 1：挂载单个配置文件

```yaml
# docker-compose.yml
services:
  uplifted:
    volumes:
      - ./config/config.yaml:/config/config.yaml:ro
```

#### 方式 2：挂载整个配置目录

```yaml
# docker-compose.yml
services:
  uplifted:
    volumes:
      - ./config:/config:ro  # :ro 表示只读
```

---

### 配置文件示例

创建 `./config/config.yaml`：

```yaml
# config/config.yaml
server:
  host: 0.0.0.0
  port: 7541
  workers: 4
  log_level: INFO

tools_server:
  port: 8086
  mcp_enabled: true

database:
  path: /data/uplifted.db
  pool_size: 10

plugins:
  enabled: true
  auto_load: true
  auto_activate: true
  directories:
    - /plugins
    - /app/examples/plugins

logging:
  level: INFO
  file: /logs/uplifted.log
  max_size: 10485760  # 10MB
  backup_count: 5
  format: "[%(asctime)s] %(levelname)s - %(message)s"

security:
  api_key_required: false
  cors_origins:
    - "*"
  rate_limit:
    enabled: false
    requests: 100
    period: 60

# AI Providers (使用环境变量更安全)
# ai_providers:
#   openai:
#     api_key: ${OPENAI_API_KEY}
#   anthropic:
#     api_key: ${ANTHROPIC_API_KEY}
```

---

## 敏感信息管理

### 方法 1：Docker Secrets（推荐生产环境）

#### 创建 secrets

```bash
# 创建 API Key secret
echo "sk-your-openai-key" | docker secret create openai_api_key -
echo "sk-ant-your-anthropic-key" | docker secret create anthropic_api_key -
```

#### 在 docker-compose.yml 中使用

```yaml
version: '3.8'

services:
  uplifted:
    image: uplifted:latest
    secrets:
      - openai_api_key
      - anthropic_api_key
    environment:
      - OPENAI_API_KEY_FILE=/run/secrets/openai_api_key
      - ANTHROPIC_API_KEY_FILE=/run/secrets/anthropic_api_key

secrets:
  openai_api_key:
    external: true
  anthropic_api_key:
    external: true
```

#### 在代码中读取 secrets

```python
# server/uplifted/utils/secrets.py
import os

def get_secret(key: str) -> str:
    """从环境变量或 Docker secrets 读取敏感信息"""
    # 优先读取环境变量
    value = os.getenv(key)
    if value:
        return value

    # 尝试从 secrets 文件读取
    secret_file = os.getenv(f"{key}_FILE")
    if secret_file and os.path.exists(secret_file):
        with open(secret_file) as f:
            return f.read().strip()

    raise ValueError(f"Secret '{key}' not found")

# 使用
openai_key = get_secret("OPENAI_API_KEY")
```

---

### 方法 2：使用 .env 文件（开发环境）

```bash
# .env
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# 确保 .env 在 .gitignore 中
echo ".env" >> .gitignore
```

---

### 方法 3：环境变量文件加密（高级）

使用工具如 `sops` 或 `git-crypt` 加密 .env 文件：

```bash
# 使用 sops 加密
sops -e .env > .env.encrypted

# 解密并启动
sops -d .env.encrypted > .env
docker-compose up -d
rm .env  # 启动后删除明文
```

---

## 配置优先级

配置的读取优先级（从高到低）：

```
1. 命令行参数 (-e)
   docker run -e UPLIFTED_ENV=dev uplifted:latest

2. docker-compose.yml environment
   environment:
     - UPLIFTED_ENV=production

3. .env 文件
   UPLIFTED_ENV=production

4. 配置文件 (/config/config.yaml)
   server:
     log_level: INFO

5. 代码默认值
   LOG_LEVEL = "WARNING"
```

### 示例：同一配置在不同地方设置

```bash
# .env 文件
UPLIFTED__SERVER__LOG_LEVEL=INFO

# docker-compose.yml
environment:
  - UPLIFTED__SERVER__LOG_LEVEL=DEBUG

# 最终使用：DEBUG (docker-compose.yml 优先级更高)
```

---

## 实际操作示例

### 场景 1：开发环境配置

```bash
# 1. 创建开发环境配置
cat > .env.development << EOF
UPLIFTED_ENV=development
UPLIFTED__SERVER__LOG_LEVEL=DEBUG
OPENAI_API_KEY=sk-test-key
DEBUG=true
EOF

# 2. 使用开发配置启动
cp .env.development .env
docker-compose up -d

# 3. 查看日志
docker-compose logs -f uplifted
```

---

### 场景 2：生产环境配置

```bash
# 1. 创建生产环境配置
cat > .env.production << EOF
UPLIFTED_ENV=production
UPLIFTED__SERVER__LOG_LEVEL=INFO
UPLIFTED__SERVER__WORKERS=8
UPLIFTED__SECURITY__API_KEY_REQUIRED=true
UPLIFTED__SECURITY__API_KEY=your-secure-api-key
OPENAI_API_KEY=sk-prod-key
SENTRY_DSN=https://your-sentry-dsn
EOF

# 2. 设置正确的权限
chmod 600 .env.production

# 3. 使用生产配置
cp .env.production .env
docker-compose up -d
```

---

### 场景 3：整合 HexStrike 的配置

```bash
# .env
UPLIFTED_ENV=production
OPENAI_API_KEY=sk-your-key

# HexStrike 配置
HEXSTRIKE_HOST=hexstrike
HEXSTRIKE_PORT=8888
HEXSTRIKE_API_URL=http://hexstrike:8888
```

```yaml
# docker-compose.yml
services:
  uplifted:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - HEXSTRIKE_API_URL=${HEXSTRIKE_API_URL}
    depends_on:
      - hexstrike

  hexstrike:
    build: ./hexstrike-ai
    container_name: hexstrike
    ports:
      - "8888:8888"
    environment:
      - HEXSTRIKE_PORT=8888
```

---

### 场景 4：动态修改配置（无需重启）

某些配置支持热重载：

```bash
# 1. 进入容器
docker-compose exec uplifted bash

# 2. 修改配置
echo "new_value" > /config/runtime_config.txt

# 3. 触发重载（如果应用支持）
curl -X POST http://localhost:7541/api/config/reload
```

---

### 场景 5：查看当前配置

```bash
# 查看环境变量
docker-compose exec uplifted env | grep UPLIFTED

# 查看配置文件
docker-compose exec uplifted cat /config/config.yaml

# 通过 API 查看配置（如果有接口）
curl http://localhost:7541/api/config
```

---

## 最佳实践

### ✅ 推荐做法

1. **敏感信息**：
   - ✅ 使用 `.env` 文件或 Docker Secrets
   - ✅ 确保 `.env` 在 `.gitignore` 中
   - ✅ 生产环境使用 Docker Secrets

2. **配置文件**：
   - ✅ 提供 `.env.example` 作为模板
   - ✅ 使用 Volume 挂载配置目录
   - ✅ 配置文件使用 `:ro` (只读) 挂载

3. **版本控制**：
   - ✅ 提交 `.env.example`
   - ✅ 提交 `config.yaml.example`
   - ❌ 不提交 `.env` 或包含密钥的文件

4. **环境隔离**：
   - ✅ 不同环境使用不同的 `.env` 文件
   - ✅ 使用 `docker-compose.override.yml` 覆盖配置

5. **文档化**：
   - ✅ 在 `.env.example` 中注释每个配置项
   - ✅ 维护配置文档（如本文档）

---

### ❌ 避免做法

1. ❌ 在 Dockerfile 中硬编码敏感信息
2. ❌ 将 `.env` 文件提交到 Git
3. ❌ 在 docker-compose.yml 中明文写入 API Key
4. ❌ 使用默认密码在生产环境
5. ❌ 配置文件权限过于宽松（应该是 600 或 400）

---

## 配置检查清单

启动服务前检查：

```bash
# ✓ .env 文件存在且配置正确
[ -f .env ] && echo "✓ .env exists" || echo "✗ .env missing"

# ✓ 必需的 API Key 已配置
grep -q "OPENAI_API_KEY=sk-" .env && echo "✓ OpenAI key set" || echo "⚠ OpenAI key missing"

# ✓ .env 文件权限正确（600 或 400）
stat -c "%a" .env | grep -q "600\|400" && echo "✓ Permissions OK" || echo "⚠ Fix permissions: chmod 600 .env"

# ✓ 配置目录存在
[ -d ./config ] && echo "✓ config directory exists" || mkdir -p ./config

# ✓ docker-compose.yml 语法正确
docker-compose config > /dev/null 2>&1 && echo "✓ docker-compose.yml valid" || echo "✗ Syntax error"
```

---

## 故障排查

### 问题 1：环境变量未生效

**症状**：修改了 `.env` 但配置没有改变

**解决**：
```bash
# 1. 重新构建并重启（确保读取新配置）
docker-compose down
docker-compose up -d --force-recreate

# 2. 检查环境变量是否正确传入
docker-compose exec uplifted env | grep UPLIFTED
```

---

### 问题 2：配置文件挂载失败

**症状**：`ERROR: Cannot find config file`

**解决**：
```bash
# 检查挂载路径
docker-compose exec uplifted ls -la /config

# 检查宿主机文件存在
ls -la ./config/config.yaml

# 重新挂载
docker-compose down
docker-compose up -d
```

---

### 问题 3：Docker Secrets 读取失败

**症状**：`Secret 'xxx' not found`

**解决**：
```bash
# 检查 secrets 是否创建
docker secret ls

# 检查容器内 secrets
docker-compose exec uplifted ls -la /run/secrets/

# 重新创建 secret
docker secret rm openai_api_key
echo "sk-new-key" | docker secret create openai_api_key -
```

---

## 总结

| 配置方式 | 适用场景 | 安全性 | 灵活性 |
|---------|---------|--------|--------|
| `.env` 文件 | 开发环境 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Docker Secrets | 生产环境 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 配置文件挂载 | 复杂配置 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 环境变量 | 简单配置 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

**推荐方案**：
- 🏠 **开发环境**：`.env` 文件 + 配置文件挂载
- 🏢 **生产环境**：Docker Secrets + 配置文件挂载 + 环境变量

---

## 参考资源

- [Docker Compose 环境变量文档](https://docs.docker.com/compose/environment-variables/)
- [Docker Secrets 文档](https://docs.docker.com/engine/swarm/secrets/)
- [12-Factor App 配置管理](https://12factor.net/config)
