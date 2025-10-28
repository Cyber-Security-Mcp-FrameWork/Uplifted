# Uplifted 部署指南

本文档提供 Uplifted 的完整部署指南，涵盖从开发环境到生产环境的各种部署场景。

## 目录

- [部署方式概览](#部署方式概览)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细部署指南](#详细部署指南)
  - [配置向导部署](#配置向导部署)
  - [一键安装部署](#一键安装部署)
  - [Docker 部署](#docker-部署)
  - [手动部署](#手动部署)
  - [systemd 服务部署](#systemd-服务部署)
  - [Windows 服务部署](#windows-服务部署)
- [云平台部署](#云平台部署)
- [配置管理](#配置管理)
- [安全加固](#安全加固)
- [监控和日志](#监控和日志)
- [故障排查](#故障排查)
- [性能优化](#性能优化)
- [升级和回滚](#升级和回滚)

---

## 部署方式概览

Uplifted 提供多种部署方式，适应不同的使用场景：

| 部署方式 | 适用场景 | 难度 | 推荐指数 |
|---------|---------|------|---------|
| **配置向导** | 首次部署，需要引导式配置 | ⭐ | ⭐⭐⭐⭐⭐ |
| **一键安装** | 快速部署到开发/测试环境 | ⭐ | ⭐⭐⭐⭐⭐ |
| **Docker Compose** | 容器化部署，易于迁移 | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **systemd 服务** | Linux 生产环境 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Windows 服务** | Windows 生产环境 | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **手动部署** | 完全自定义配置 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Kubernetes** | 大规模集群部署 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

---

## 系统要求

### 最低要求

- **操作系统**:
  - Linux: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+
  - macOS: 11 (Big Sur) 或更高
  - Windows: 10/11, Server 2019+

- **Python**: 3.10 或更高版本

- **内存**: 最低 2GB RAM（推荐 4GB+）

- **存储**: 最低 5GB 可用空间（推荐 20GB+）

- **网络**: 需要访问 AI 提供商 API（OpenAI、Anthropic 等）

### 推荐配置

- **CPU**: 4 核心或更多
- **内存**: 8GB RAM 或更多
- **存储**: SSD 硬盘，50GB+ 可用空间
- **网络**: 稳定的互联网连接，带宽 10Mbps+

### 依赖软件

#### 必需
- Python 3.10+
- pip (Python 包管理器)

#### 可选
- **Git**: 用于克隆仓库和插件管理
- **Docker**: 容器化部署
- **Docker Compose**: 多容器编排
- **NSSM**: Windows 服务管理（仅 Windows）
- **systemd**: Linux 服务管理（大多数现代 Linux 发行版自带）

---

## 快速开始

### 最快部署方式（推荐新手）

**Linux/macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/uplifted/uplifted/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/uplifted/uplifted.git
cd uplifted
powershell -ExecutionPolicy Bypass -File install.ps1
```

按照安装向导的提示操作，5 分钟内即可完成部署。

---

## 详细部署指南

### 配置向导部署

配置向导提供交互式的配置过程，适合首次部署。

#### 1. 克隆仓库

```bash
git clone https://github.com/uplifted/uplifted.git
cd uplifted
```

#### 2. 运行配置向导

```bash
# 交互式配置（推荐）
python config_wizard.py

# 使用预设配置文件
python config_wizard.py --profile=production

# 非交互式（使用默认值）
python config_wizard.py --non-interactive
```

#### 3. 配置向导步骤

配置向导会引导您完成以下步骤：

1. **系统环境检测**
   - 检测操作系统和 Python 版本
   - 验证系统资源（CPU、内存）

2. **依赖检查**
   - 检查 Git、构建工具等依赖
   - 验证 Python 包是否已安装

3. **基本配置**
   - 选择环境（development/production/minimal）
   - 配置服务器地址和端口
   - 设置工作进程数量

4. **AI 提供商配置**
   - 配置 OpenAI API 密钥
   - 配置 Anthropic API 密钥
   - 配置其他 AI 提供商（可选）

5. **高级配置**
   - 数据库路径
   - 插件设置
   - 日志配置
   - 安全选项（API 密钥认证、CORS、限流）

6. **生成配置文件**
   - 自动生成 `.env` 文件
   - 生成 `config/config.yaml` 文件
   - 创建必要的目录结构

#### 4. 启动服务

```bash
# 创建虚拟环境（如果尚未创建）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install uv
uv pip install -e .

# 启动服务
python -m server.run_main_server
```

---

### 一键安装部署

一键安装脚本会自动完成所有安装步骤。

#### Linux/macOS 一键安装

**方式 1: 直接下载并执行**
```bash
curl -sSL https://raw.githubusercontent.com/uplifted/uplifted/main/install.sh | bash
```

**方式 2: 下载后执行**
```bash
# 下载安装脚本
wget https://raw.githubusercontent.com/uplifted/uplifted/main/install.sh

# 或使用 curl
curl -O https://raw.githubusercontent.com/uplifted/uplifted/main/install.sh

# 添加执行权限
chmod +x install.sh

# 执行安装
./install.sh
```

**自定义安装路径:**
```bash
# 设置安装目录
export UPLIFTED_INSTALL_DIR="/opt/uplifted"
./install.sh

# 或使用不同分支
export UPLIFTED_BRANCH="develop"
./install.sh
```

#### Windows 一键安装

**PowerShell 安装:**
```powershell
# 克隆仓库
git clone https://github.com/uplifted/uplifted.git
cd uplifted

# 执行安装脚本
powershell -ExecutionPolicy Bypass -File install.ps1
```

**自定义安装路径:**
```powershell
# 设置安装目录
$env:UPLIFTED_INSTALL_DIR = "C:\uplifted"

# 执行安装
powershell -ExecutionPolicy Bypass -File install.ps1
```

#### 安装脚本功能

一键安装脚本会自动完成：

1. ✅ 检查 Python 版本（>=3.10）
2. ✅ 安装系统依赖（Git、构建工具等）
3. ✅ 克隆或更新代码仓库
4. ✅ 创建 Python 虚拟环境
5. ✅ 安装 Python 依赖（使用 uv 加速）
6. ✅ 生成默认配置文件
7. ✅ 创建 systemd/Windows 服务（可选）
8. ✅ 创建启动脚本（start.sh, stop.sh, status.sh）
9. ✅ 添加到系统 PATH（可选）

#### 启动服务

安装完成后，使用生成的启动脚本：

**Linux/macOS:**
```bash
# 进入安装目录
cd ~/.uplifted  # 默认安装路径

# 启动服务
./start.sh

# 停止服务
./stop.sh

# 查看状态
./status.sh
```

**Windows:**
```cmd
# 进入安装目录
cd %USERPROFILE%\.uplifted

# 启动服务
start.bat

# 停止服务
stop.bat

# 查看状态
status.bat
```

---

### Docker 部署

Docker 部署提供最佳的环境一致性和可移植性。

#### 1. 前置准备

确保已安装：
- Docker 20.10+
- Docker Compose 2.0+

```bash
# 验证 Docker 安装
docker --version
docker-compose --version
```

#### 2. 克隆仓库

```bash
git clone https://github.com/uplifted/uplifted.git
cd uplifted
```

#### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env  # 或使用您喜欢的编辑器
```

**必须配置的变量:**
```bash
# 至少配置一个 AI 提供商 API 密钥
OPENAI_API_KEY=sk-...
# 或
ANTHROPIC_API_KEY=sk-ant-...
```

#### 4. 构建和启动

```bash
# 构建镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 仅查看主服务日志
docker-compose logs -f uplifted
```

#### 5. 验证部署

```bash
# 检查容器状态
docker-compose ps

# 检查健康状态
docker-compose exec uplifted /usr/local/bin/healthcheck.sh

# 测试 API
curl http://localhost:7541/status
```

#### 6. 访问服务

- **Main API**: http://localhost:7541
- **API 文档**: http://localhost:7541/docs
- **Tools Server**: http://localhost:8086

#### Docker 常用命令

```bash
# 停止服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器及卷（⚠️ 会删除数据）
docker-compose down -v

# 重启服务
docker-compose restart

# 查看资源使用
docker stats uplifted

# 进入容器 shell
docker-compose exec uplifted bash

# 查看实时日志
docker-compose logs -f --tail=100

# 更新并重启
git pull
docker-compose build
docker-compose up -d
```

#### 开发模式

使用 `docker-compose.override.yml` 启用开发模式：

```bash
# 使用开发模式启动
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# 特点：
# - 挂载源代码目录（热重载）
# - 启用 DEBUG 模式
# - 增加资源限制
```

---

### 手动部署

手动部署提供最大的灵活性和控制权。

#### 1. 系统准备

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    git curl wget \
    build-essential \
    libx11-6 libxtst6 libfreetype6
```

**CentOS/RHEL:**
```bash
sudo yum install -y \
    python3.11 python3-pip \
    git curl wget \
    gcc gcc-c++ make \
    libX11 libXtst freetype
```

**macOS:**
```bash
# 使用 Homebrew
brew install python@3.11 git
```

#### 2. 创建用户（生产环境推荐）

```bash
# 创建专用用户
sudo useradd -r -s /bin/bash -d /opt/uplifted -m uplifted

# 切换到该用户
sudo su - uplifted
```

#### 3. 克隆仓库

```bash
git clone https://github.com/uplifted/uplifted.git
cd uplifted
```

#### 4. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

#### 5. 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装 uv（可选，但推荐，速度更快）
pip install uv

# 使用 uv 安装依赖
uv pip install -e .

# 或使用传统 pip
pip install -e .
```

#### 6. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
nano .env

# 创建必要的目录
mkdir -p config data logs plugins
```

**编辑 `.env` 文件，至少配置:**
```bash
# 环境
UPLIFTED_ENV=production

# 服务器
UPLIFTED__SERVER__HOST=0.0.0.0
UPLIFTED__SERVER__PORT=7541
UPLIFTED__SERVER__WORKERS=4

# AI 提供商（至少一个）
OPENAI_API_KEY=your-api-key-here
# 或
ANTHROPIC_API_KEY=your-api-key-here
```

#### 7. 生成配置文件（可选）

```bash
# 使用配置向导
python config_wizard.py

# 或手动创建
python -c "
from server.uplifted.extensions.config_utils import generate_config_template
generate_config_template('production', 'config/config.yaml')
"
```

#### 8. 测试运行

```bash
# 前台运行（用于测试）
python -m server.run_main_server

# 如果一切正常，按 Ctrl+C 停止
```

#### 9. 配置为服务（见下文）

---

### systemd 服务部署

将 Uplifted 配置为 systemd 服务，实现开机自启和自动重启。

#### 1. 准备服务文件

```bash
# 复制服务文件到 systemd 目录
sudo cp systemd/uplifted.service /etc/systemd/system/

# 编辑服务文件（如果需要自定义）
sudo nano /etc/systemd/system/uplifted.service
```

#### 2. 修改服务文件（如果需要）

```ini
[Unit]
Description=Uplifted AI Agent System
Documentation=https://uplifted.ai/docs
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=uplifted  # 改为您的用户名
Group=uplifted  # 改为您的组名
WorkingDirectory=/opt/uplifted  # 改为您的安装路径

# 环境变量
Environment="PATH=/opt/uplifted/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
Environment="UPLIFTED_ENV=production"
EnvironmentFile=-/etc/uplifted/environment

# 执行命令
ExecStartPre=/bin/sleep 5
ExecStart=/opt/uplifted/venv/bin/python -m server.run_main_server
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

# 重启策略
Restart=on-failure
RestartSec=10s
StartLimitBurst=5
StartLimitInterval=300s

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/uplifted/data /opt/uplifted/logs
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

# 日志
StandardOutput=journal
StandardError=journal
SyslogIdentifier=uplifted

[Install]
WantedBy=multi-user.target
```

#### 3. 启用和启动服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable uplifted

# 启动服务
sudo systemctl start uplifted

# 查看状态
sudo systemctl status uplifted
```

#### 4. 管理服务

```bash
# 停止服务
sudo systemctl stop uplifted

# 重启服务
sudo systemctl restart uplifted

# 查看日志
sudo journalctl -u uplifted -f

# 查看最近的日志
sudo journalctl -u uplifted -n 100

# 禁用服务
sudo systemctl disable uplifted
```

#### 5. 环境变量文件（可选）

创建 `/etc/uplifted/environment` 文件存储环境变量：

```bash
# 创建配置目录
sudo mkdir -p /etc/uplifted

# 创建环境变量文件
sudo nano /etc/uplifted/environment
```

**内容示例:**
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
UPLIFTED__SERVER__WORKERS=8
```

**设置权限:**
```bash
sudo chmod 600 /etc/uplifted/environment
sudo chown uplifted:uplifted /etc/uplifted/environment
```

---

### Windows 服务部署

使用 NSSM (Non-Sucking Service Manager) 将 Uplifted 配置为 Windows 服务。

#### 1. 安装 NSSM

**方式 1: 使用 Chocolatey**
```powershell
choco install nssm
```

**方式 2: 手动下载**
1. 访问 https://nssm.cc/download
2. 下载并解压
3. 将 `nssm.exe` 复制到 `C:\Windows\System32`

#### 2. 安装服务

```powershell
# 设置路径（根据实际情况修改）
$installDir = "$env:USERPROFILE\.uplifted"
$pythonPath = "$installDir\venv\Scripts\python.exe"

# 安装服务
nssm install Uplifted $pythonPath "-m" "server.run_main_server"

# 设置工作目录
nssm set Uplifted AppDirectory $installDir

# 设置显示名称和描述
nssm set Uplifted DisplayName "Uplifted AI Agent System"
nssm set Uplifted Description "Uplifted AI Agent System - Enterprise Security Framework"

# 设置启动类型为自动
nssm set Uplifted Start SERVICE_AUTO_START

# 设置输出日志
nssm set Uplifted AppStdout "$installDir\logs\service-stdout.log"
nssm set Uplifted AppStderr "$installDir\logs\service-stderr.log"

# 设置日志轮转
nssm set Uplifted AppRotateFiles 1
nssm set Uplifted AppRotateBytes 10485760  # 10MB
```

#### 3. 管理服务

```powershell
# 启动服务
net start Uplifted
# 或
Start-Service Uplifted

# 停止服务
net stop Uplifted
# 或
Stop-Service Uplifted

# 重启服务
Restart-Service Uplifted

# 查看服务状态
sc query Uplifted
# 或
Get-Service Uplifted

# 查看日志
Get-Content "$env:USERPROFILE\.uplifted\logs\service-stdout.log" -Tail 50 -Wait
```

#### 4. 卸载服务

```powershell
# 停止服务
net stop Uplifted

# 卸载服务
nssm remove Uplifted confirm
```

---

## 云平台部署

### AWS 部署

#### EC2 实例部署

```bash
# 1. 启动 EC2 实例（Ubuntu 22.04 LTS）
# 最低配置: t3.medium (2 vCPU, 4GB RAM)

# 2. SSH 连接到实例
ssh -i your-key.pem ubuntu@your-instance-ip

# 3. 更新系统
sudo apt update && sudo apt upgrade -y

# 4. 使用一键安装脚本
curl -sSL https://raw.githubusercontent.com/uplifted/uplifted/main/install.sh | bash

# 5. 配置防火墙（安全组）
# 开放端口: 7541 (Main API), 8086 (Tools Server)
```

#### ECS (Docker) 部署

```yaml
# task-definition.json
{
  "family": "uplifted",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "uplifted",
      "image": "your-registry/uplifted:latest",
      "portMappings": [
        {"containerPort": 7541, "protocol": "tcp"},
        {"containerPort": 8086, "protocol": "tcp"}
      ],
      "environment": [
        {"name": "UPLIFTED_ENV", "value": "production"}
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:uplifted/openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/uplifted",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Platform

#### Compute Engine 部署

```bash
# 1. 创建 VM 实例
gcloud compute instances create uplifted-instance \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB

# 2. SSH 连接
gcloud compute ssh uplifted-instance

# 3. 执行安装脚本
curl -sSL https://raw.githubusercontent.com/uplifted/uplifted/main/install.sh | bash

# 4. 配置防火墙规则
gcloud compute firewall-rules create allow-uplifted \
  --allow=tcp:7541,tcp:8086 \
  --source-ranges=0.0.0.0/0
```

#### Cloud Run 部署

```bash
# 1. 构建容器镜像
gcloud builds submit --tag gcr.io/YOUR_PROJECT/uplifted

# 2. 部署到 Cloud Run
gcloud run deploy uplifted \
  --image gcr.io/YOUR_PROJECT/uplifted \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --port 7541 \
  --set-env-vars UPLIFTED_ENV=production \
  --set-secrets OPENAI_API_KEY=openai-key:latest
```

### Azure 部署

#### Virtual Machine 部署

```bash
# 1. 创建 VM
az vm create \
  --resource-group uplifted-rg \
  --name uplifted-vm \
  --image UbuntuLTS \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys

# 2. 开放端口
az vm open-port --resource-group uplifted-rg --name uplifted-vm --port 7541
az vm open-port --resource-group uplifted-rg --name uplifted-vm --port 8086

# 3. SSH 连接并安装
ssh azureuser@<public-ip>
curl -sSL https://raw.githubusercontent.com/uplifted/uplifted/main/install.sh | bash
```

#### Container Instances 部署

```bash
# 创建容器实例
az container create \
  --resource-group uplifted-rg \
  --name uplifted-container \
  --image your-registry/uplifted:latest \
  --cpu 2 \
  --memory 4 \
  --ports 7541 8086 \
  --environment-variables \
    UPLIFTED_ENV=production \
  --secure-environment-variables \
    OPENAI_API_KEY=<your-key>
```

---

## 配置管理

详细的配置管理指南请参考 [CONFIG_MANAGEMENT.md](./CONFIG_MANAGEMENT.md)。

### 配置文件位置

- **环境变量**: `.env`
- **YAML 配置**: `config/config.yaml`
- **数据库**: `data/uplifted.db`
- **日志**: `logs/uplifted.log`
- **插件**: `plugins/`

### 关键配置项

#### 服务器配置

```bash
UPLIFTED__SERVER__HOST=0.0.0.0      # 监听地址
UPLIFTED__SERVER__PORT=7541         # 主服务端口
UPLIFTED__SERVER__WORKERS=4         # 工作进程数
UPLIFTED__SERVER__LOG_LEVEL=INFO    # 日志级别
```

#### AI 提供商

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# 其他提供商...
```

#### 安全配置

```bash
UPLIFTED__SECURITY__API_KEY_REQUIRED=true
UPLIFTED__SECURITY__API_KEY=your-secure-key
UPLIFTED__SECURITY__CORS_ENABLED=true
UPLIFTED__SECURITY__RATE_LIMIT__ENABLED=true
```

### 环境变量优先级

配置加载优先级（从高到低）：

1. 环境变量
2. `.env` 文件
3. `config/config.yaml`
4. 代码默认值

---

## 安全加固

### 1. 使用专用用户运行

```bash
# 创建专用用户
sudo useradd -r -s /bin/bash -d /opt/uplifted -m uplifted

# 设置目录权限
sudo chown -R uplifted:uplifted /opt/uplifted
sudo chmod 750 /opt/uplifted
```

### 2. 限制文件权限

```bash
# 配置文件权限
chmod 600 .env
chmod 600 config/config.yaml

# 日志目录权限
chmod 750 logs/
chmod 640 logs/*.log
```

### 3. 启用 API 密钥认证

```bash
# 在 .env 中配置
UPLIFTED__SECURITY__API_KEY_REQUIRED=true
UPLIFTED__SECURITY__API_KEY=<生成一个强密钥>

# 生成密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. 配置 HTTPS (使用 Nginx 反向代理)

```nginx
# /etc/nginx/sites-available/uplifted
server {
    listen 443 ssl http2;
    server_name uplifted.example.com;

    ssl_certificate /etc/ssl/certs/uplifted.crt;
    ssl_certificate_key /etc/ssl/private/uplifted.key;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://127.0.0.1:7541;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. 防火墙配置

**UFW (Ubuntu):**
```bash
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 443/tcp     # HTTPS
sudo ufw deny 7541/tcp     # 不直接暴露到公网
sudo ufw enable
```

**firewalld (CentOS):**
```bash
sudo firewall-cmd --add-service=ssh --permanent
sudo firewall-cmd --add-service=https --permanent
sudo firewall-cmd --reload
```

### 6. 定期更新

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新 Uplifted
cd /opt/uplifted
git pull
source venv/bin/activate
pip install -U -e .
sudo systemctl restart uplifted
```

---

## 监控和日志

### 日志位置

- **应用日志**: `logs/uplifted.log`
- **systemd 日志**: `journalctl -u uplifted`
- **Docker 日志**: `docker-compose logs uplifted`

### 查看日志

```bash
# 实时查看应用日志
tail -f logs/uplifted.log

# 查看 systemd 日志
sudo journalctl -u uplifted -f

# 查看 Docker 日志
docker-compose logs -f uplifted

# 查看最近 100 行
sudo journalctl -u uplifted -n 100
```

### 日志级别

配置日志级别：
```bash
UPLIFTED__SERVER__LOG_LEVEL=DEBUG   # DEBUG, INFO, WARNING, ERROR
```

### 监控指标

启用 Prometheus 指标（可选）：
```bash
UPLIFTED__MONITORING__ENABLED=true
UPLIFTED__MONITORING__PROMETHEUS_PORT=9090
```

访问指标：`http://localhost:9090/metrics`

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

**检查日志:**
```bash
# systemd
sudo journalctl -u uplifted -n 50

# Docker
docker-compose logs uplifted
```

**常见原因:**
- 端口被占用
- Python 版本不兼容
- 缺少依赖
- 配置文件错误

**解决方法:**
```bash
# 检查端口占用
sudo lsof -i :7541
sudo netstat -tulpn | grep 7541

# 检查 Python 版本
python --version  # 应该 >= 3.10

# 重新安装依赖
pip install -U -e .

# 验证配置
python -c "from server.uplifted.extensions.config_manager import ConfigManager; cm = ConfigManager(); print(cm.get_all())"
```

#### 2. API 无法访问

**检查服务状态:**
```bash
# systemd
sudo systemctl status uplifted

# Docker
docker-compose ps

# 进程
ps aux | grep run_main_server
```

**测试连接:**
```bash
# 本地测试
curl http://localhost:7541/status

# 远程测试
curl http://YOUR_SERVER_IP:7541/status
```

**检查防火墙:**
```bash
# UFW
sudo ufw status

# firewalld
sudo firewall-cmd --list-all
```

#### 3. AI 提供商连接失败

**检查 API 密钥:**
```bash
# 验证环境变量
env | grep -E "(OPENAI|ANTHROPIC)"

# 测试 API 连接
python -c "
import os
import httpx
api_key = os.getenv('OPENAI_API_KEY')
headers = {'Authorization': f'Bearer {api_key}'}
r = httpx.get('https://api.openai.com/v1/models', headers=headers)
print(r.status_code)
"
```

#### 4. 插件无法加载

**检查插件目录:**
```bash
ls -la plugins/

# 验证插件清单
cat plugins/your-plugin/manifest.yaml
```

**查看插件日志:**
```bash
grep "plugin" logs/uplifted.log
```

#### 5. 数据库错误

**检查数据库文件:**
```bash
ls -la data/uplifted.db

# 检查权限
chmod 644 data/uplifted.db

# 备份并重建（⚠️ 会丢失数据）
mv data/uplifted.db data/uplifted.db.backup
# 重启服务会自动创建新数据库
```

### 调试模式

启用调试模式获取更多信息：

```bash
# 环境变量
export UPLIFTED__DEBUG=true
export UPLIFTED__SERVER__LOG_LEVEL=DEBUG

# 或在 .env 中
UPLIFTED__DEBUG=true
UPLIFTED__SERVER__LOG_LEVEL=DEBUG
```

### 获取帮助

1. 查看文档：`docs/`
2. 搜索 Issues：https://github.com/uplifted/uplifted/issues
3. 提交新 Issue（包含日志和错误信息）

---

## 性能优化

### 1. 工作进程数量

根据 CPU 核心数调整：
```bash
# 推荐: CPU 核心数 / 2
UPLIFTED__SERVER__WORKERS=4
```

### 2. 启用缓存（可选）

使用 Redis 缓存：
```bash
# 启动 Redis
docker run -d -p 6379:6379 redis:alpine

# 配置 Uplifted
REDIS_URL=redis://localhost:6379/0
UPLIFTED__CACHE__ENABLED=true
UPLIFTED__CACHE__TTL=3600
```

### 3. 数据库优化

**使用 PostgreSQL（可选，适合大规模部署）:**
```bash
# 启动 PostgreSQL
docker run -d \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=uplifted \
  -p 5432:5432 \
  postgres:15-alpine

# 配置 Uplifted
UPLIFTED__DATABASE__URL=postgresql://postgres:changeme@localhost:5432/uplifted
```

### 4. 资源限制

**systemd 资源限制:**
```ini
[Service]
MemoryMax=4G
CPUQuota=200%  # 2 CPU cores
```

**Docker 资源限制:**
```yaml
services:
  uplifted:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
```

### 5. 负载均衡（高可用部署）

使用 Nginx 负载均衡多个实例：

```nginx
upstream uplifted_backend {
    least_conn;
    server 127.0.0.1:7541;
    server 127.0.0.1:7542;
    server 127.0.0.1:7543;
}

server {
    listen 80;
    location / {
        proxy_pass http://uplifted_backend;
    }
}
```

---

## 升级和回滚

### 升级流程

#### 1. 备份数据

```bash
# 备份数据库
cp data/uplifted.db data/uplifted.db.backup.$(date +%Y%m%d)

# 备份配置
tar czf config-backup-$(date +%Y%m%d).tar.gz config/ .env

# 备份插件
tar czf plugins-backup-$(date +%Y%m%d).tar.gz plugins/
```

#### 2. 更新代码

```bash
# 拉取最新代码
git fetch --tags
git pull origin main

# 或切换到特定版本
git checkout v1.2.0
```

#### 3. 更新依赖

```bash
# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install -U -e .
```

#### 4. 运行迁移（如果有）

```bash
# 检查是否有数据库迁移
python -m server.uplifted.migrations.migrate
```

#### 5. 重启服务

```bash
# systemd
sudo systemctl restart uplifted

# Docker
docker-compose down
docker-compose build
docker-compose up -d

# 手动
# 停止旧进程，然后重新启动
```

#### 6. 验证升级

```bash
# 检查服务状态
sudo systemctl status uplifted

# 测试 API
curl http://localhost:7541/status

# 查看日志
sudo journalctl -u uplifted -f
```

### 回滚流程

如果升级出现问题：

```bash
# 1. 停止服务
sudo systemctl stop uplifted

# 2. 回退代码
git checkout <previous-version>

# 3. 恢复依赖
pip install -e .

# 4. 恢复数据（如果需要）
cp data/uplifted.db.backup.<date> data/uplifted.db

# 5. 恢复配置（如果需要）
tar xzf config-backup-<date>.tar.gz

# 6. 重启服务
sudo systemctl start uplifted
```

### 零停机升级（高级）

使用负载均衡器进行滚动升级：

1. 从负载均衡器移除实例 1
2. 升级实例 1
3. 将实例 1 加回负载均衡器
4. 验证实例 1 正常工作
5. 重复步骤 1-4 对其他实例进行升级

---

## 附录

### A. 端口列表

| 端口 | 服务 | 说明 |
|-----|------|-----|
| 7541 | Main API | 主 API 服务 |
| 8086 | Tools Server | 工具服务器 |
| 9090 | Prometheus | 监控指标（可选） |

### B. 目录结构

```
uplifted/
├── config/              # 配置文件
│   └── config.yaml
├── data/               # 数据库和持久化数据
│   └── uplifted.db
├── logs/               # 日志文件
│   └── uplifted.log
├── plugins/            # 插件目录
├── server/             # 服务器代码
│   └── uplifted/
├── docker/             # Docker 配置
├── systemd/            # systemd 配置
├── .env                # 环境变量
├── docker-compose.yml  # Docker Compose 配置
├── install.sh          # Linux/macOS 安装脚本
├── install.ps1         # Windows 安装脚本
└── config_wizard.py    # 配置向导
```

### C. 有用的命令速查表

```bash
# 查看服务状态
sudo systemctl status uplifted

# 重启服务
sudo systemctl restart uplifted

# 查看日志
sudo journalctl -u uplifted -f

# 测试 API
curl http://localhost:7541/status

# 进入虚拟环境
source venv/bin/activate

# 更新代码
git pull && pip install -U -e .

# 备份数据
tar czf backup-$(date +%Y%m%d).tar.gz data/ config/ .env

# 检查端口
sudo lsof -i :7541

# 查看进程
ps aux | grep run_main_server

# Docker 命令
docker-compose up -d
docker-compose logs -f
docker-compose restart
docker-compose down
```

---

## 相关文档

- [配置管理指南](./CONFIG_MANAGEMENT.md)
- [Docker 部署指南](../docker/README.md)
- [Week 2 总结](./WEEK2_SUMMARY.md)
- [项目进度](./PROJECT_PROGRESS.md)

---

**最后更新**: 2024-10

**版本**: 1.0.0

如有问题，请访问: https://github.com/uplifted/uplifted/issues
