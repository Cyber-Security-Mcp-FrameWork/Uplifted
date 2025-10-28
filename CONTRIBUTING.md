# Contributing to Uplifted

首先，感谢你考虑为 Uplifted 做出贡献！正是像你这样的人让 Uplifted 成为一个优秀的工具。

## 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发设置](#开发设置)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [发布流程](#发布流程)

---

## 行为准则

本项目及其所有参与者均受[行为准则](CODE_OF_CONDUCT.md)约束。参与本项目即表示你同意遵守其条款。

简而言之：

- **尊重他人**: 尊重不同的观点和经验
- **接受建设性批评**: 以开放和专业的态度接受反馈
- **关注社区最佳利益**: 考虑对整个社区的影响
- **保持友好和耐心**: 帮助他人学习和成长

---

## 如何贡献

### 报告 Bug

Bug 报告帮助我们改进 Uplifted。提交 bug 前，请：

1. **检查现有 Issues**: 确保 bug 未被报告
2. **使用最新版本**: 确认问题在最新版本中仍存在
3. **收集信息**: 准备详细的复现步骤

**Bug 报告应包含**:

- **清晰的标题**: 简洁描述问题
- **环境信息**:
  - OS 版本
  - Python 版本
  - Uplifted 版本
- **复现步骤**: 详细的步骤说明
- **预期行为**: 你期望发生什么
- **实际行为**: 实际发生了什么
- **日志和截图**: 相关的错误信息
- **可能的解决方案**: (可选) 你的想法

**示例**:

```markdown
## Bug 描述
配置加载器在 Windows 上无法处理路径

## 环境
- OS: Windows 11
- Python: 3.10.8
- Uplifted: 0.8.0

## 复现步骤
1. 创建配置文件 `C:\config\app.json`
2. 运行 `loader = JSONConfigLoader()`
3. 调用 `loader.load("C:\config\app.json")`

## 预期行为
配置应该成功加载

## 实际行为
抛出 `FileNotFoundError` 异常

## 错误信息
```
FileNotFoundError: [Errno 2] No such file or directory: 'C:configapp.json'
```

## 可能的解决方案
需要使用 `os.path.join()` 而不是字符串拼接
```

### 建议新功能

我们欢迎功能建议！提交建议前，请：

1. **检查路线图**: 查看功能是否已在计划中
2. **搜索现有建议**: 避免重复
3. **考虑范围**: 功能是否符合项目目标

**功能建议应包含**:

- **清晰的用例**: 为什么需要这个功能
- **详细描述**: 功能如何工作
- **API 设计**: (可选) 建议的接口
- **替代方案**: 考虑过的其他方法
- **影响分析**: 对现有功能的影响

### 改进文档

文档改进总是受欢迎的！你可以：

- 修正拼写和语法错误
- 改进现有文档的清晰度
- 添加缺失的文档
- 翻译文档到其他语言
- 添加更多代码示例

### 提交代码

