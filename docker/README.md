# Uplifted Docker 部署指南

快速使用 Docker 部署 Uplifted。

## 快速开始

### 1. 使用 Docker Compose（推荐）

```bash
# 克隆仓库
git clone https://github.com/uplifted/uplifted.git
cd uplifted

# 复制环境变量模板
cp .env.example .env

# 编辑 .env，填入你的 API 密钥
nano .env

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 访问服务
# Main API: http://localhost:7541
# API Docs: http://localhost:7541/docs
# Tools Server: http://localhost:8086
```

### 2. 使用 Docker（不使用 Compose）

```bash
# 构建镜像
docker build -t uplifted:latest .

# 运行容器
docker run -d \
  --name uplifted \
  -p 7541:7541 \
  -p 8086:8086 \
  -v uplifted-data:/data \
  -v uplifted-logs:/logs \
  -v uplifted-config:/config \
  -v uplifted-plugins:/plugins \
  -e OPENAI_API_KEY=your-key \
  -e ANTHROPIC_API_KEY=your-key \
  uplifted:latest

# 查看日志
docker logs -f uplifted
```

## 目录结构

```
docker/
├── entrypoint.sh          # 容器启动脚本
├── healthcheck.sh         # 健康检查脚本
├── nginx/                 # Nginx 配置（可选）
│   ├── nginx.conf
│   └── ssl/
└── README.md              # 本文档
```

## 环境变量

详细的环境变量配置请参考 `.env.example`。

### 必需的环境变量

```bash
# 至少配置一个 AI 提供商的 API 密钥
OPENAI_API_KEY=sk-...
# 或
ANTHROPIC_API_KEY=sk-ant-...
```

### 常用配置

```bash
# 服务器配置
UPLIFTED_ENV=production
UPLIFTED__SERVER__WORKERS=4
UPLIFTED__SERVER__LOG_LEVEL=INFO

# 插件配置
UPLIFTED__PLUGINS__ENABLED=true
UPLIFTED__PLUGINS__AUTO_LOAD=true
```

## 数据持久化

Docker Compose 自动创建以下卷：

- `uplifted-data` - 数据库和持久化数据
- `uplifted-logs` - 日志文件
- `uplifted-config` - 配置文件
- `uplifted-plugins` - 插件目录

### 备份数据

```bash
# 备份所有数据
docker run --rm \
  -v uplifted-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/uplifted-data-$(date +%Y%m%d).tar.gz /data

# 恢复数据
docker run --rm \
  -v uplifted-data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/uplifted-data-20251028.tar.gz -C /
```

## 健康检查

容器内置健康检查，每30秒检查一次：

```bash
# 查看健康状态
docker ps

# 手动运行健康检查
docker exec uplifted /usr/local/bin/healthcheck.sh
```

## 常用命令

### 查看日志

```bash
# 所有日志
docker-compose logs -f

# 仅主服务
docker-compose logs -f uplifted

# 最近100行
docker-compose logs --tail=100 uplifted
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 仅重启主服务
docker-compose restart uplifted
```

### 进入容器

```bash
# 进入 bash shell
docker-compose exec uplifted bash

# 进入 Python REPL
docker-compose exec uplifted python
```

### 生成配置

```bash
# 生成默认配置
docker-compose exec uplifted entrypoint.sh config

# 查看生成的配置
docker-compose exec uplifted cat /config/config.yaml
```

### 运行测试

```bash
# 运行测试
docker-compose exec uplifted entrypoint.sh test
```

## 多阶段构建

Dockerfile 使用多阶段构建优化镜像大小：

- **Builder 阶段**: 安装依赖，创建虚拟环境
- **Runtime 阶段**: 仅复制必要文件，移除构建工具

最终镜像大小约 500-700MB。

## 生产部署建议

### 1. 使用具体的镜像标签

```yaml
# docker-compose.yml
services:
  uplifted:
    image: uplifted:0.53.1  # 使用具体版本，而不是 latest
```

### 2. 限制资源

```yaml
services:
  uplifted:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. 配置日志轮转

```yaml
services:
  uplifted:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. 使用 Secrets 管理敏感信息

```yaml
services:
  uplifted:
    secrets:
      - openai_api_key
      - anthropic_api_key

secrets:
  openai_api_key:
    file: ./secrets/openai_api_key.txt
  anthropic_api_key:
    file: ./secrets/anthropic_api_key.txt
```

### 5. 添加反向代理（Nginx）

参考 `docker-compose.yml` 中的 nginx 服务配置。

## 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker-compose logs uplifted

# 检查配置
docker-compose config

# 验证环境变量
docker-compose exec uplifted env | grep UPLIFTED
```

### API 无法访问

```bash
# 检查端口
docker-compose ps

# 测试健康检查
docker-compose exec uplifted /usr/local/bin/healthcheck.sh

# 检查防火墙
sudo ufw status
sudo ufw allow 7541/tcp
```

### 权限问题

```bash
# 检查文件所有权
docker-compose exec uplifted ls -la /data /logs /config

# 修复权限（如果需要）
docker-compose exec uplifted chown -R uplifted:uplifted /data /logs /config
```

### 性能问题

```bash
# 查看资源使用
docker stats uplifted

# 增加 workers
# 在 .env 中设置
UPLIFTED__SERVER__WORKERS=8

# 重启服务
docker-compose restart
```

## 升级

### 升级到新版本

```bash
# 拉取新代码
git pull

# 重新构建镜像
docker-compose build --no-cache

# 停止旧容器
docker-compose down

# 启动新容器
docker-compose up -d

# 验证
docker-compose logs -f
```

### 回滚

```bash
# 使用之前的镜像
docker-compose down
docker-compose up -d uplifted:0.52.0

# 或从备份恢复数据
```

## 监控

### Prometheus 指标

```yaml
# docker-compose.yml 中启用监控
services:
  uplifted:
    environment:
      - UPLIFTED__MONITORING__ENABLED=true
      - UPLIFTED__MONITORING__PROMETHEUS_PORT=9090
    ports:
      - "9090:9090"
```

### Grafana 仪表板

参考 `docker/grafana/` 目录中的仪表板配置。

## 安全建议

1. **不要使用 root 用户**
   - 容器已配置为 `uplifted` 用户运行

2. **限制网络访问**
   ```yaml
   networks:
     uplifted-network:
       internal: true  # 内部网络，不暴露到外部
   ```

3. **使用 HTTPS**
   - 配置 Nginx 反向代理
   - 使用 Let's Encrypt 证书

4. **定期更新**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

5. **扫描漏洞**
   ```bash
   docker scan uplifted:latest
   ```

## 相关文档

- [部署指南](../docs/DEPLOYMENT.md)
- [配置管理](../docs/CONFIG_MANAGEMENT.md)
- [API 文档](http://localhost:7541/docs)

## 支持

- Issues: https://github.com/uplifted/uplifted/issues
- 文档: https://uplifted.ai/docs
