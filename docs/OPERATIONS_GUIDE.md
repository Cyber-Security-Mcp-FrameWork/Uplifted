# Uplifted 运维指南

本文档提供 Uplifted 系统的日常运维、监控、维护和故障排查指南。

## 目录

- [日常运维](#日常运维)
- [监控和告警](#监控和告警)
- [日志管理](#日志管理)
- [备份和恢复](#备份和恢复)
- [性能调优](#性能调优)
- [故障排查](#故障排查)
- [安全维护](#安全维护)
- [升级和维护窗口](#升级和维护窗口)
- [容量规划](#容量规划)
- [应急预案](#应急预案)
- [运维检查清单](#运维检查清单)

---

## 日常运维

### 每日检查

#### 1. 服务状态检查

```bash
# systemd 方式
sudo systemctl status uplifted

# Docker 方式
docker-compose ps

# 手动方式
curl http://localhost:7541/status
```

**预期输出**:
```json
{
  "status": "Server is running"
}
```

#### 2. 健康检查

```bash
# 检查主 API
curl http://localhost:7541/api/v1/system/status

# 检查工具服务器
curl http://localhost:8086/health
```

**预期输出**:
```json
{
  "plugin_count": 12,
  "active_plugin_count": 10,
  "total_tools": 45,
  "active_tools": 42,
  "mcp_available": true
}
```

#### 3. 日志检查

```bash
# 查看最近的错误
grep -i error logs/uplifted.log | tail -n 50

# 或使用 journalctl (systemd)
sudo journalctl -u uplifted --since "1 hour ago" | grep -i error

# Docker logs
docker-compose logs --tail=100 uplifted | grep -i error
```

#### 4. 资源使用检查

```bash
# CPU 和内存使用
top -p $(pgrep -f uplifted)

# 或使用 htop
htop -p $(pgrep -f uplifted)

# Docker 资源使用
docker stats uplifted
```

### 每周维护

#### 1. 日志轮转

确保日志文件不会无限增长：

```bash
# 检查日志大小
du -h logs/uplifted.log

# 手动轮转（如果需要）
mv logs/uplifted.log logs/uplifted.log.$(date +%Y%m%d)
sudo systemctl reload uplifted  # 重新打开日志文件
```

**自动日志轮转配置** (`/etc/logrotate.d/uplifted`):

```
/opt/uplifted/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 uplifted uplifted
    sharedscripts
    postrotate
        systemctl reload uplifted > /dev/null 2>&1 || true
    endscript
}
```

#### 2. 数据库维护

**SQLite**:

```bash
# 进入数据库
sqlite3 data/uplifted.db

# 运行优化
VACUUM;
ANALYZE;

# 检查完整性
PRAGMA integrity_check;

# 退出
.quit
```

**PostgreSQL**:

```bash
# 运行 VACUUM
psql -U uplifted -d uplifted -c "VACUUM ANALYZE;"

# 检查死元组
psql -U uplifted -d uplifted -c "SELECT schemaname, tablename, n_dead_tup FROM pg_stat_user_tables WHERE n_dead_tup > 1000;"

# 重建索引（如果需要）
psql -U uplifted -d uplifted -c "REINDEX DATABASE uplifted;"
```

#### 3. 磁盘空间检查

```bash
# 检查磁盘使用
df -h

# 检查各目录大小
du -sh /opt/uplifted/*

# 清理旧日志（保留最近 30 天）
find /opt/uplifted/logs -name "*.log.*" -mtime +30 -delete
```

### 每月维护

#### 1. 更新检查

```bash
# 检查是否有新版本
cd /opt/uplifted
git fetch
git log HEAD..origin/main --oneline

# 查看 changelog
git log HEAD..origin/main --pretty=format:"%h - %s"
```

#### 2. 安全更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade  # Ubuntu/Debian
sudo yum update  # CentOS/RHEL

# 更新 Python 依赖
source venv/bin/activate
pip list --outdated
pip install -U <package-name>  # 谨慎更新
```

#### 3. 性能审计

```bash
# 生成性能报告
python -m uplifted.tools.performance_audit

# 或手动检查
# - API 响应时间
# - 数据库查询性能
# - 插件加载时间
# - 工具执行时间
```

---

## 监控和告警

### Prometheus 监控

#### 1. 启用 Prometheus 指标

在 `.env` 中配置：

```bash
UPLIFTED__MONITORING__ENABLED=true
UPLIFTED__MONITORING__PROMETHEUS_PORT=9090
```

#### 2. Prometheus 配置

创建 `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'uplifted'
    static_configs:
      - targets: ['localhost:9090']
```

#### 3. 关键指标

- `uplifted_requests_total` - 总请求数
- `uplifted_requests_duration_seconds` - 请求耗时
- `uplifted_active_plugins` - 活跃插件数
- `uplifted_tool_calls_total` - 工具调用总数
- `uplifted_tool_errors_total` - 工具错误数
- `uplifted_db_connections` - 数据库连接数

#### 4. Grafana 仪表板

导入预配置的 Grafana 仪表板：

```bash
# 访问 Grafana
http://localhost:3000

# 导入仪表板
Configuration → Data Sources → Add Prometheus
Dashboards → Import → Upload uplifted-dashboard.json
```

### 告警规则

#### Prometheus 告警规则

创建 `alerts.yml`:

```yaml
groups:
  - name: uplifted_alerts
    rules:
      # 服务不可用告警
      - alert: UpliftedDown
        expr: up{job="uplifted"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Uplifted 服务不可用"
          description: "Uplifted 服务已停止超过 1 分钟"

      # 高错误率告警
      - alert: HighErrorRate
        expr: rate(uplifted_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "高错误率"
          description: "5xx 错误率超过 10%"

      # CPU 使用率告警
      - alert: HighCPUUsage
        expr: process_cpu_seconds_total > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "CPU 使用率超过 80%"

      # 磁盘空间告警
      - alert: LowDiskSpace
        expr: node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "磁盘空间不足"
          description: "可用磁盘空间低于 10%"
```

### 健康检查脚本

创建 `scripts/health_check.sh`:

```bash
#!/bin/bash

# Uplifted 健康检查脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

check_service() {
    echo "检查服务状态..."
    if systemctl is-active --quiet uplifted; then
        echo -e "${GREEN}✓ 服务运行中${NC}"
        return 0
    else
        echo -e "${RED}✗ 服务未运行${NC}"
        return 1
    fi
}

check_api() {
    echo "检查 API 端点..."
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:7541/status)
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ API 响应正常${NC}"
        return 0
    else
        echo -e "${RED}✗ API 无响应 (HTTP $response)${NC}"
        return 1
    fi
}

check_resources() {
    echo "检查资源使用..."

    # CPU
    cpu=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    echo "  CPU 使用率: ${cpu}%"

    # 内存
    mem=$(free | grep Mem | awk '{printf("%.2f"), $3/$2 * 100.0}')
    echo "  内存使用率: ${mem}%"

    # 磁盘
    disk=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
    echo "  磁盘使用率: ${disk}%"

    if (( $(echo "$disk > 80" | bc -l) )); then
        echo -e "${RED}! 警告: 磁盘使用率超过 80%${NC}"
        return 1
    fi

    return 0
}

check_logs() {
    echo "检查最近错误..."
    error_count=$(grep -i error logs/uplifted.log 2>/dev/null | tail -n 100 | wc -l)
    echo "  最近 100 行中的错误: $error_count"

    if [ "$error_count" -gt 10 ]; then
        echo -e "${RED}! 警告: 错误数量较多${NC}"
        grep -i error logs/uplifted.log | tail -n 5
        return 1
    fi

    return 0
}

main() {
    echo "======================================"
    echo "  Uplifted 健康检查"
    echo "======================================"
    echo ""

    failures=0

    check_service || ((failures++))
    echo ""

    check_api || ((failures++))
    echo ""

    check_resources || ((failures++))
    echo ""

    check_logs || ((failures++))
    echo ""

    echo "======================================"
    if [ $failures -eq 0 ]; then
        echo -e "${GREEN}✓ 所有检查通过${NC}"
        exit 0
    else
        echo -e "${RED}✗ $failures 项检查失败${NC}"
        exit 1
    fi
}

main
```

使用方法：

```bash
# 手动运行
bash scripts/health_check.sh

# 定时检查 (crontab)
*/10 * * * * /opt/uplifted/scripts/health_check.sh >> /var/log/uplifted-health.log 2>&1
```

---

## 日志管理

### 日志级别

在 `.env` 中配置日志级别：

```bash
# 开发环境
UPLIFTED__LOGGING__LEVEL=DEBUG

# 生产环境
UPLIFTED__LOGGING__LEVEL=INFO

# 仅错误
UPLIFTED__LOGGING__LEVEL=ERROR
```

### 日志格式

默认日志格式：

```
2025-10-28 10:30:45,123 - uplifted.plugin_manager - INFO - Plugin 'security_scanner' activated
2025-10-28 10:30:46,456 - uplifted.mcp_bridge - INFO - Registered 5 tools from 'security_scanner'
2025-10-28 10:30:47,789 - uplifted.api - ERROR - Error in plugins_api.py at line 142: Plugin 'unknown' not found
```

### 日志查询

#### 查看实时日志

```bash
# tail -f
tail -f logs/uplifted.log

# journalctl
sudo journalctl -u uplifted -f

# Docker
docker-compose logs -f uplifted
```

#### 过滤日志

```bash
# 仅错误
grep ERROR logs/uplifted.log

# 特定插件
grep "plugin_manager" logs/uplifted.log

# 时间范围 (journalctl)
sudo journalctl -u uplifted --since "2025-10-28 10:00:00" --until "2025-10-28 11:00:00"

# 特定级别
sudo journalctl -u uplifted -p err  # 仅错误
```

#### 日志分析

```bash
# 统计错误类型
grep ERROR logs/uplifted.log | awk -F': ' '{print $NF}' | sort | uniq -c | sort -rn

# 最活跃的插件
grep "activated\|deactivated" logs/uplifted.log | awk '{print $6}' | sort | uniq -c | sort -rn

# 每小时请求数
grep "Request" logs/uplifted.log | awk '{print $1, $2}' | cut -d: -f1 | uniq -c
```

### 集中式日志

#### ELK Stack

**Filebeat 配置** (`filebeat.yml`):

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /opt/uplifted/logs/*.log
    fields:
      service: uplifted
      environment: production

output.elasticsearch:
  hosts: ["localhost:9200"]

setup.kibana:
  host: "localhost:5601"
```

#### Loki

**Promtail 配置** (`promtail.yml`):

```yaml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:
  - job_name: uplifted
    static_configs:
      - targets:
          - localhost
        labels:
          job: uplifted
          __path__: /opt/uplifted/logs/*.log
```

---

## 备份和恢复

### 备份策略

#### 每日备份

**备份脚本** (`scripts/backup.sh`):

```bash
#!/bin/bash

# Uplifted 备份脚本

BACKUP_DIR="/backup/uplifted"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/uplifted_$DATE"

echo "开始备份: $BACKUP_PATH"

# 创建备份目录
mkdir -p "$BACKUP_PATH"

# 备份数据库
echo "备份数据库..."
cp -r /opt/uplifted/data "$BACKUP_PATH/"

# 备份配置
echo "备份配置..."
cp -r /opt/uplifted/config "$BACKUP_PATH/"
cp /opt/uplifted/.env "$BACKUP_PATH/"

# 备份插件
echo "备份插件..."
cp -r /opt/uplifted/plugins "$BACKUP_PATH/"

# 压缩
echo "压缩备份..."
tar -czf "$BACKUP_PATH.tar.gz" -C "$BACKUP_DIR" "uplifted_$DATE"
rm -rf "$BACKUP_PATH"

echo "备份完成: $BACKUP_PATH.tar.gz"

# 清理旧备份（保留最近 7 天）
find "$BACKUP_DIR" -name "uplifted_*.tar.gz" -mtime +7 -delete

echo "清理旧备份完成"
```

#### 自动备份

添加到 crontab：

```bash
# 每天凌晨 2点备份
0 2 * * * /opt/uplifted/scripts/backup.sh >> /var/log/uplifted-backup.log 2>&1
```

### 恢复流程

#### 从备份恢复

```bash
#!/bin/bash

# 恢复脚本

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "用法: $0 <backup-file.tar.gz>"
    exit 1
fi

echo "从备份恢复: $BACKUP_FILE"

# 停止服务
sudo systemctl stop uplifted

# 备份当前数据（以防万一）
mv /opt/uplifted/data /opt/uplifted/data.old
mv /opt/uplifted/config /opt/uplifted/config.old

# 解压备份
tar -xzf "$BACKUP_FILE" -C /tmp/

# 恢复数据
cp -r /tmp/uplifted_*/data /opt/uplifted/
cp -r /tmp/uplifted_*/config /opt/uplifted/
cp /tmp/uplifted_*/.env /opt/uplifted/

# 设置权限
chown -R uplifted:uplifted /opt/uplifted/data
chown -R uplifted:uplifted /opt/uplifted/config

# 启动服务
sudo systemctl start uplifted

# 验证
sleep 5
curl http://localhost:7541/status

echo "恢复完成"
```

### 数据库备份

#### PostgreSQL

```bash
# 备份
pg_dump -U uplifted uplifted > /backup/uplifted_$(date +%Y%m%d).sql

# 恢复
psql -U uplifted uplifted < /backup/uplifted_20251028.sql
```

#### SQLite

```bash
# 备份
sqlite3 /opt/uplifted/data/uplifted.db ".backup /backup/uplifted_$(date +%Y%m%d).db"

# 恢复
cp /backup/uplifted_20251028.db /opt/uplifted/data/uplifted.db
```

---

## 性能调优

### 系统级优化

#### 1. 调整 Worker 数量

```bash
# 推荐: CPU 核心数 / 2
UPLIFTED__SERVER__WORKERS=4
```

#### 2. 数据库连接池

```bash
# 增加连接池大小
UPLIFTED__DATABASE__POOL_SIZE=20
UPLIFTED__DATABASE__MAX_OVERFLOW=10
```

#### 3. 启用缓存

```bash
# Redis 缓存
REDIS_URL=redis://localhost:6379/0
UPLIFTED__CACHE__ENABLED=true
UPLIFTED__CACHE__TTL=3600
```

### 应用级优化

#### 1. 异步处理

```python
# 使用异步端点
@app.get("/api/v1/plugins")
async def list_plugins():
    plugins = await plugin_manager.list_plugins_async()
    return plugins
```

#### 2. 数据库索引

```sql
-- 为常查询字段添加索引
CREATE INDEX idx_plugin_status ON plugins(status);
CREATE INDEX idx_tool_plugin_id ON tools(plugin_id);
CREATE INDEX idx_tool_active ON tools(active);
```

#### 3. 查询优化

```python
# 使用 select_related 减少查询次数
# 批量操作
# 避免 N+1 查询
```

### 性能基准测试

```bash
# 使用 Apache Bench
ab -n 1000 -c 10 http://localhost:7541/api/v1/plugins

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:7541/api/v1/plugins

# 使用 Locust
locust -f load_test.py --host=http://localhost:7541
```

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

**检查步骤**:

```bash
# 1. 查看 systemd 日志
sudo journalctl -u uplifted -n 100

# 2. 检查端口占用
sudo lsof -i :7541

# 3. 验证配置文件
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# 4. 检查文件权限
ls -la /opt/uplifted
```

**常见原因**:
- 端口被占用
- 配置文件语法错误
- 权限不足
- 依赖缺失

#### 2. API 响应缓慢

**诊断**:

```bash
# 1. 检查系统资源
top
htop
iostat

# 2. 检查数据库性能
# PostgreSQL
psql -c "SELECT * FROM pg_stat_activity;"

# SQLite
sqlite3 uplifted.db "PRAGMA optimize;"

# 3. 查看慢查询日志
grep "slow" logs/uplifted.log
```

**优化措施**:
- 增加 worker 数量
- 启用缓存
- 优化数据库查询
- 增加硬件资源

#### 3. 插件加载失败

**检查**:

```bash
# 1. 验证插件清单
python -c "
from server.uplifted.extensions.plugin_manifest import PluginManifest
manifest = PluginManifest.from_yaml_file('plugins/my_plugin/manifest.yaml')
print(manifest.validate())
"

# 2. 检查依赖
cd plugins/my_plugin
pip install -r requirements.txt

# 3. 测试插件
python -m pytest tests/
```

#### 4. 内存泄漏

**诊断**:

```bash
# 使用 memory_profiler
pip install memory-profiler
python -m memory_profiler server/run_main_server.py

# 查看内存使用趋势
ps aux | grep uplifted | awk '{print $6}'
```

**解决**:
- 定期重启服务
- 修复代码中的循环引用
- 限制缓存大小

### 调试技巧

#### 启用调试模式

```bash
UPLIFTED__DEBUG=true
UPLIFTED__SERVER__LOG_LEVEL=DEBUG
```

#### 使用 pdb 调试

```python
import pdb; pdb.set_trace()
```

#### 性能分析

```python
# 使用 cProfile
python -m cProfile -o profile.stats server/run_main_server.py

# 分析结果
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(20)"
```

---

## 安全维护

### 安全检查清单

- [ ] 使用最新版本
- [ ] 所有密钥使用环境变量
- [ ] 启用 HTTPS
- [ ] 配置防火墙
- [ ] 启用 API 密钥认证
- [ ] 定期更新依赖
- [ ] 限制文件权限
- [ ] 定期审计日志
- [ ] 备份加密

### 安全扫描

```bash
# Python 依赖漏洞扫描
pip install safety
safety check

# 代码安全扫描
pip install bandit
bandit -r server/

# Docker 镜像扫描
docker scan uplifted:latest
```

### 密钥轮转

```bash
# 1. 生成新密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. 更新配置
nano .env

# 3. 重启服务
sudo systemctl restart uplifted
```

---

## 升级和维护窗口

### 计划升级

#### 1. 升级前准备

```bash
# 通知用户
echo "系统将于 2025-10-28 02:00 进行维护" > /opt/uplifted/maintenance.txt

# 完整备份
bash scripts/backup.sh

# 验证备份
tar -tzf /backup/uplifted_*.tar.gz | head
```

#### 2. 执行升级

```bash
# 进入维护模式
sudo systemctl stop uplifted

# 拉取更新
cd /opt/uplifted
git pull

# 更新依赖
source venv/bin/activate
pip install -U -r requirements.txt

# 运行迁移（如果有）
python -m uplifted.migrations.migrate

# 启动服务
sudo systemctl start uplifted
```

#### 3. 升级后验证

```bash
# 检查服务状态
sudo systemctl status uplifted

# API 测试
curl http://localhost:7541/status
curl http://localhost:7541/api/v1/system/status

# 查看日志
sudo journalctl -u uplifted -n 50

# 运行健康检查
bash scripts/health_check.sh
```

### 回滚计划

如果升级失败：

```bash
# 1. 停止服务
sudo systemctl stop uplifted

# 2. 恢复代码
git reset --hard <previous-version>

# 3. 恢复数据（如果需要）
bash scripts/restore.sh /backup/uplifted_20251028.tar.gz

# 4. 启动服务
sudo systemctl start uplifted

# 5. 验证
bash scripts/health_check.sh
```

---

## 容量规划

### 资源需求估算

#### 小型部署 (< 100 用户)

- **CPU**: 2 核
- **内存**: 4GB
- **存储**: 20GB
- **带宽**: 10Mbps

#### 中型部署 (100-1000 用户)

- **CPU**: 4-8 核
- **内存**: 8-16GB
- **存储**: 100GB
- **带宽**: 100Mbps

#### 大型部署 (> 1000 用户)

- **CPU**: 16+ 核（或多实例）
- **内存**: 32GB+
- **存储**: 500GB+
- **带宽**: 1Gbps+
- **负载均衡**: 必需

### 扩容策略

#### 垂直扩容

```bash
# 增加 worker 数量
UPLIFTED__SERVER__WORKERS=8

# 增加数据库连接池
UPLIFTED__DATABASE__POOL_SIZE=50
```

#### 水平扩容

1. 部署多个实例
2. 配置负载均衡器
3. 使用共享数据库 (PostgreSQL)
4. 使用共享缓存 (Redis)
5. 共享文件存储 (NFS/S3)

---

## 应急预案

### 服务中断

**步骤**:

1. 确认中断范围
2. 通知相关人员
3. 启动应急流程
4. 检查日志确定原因
5. 尝试重启服务
6. 如果失败，从备份恢复
7. 验证服务恢复
8. 编写事后报告

### 数据损坏

**步骤**:

1. 立即停止服务
2. 备份当前状态（即使损坏）
3. 从最近的备份恢复
4. 验证数据完整性
5. 重启服务
6. 查明损坏原因

### 安全事件

**步骤**:

1. 隔离受影响系统
2. 收集证据和日志
3. 通知安全团队
4. 分析攻击向量
5. 修复漏洞
6. 恢复服务
7. 加强监控

---

## 运维检查清单

### 每日检查

- [ ] 服务状态正常
- [ ] API 响应正常
- [ ] 无严重错误日志
- [ ] 资源使用正常
- [ ] 备份已完成

### 每周检查

- [ ] 日志已轮转
- [ ] 数据库已优化
- [ ] 磁盘空间充足
- [ ] 安全更新已应用
- [ ] 性能指标正常

### 每月检查

- [ ] 完整系统备份
- [ ] 恢复演练
- [ ] 容量评估
- [ ] 安全审计
- [ ] 文档更新

### 季度检查

- [ ] 系统升级评估
- [ ] 性能基准测试
- [ ] 灾难恢复演练
- [ ] 架构review
- [ ] 许可证续订

---

## 相关文档

- [部署指南](./DEPLOYMENT.md)
- [配置管理](./CONFIG_MANAGEMENT.md)
- [架构文档](./ARCHITECTURE.md)
- [插件开发教程](./PLUGIN_DEVELOPMENT_TUTORIAL.md)

---

**最后更新**: 2025-10-28
**版本**: 1.0.0
**作者**: Uplifted Team

如有运维相关问题，欢迎提交 Issue 或联系运维团队！