查看 [Issues](https://github.com/uplifted/uplifted/issues) 中标记为 `good first issue` 或 `help wanted` 的问题。

---

## 开发设置

### 前置要求

- Python 3.10+
- Git
- (可选) Docker

### 克隆仓库

```bash
git clone https://github.com/uplifted/uplifted.git
cd uplifted
```

### 创建虚拟环境

```bash
# Linux/macOS
python -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 安装依赖

```bash
# 开发依赖
pip install -r server/requirements-test.txt

# 可选：安装开发工具
pip install black isort flake8 mypy pre-commit
```

### 配置 Git Hooks (推荐)

```bash
pre-commit install
```

这会在每次提交前自动运行代码格式化和检查。

---

## 代码规范

### Python 代码风格

我们遵循 [PEP 8](https://pep8.org/) 和 [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)。

#### 格式化

使用 **Black** 进行代码格式化：

```bash
black server/uplifted/
```

**配置** (`pyproject.toml`):
```toml
[tool.black]
line-length = 100
target-version = ['py310']
```

#### 导入排序

使用 **isort** 排序导入：

```bash
isort server/uplifted/
```

**配置** (`pyproject.toml`):
```toml
[tool.isort]
profile = "black"
line_length = 100
```

#### Linting

使用 **flake8** 进行 linting：

```bash
flake8 server/uplifted/
```

**配置** (`.flake8`):
```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = .git,__pycache__,venv
```

### 类型提示

**所有新代码必须包含类型提示**:

```python
# ✓ 好的做法
def load_config(file_path: str, validate: bool = True) -> Dict[str, Any]:
    """加载配置文件"""
    ...

# ✗ 避免
def load_config(file_path, validate=True):
    """加载配置文件"""
    ...
```

使用 **mypy** 进行类型检查：

```bash
mypy server/uplifted/ --ignore-missing-imports
```

### 文档字符串

使用 **Google 风格**的文档字符串：

```python
def process_data(data: List[Dict[str, Any]], filter_empty: bool = False) -> List[Dict[str, Any]]:
    """
    处理输入数据并返回过滤后的结果

    此函数接受数据列表，应用指定的过滤规则，并返回处理后的数据。

    参数:
        data: 包含字典的列表，每个字典代表一条数据记录
        filter_empty: 是否过滤空值，默认为 False

    返回:
        处理后的数据列表

    引发:
        ValueError: 如果 data 为 None
        TypeError: 如果 data 不是列表

    示例:
        >>> data = [{"name": "Alice", "age": 30}, {"name": "", "age": 25}]
        >>> process_data(data, filter_empty=True)
        [{"name": "Alice", "age": 30}]
    """
    if data is None:
        raise ValueError("data cannot be None")

    # 实现逻辑...
```

### 命名规范

- **模块**: `lowercase_with_underscores.py`
- **类**: `CapitalizedWords`
- **函数/方法**: `lowercase_with_underscores()`
- **常量**: `UPPERCASE_WITH_UNDERSCORES`
- **私有**: `_leading_underscore`

---

## 测试指南

### 测试要求

**所有新功能必须包含测试**。我们的目标是保持 >85% 的代码覆盖率。

### 运行测试

```bash
# 所有测试
python run_tests.py

# 单元测试
python run_tests.py --unit

# 集成测试
python run_tests.py --integration

# 特定测试文件
pytest server/tests/unit/test_plugin_manifest.py -v

# 特定测试
pytest server/tests/unit/test_plugin_manifest.py::TestPluginManifest::test_create_manifest -v
```

### 编写测试

#### 测试结构

```python
import pytest
from uplifted.extensions.plugin_manifest import PluginManifest, PluginMetadata


class TestPluginManifest:
    """插件清单测试"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.manifest = PluginManifest(
            metadata=PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                description="Test",
                author="Test"
            ),
            ...
        )

    def teardown_method(self):
        """每个测试方法后执行"""
        pass

    def test_create_manifest(self):
        """测试创建清单"""
        # Arrange (准备)
        expected_name = "test_plugin"

        # Act (执行)
        actual_name = self.manifest.metadata.name

        # Assert (断言)
        assert actual_name == expected_name
```

#### 使用 Fixtures

```python
@pytest.fixture
def sample_config():
    """提供示例配置"""
    return {
        "database": {
            "host": "localhost",
            "port": 5432
        }
    }


def test_load_config(sample_config):
    """测试加载配置"""
    loader = ConfigLoader()
    result = loader.load(sample_config)
    assert result["database"]["host"] == "localhost"
```

#### 参数化测试

```python
@pytest.mark.parametrize("input_value,expected", [
    ("true", True),
    ("false", False),
    ("123", 123),
    ("hello", "hello")
])
def test_parse_value(input_value, expected):
    """测试值解析"""
    loader = EnvConfigLoader()
    result = loader._parse_value(input_value)
    assert result == expected
```

#### 异步测试

```python
@pytest.mark.asyncio
async def test_async_operation():
    """测试异步操作"""
    result = await some_async_function()
    assert result is not None
```

### 测试覆盖率

```bash
# 生成覆盖率报告
python run_tests.py --coverage

# 查看 HTML 报告
# 打开 server/tests/coverage_html/index.html
```

---

## 提交规范

### Commit Message 格式

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Type

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（不是新功能也不是 bug 修复）
- `perf`: 性能优化
- `test`: 添加或修改测试
- `chore`: 构建过程或辅助工具的变动

#### Scope (可选)

- `plugin`: 插件系统
- `config`: 配置管理
- `deploy`: 部署
- `docs`: 文档
- `test`: 测试

#### 示例

```bash
# 新功能
git commit -m "feat(plugin): add support for async plugin initialization"

# Bug 修复
git commit -m "fix(config): handle Windows path separators correctly"

# 文档
git commit -m "docs(testing): add performance testing examples"

# 详细说明
git commit -m "feat(plugin): add plugin dependency resolution

Implement automatic dependency resolution for plugins using
topological sorting. This allows plugins to declare dependencies
on other plugins and ensures they are loaded in the correct order.

Closes #123"
```

---

## Pull Request 流程

### 创建 Pull Request

1. **Fork 仓库**
   ```bash
   # 在 GitHub 上点击 Fork
   git clone https://github.com/YOUR_USERNAME/uplifted.git
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/my-awesome-feature
   # 或
   git checkout -b fix/issue-123
   ```

3. **进行修改**
   - 编写代码
   - 添加测试
   - 更新文档

4. **运行测试**
   ```bash
   python run_tests.py
   python security_audit.py
   ```

5. **提交修改**
   ```bash
   git add .
   git commit -m "feat: add my awesome feature"
   ```

6. **推送到 GitHub**
   ```bash
   git push origin feature/my-awesome-feature
   ```

7. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 链接相关 Issue

### PR 检查清单

在提交 PR 前，确保：

- [ ] 代码通过所有测试
- [ ] 添加了新功能的测试
- [ ] 更新了相关文档
- [ ] 代码符合风格指南
- [ ] Commit message 遵循规范
- [ ] PR 描述清晰
- [ ] 已签署 CLA (如果需要)

### PR 模板

```markdown
## 描述

<!-- 简要描述此 PR 的内容 -->

## 相关 Issue

Closes #issue_number

## 修改类型

- [ ] Bug 修复
- [ ] 新功能
- [ ] 重大变更
- [ ] 文档更新

## 测试

<!-- 描述你如何测试这些修改 -->

## 检查清单

- [ ] 我的代码遵循项目的代码风格
- [ ] 我已进行自我审查
- [ ] 我已添加必要的注释
- [ ] 我已更新相关文档
- [ ] 我的修改没有产生新的警告
- [ ] 我已添加测试证明修复有效或功能正常
- [ ] 新的和现有的单元测试都通过了
- [ ] 任何依赖的修改都已合并和发布

## 截图 (如果适用)

<!-- 添加截图帮助解释你的修改 -->
```

### 代码审查

PR 将由维护者审查。他们可能会：

- 请求修改
- 提出建议
- 批准 PR

**作为 PR 作者**:
- 积极回应反馈
- 进行请求的修改
- 保持讨论专业和友好

**作为审查者**:
- 提供建设性反馈
- 关注代码质量和项目标准
- 尊重作者的努力

---

## 发布流程

发布由维护者管理。流程如下：

1. **版本计划**: 确定下一版本的内容
2. **功能开发**: 完成所有计划功能
3. **测试**: 全面测试
4. **文档更新**: 更新 CHANGELOG 和文档
5. **发布**: 创建 GitHub Release
6. **公告**: 通知社区

详见 [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)。

---

## 社区

### 沟通渠道

- **GitHub Issues**: Bug 报告和功能请求
- **GitHub Discussions**: 一般讨论和问题
- **Email**: [uplifted@example.com](mailto:uplifted@example.com)

### 获取帮助

如果你需要帮助：

1. 查看 [文档](./docs/)
2. 搜索现有 Issues
3. 在 Discussions 中提问
4. 联系维护者

---

## 许可证

贡献到 Uplifted 即表示你同意你的贡献将在与项目相同的许可证下发布。

---

## 致谢

感谢所有为 Uplifted 做出贡献的人！

- [贡献者列表](https://github.com/uplifted/uplifted/graphs/contributors)

---

**最后更新**: 2025-10-28

**问题？** 请在 [Discussions](https://github.com/uplifted/uplifted/discussions) 中提问。
