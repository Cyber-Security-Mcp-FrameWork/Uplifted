# Uplifted 测试指南

**版本**: 1.0.0
**更新日期**: 2025-10-28
**状态**: 完成

## 目录

1. [概述](#概述)
2. [测试框架](#测试框架)
3. [测试类型](#测试类型)
4. [运行测试](#运行测试)
5. [编写测试](#编写测试)
6. [测试覆盖率](#测试覆盖率)
7. [性能测试](#性能测试)
8. [安全审计](#安全审计)
9. [持续集成](#持续集成)
10. [故障排查](#故障排查)

---

## 概述

Uplifted 项目采用全面的测试策略，确保代码质量、可靠性和性能：

### 测试原则

1. **高覆盖率**: 目标 >80% 代码覆盖率
2. **快速反馈**: 单元测试快速执行（<5秒）
3. **隔离测试**: 每个测试独立运行，无依赖
4. **清晰命名**: 测试名称清楚描述测试内容
5. **全面断言**: 每个测试包含充分的断言

### 测试统计

- **总测试数**: 150+
- **单元测试**: 100+
- **集成测试**: 30+
- **性能测试**: 20+
- **代码覆盖率**: 目标 >80%

---

## 测试框架

### 核心工具

```python
# 核心测试框架
pytest                 # 测试框架
pytest-asyncio        # 异步测试支持
pytest-cov            # 覆盖率报告
pytest-mock           # Mock 支持

# 性能测试
pytest-benchmark      # 基准测试
memory-profiler       # 内存分析

# 代码质量
bandit                # 安全扫描
safety                # 依赖漏洞扫描
mypy                  # 类型检查
```

### 项目结构

```
server/tests/
├── __init__.py           # 测试包
├── conftest.py           # 共享 fixtures
├── unit/                 # 单元测试
│   ├── test_plugin_manifest.py
│   ├── test_config_loaders.py
│   └── ...
├── integration/          # 集成测试
│   ├── test_plugin_system_integration.py
│   └── ...
├── performance/          # 性能测试
│   ├── test_plugin_performance.py
│   └── ...
├── reports/              # 测试报告
└── logs/                 # 测试日志
```

---

## 测试类型

### 1. 单元测试

测试单个功能或类的行为。

**示例**:

```python
import pytest
from uplifted.extensions.plugin_manifest import PluginManifest

class TestPluginManifest:
    """插件清单单元测试"""

    def test_create_manifest(self):
        """测试创建清单"""
        manifest = PluginManifest(
            metadata=PluginMetadata(
                name="test_plugin",
                version="1.0.0",
                description="Test",
                author="Test"
            ),
            category=PluginCategory.UTILITY,
            entry_point="main.py",
            main_class="TestPlugin"
        )

        assert manifest.metadata.name == "test_plugin"
        assert manifest.category == PluginCategory.UTILITY
```

**运行单元测试**:

```bash
# 所有单元测试
python run_tests.py --unit

# 特定模块
pytest server/tests/unit/test_plugin_manifest.py -v

# 特定测试
pytest server/tests/unit/test_plugin_manifest.py::TestPluginManifest::test_create_manifest -v
```

### 2. 集成测试

测试多个模块的集成和交互。

**示例**:

```python
@pytest.mark.integration
@pytest.mark.plugin
class TestPluginLoadingFlow:
    """插件加载流程集成测试"""

    def test_plugin_lifecycle(self):
        """测试完整的插件生命周期"""
        # 1. 加载清单
        manifest = PluginManifest.from_json_file("plugin/manifest.json")

        # 2. 验证清单
        errors = manifest.validate()
        assert errors == []

        # 3. 激活插件
        plugin = create_plugin(config={})
        plugin.activate()

        # 4. 执行工具
        result = plugin.greet("User")
        assert result == "Hello, User!"

        # 5. 停用插件
        plugin.deactivate()
```

**运行集成测试**:

```bash
# 所有集成测试
python run_tests.py --integration

# 特定集成测试
pytest server/tests/integration/ -m integration -v
```

### 3. 性能测试

测试性能和基准。

**示例**:

```python
@pytest.mark.performance
class TestPluginPerformance:
    """插件性能测试"""

    def test_manifest_creation_performance(self, benchmark):
        """测试清单创建性能"""

        def create_manifest():
            return PluginManifest(
                metadata=PluginMetadata(
                    name="perf_test",
                    version="1.0.0",
                    description="Performance test",
                    author="Test"
                ),
                category=PluginCategory.UTILITY,
                entry_point="plugin.py",
                main_class="PerfPlugin"
            )

        result = benchmark(create_manifest)
        assert result.metadata.name == "perf_test"
```

**运行性能测试**:

```bash
# 所有性能测试
python run_tests.py --performance

# 查看基准结果
pytest server/tests/performance/ --benchmark-only --benchmark-autosave
```

---

## 运行测试

### 使用测试脚本

项目提供了便捷的测试运行脚本 `run_tests.py`：

```bash
# 运行所有测试
python run_tests.py

# 运行单元测试
python run_tests.py --unit

# 运行集成测试
python run_tests.py --integration

# 运行性能测试
python run_tests.py --performance

# 快速测试（跳过慢速测试）
python run_tests.py --quick

# 运行完整测试套件
python run_tests.py --suite

# 生成覆盖率报告
python run_tests.py --coverage

# 并行运行（4个进程）
python run_tests.py --parallel 4

# 运行特定模块
python run_tests.py --module plugin

# 列出所有测试
python run_tests.py --list

# 重新运行失败的测试
python run_tests.py --failed
```

### 使用 pytest 直接运行

```bash
# 运行所有测试
pytest server/tests/

# 运行特定文件
pytest server/tests/unit/test_plugin_manifest.py

# 运行特定测试类
pytest server/tests/unit/test_plugin_manifest.py::TestPluginManifest

# 运行特定测试方法
pytest server/tests/unit/test_plugin_manifest.py::TestPluginManifest::test_create_manifest

# 使用标记过滤
pytest -m unit           # 只运行单元测试
pytest -m integration    # 只运行集成测试
pytest -m "not slow"     # 跳过慢速测试

# 详细输出
pytest -v

# 超详细输出
pytest -vv

# 显示本地变量
pytest -l

# 停在第一个失败
pytest -x

# 显示测试摘要
pytest -ra

# 并行运行
pytest -n auto           # 自动使用所有 CPU
pytest -n 4              # 使用 4 个进程
```

---

## 编写测试

### 测试命名约定

```python
# 文件命名: test_*.py
test_plugin_manifest.py
test_config_loaders.py

# 类命名: Test*
class TestPluginManifest:
    pass

class TestConfigLoader:
    pass

# 方法命名: test_*
def test_create_manifest():
    pass

def test_load_config():
    pass
```

### 使用 Fixtures

```python
import pytest

@pytest.fixture
def sample_manifest():
    """提供示例清单"""
    return PluginManifest(
        metadata=PluginMetadata(
            name="sample",
            version="1.0.0",
            description="Sample",
            author="Test"
        ),
        category=PluginCategory.UTILITY,
        entry_point="plugin.py",
        main_class="SamplePlugin"
    )

def test_manifest_serialization(sample_manifest):
    """测试清单序列化"""
    json_str = sample_manifest.to_json()
    assert isinstance(json_str, str)
    assert "sample" in json_str
```

### 参数化测试

```python
@pytest.mark.parametrize("input_value,expected", [
    ("true", True),
    ("false", False),
    ("123", 123),
    ("12.5", 12.5),
    ("hello", "hello")
])
def test_parse_value(input_value, expected):
    """测试值解析"""
    loader = EnvConfigLoader()
    result = loader._parse_value(input_value)
    assert result == expected
```

### 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """测试异步功能"""
    result = await some_async_function()
    assert result is not None
```

### Mock 和 Stub

```python
from unittest.mock import Mock, AsyncMock, patch

def test_with_mock():
    """测试使用 Mock"""
    mock_db = Mock()
    mock_db.get_user.return_value = User(id="123", name="Test")

    service = UserService(mock_db)
    user = service.get_user("123")

    assert user.name == "Test"
    mock_db.get_user.assert_called_once_with("123")

@pytest.mark.asyncio
async def test_with_async_mock():
    """测试使用 AsyncMock"""
    mock_api = AsyncMock()
    mock_api.fetch_data.return_value = {"status": "success"}

    result = await mock_api.fetch_data()
    assert result["status"] == "success"
```

### 测试标记

```python
import pytest

@pytest.mark.unit
def test_unit_level():
    """单元测试标记"""
    pass

@pytest.mark.integration
def test_integration_level():
    """集成测试标记"""
    pass

@pytest.mark.slow
def test_slow_operation():
    """慢速测试标记"""
    pass

@pytest.mark.skipif(condition, reason="Reason")
def test_conditional():
    """条件跳过"""
    pass

@pytest.mark.xfail(reason="Known issue")
def test_expected_failure():
    """预期失败"""
    pass
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 使用测试脚本
python run_tests.py --coverage

# 使用 pytest
pytest --cov=server/uplifted --cov-report=html --cov-report=term

# 只显示缺失的行
pytest --cov=server/uplifted --cov-report=term-missing

# 生成 XML 报告（CI/CD）
pytest --cov=server/uplifted --cov-report=xml
```

### 查看覆盖率报告

```bash
# 终端报告
pytest --cov=server/uplifted --cov-report=term

# HTML 报告（推荐）
pytest --cov=server/uplifted --cov-report=html
# 打开 server/tests/coverage_html/index.html
```

### 覆盖率目标

| 模块 | 目标覆盖率 | 当前状态 |
|------|------------|----------|
| 插件系统 | >85% | ✓ 达标 |
| 配置管理 | >85% | ✓ 达标 |
| 核心模块 | >80% | ✓ 达标 |
| API 层 | >75% | 进行中 |
| **总体** | **>80%** | **目标中** |

---

## 性能测试

### 基准测试

```python
def test_benchmark_example(benchmark):
    """基准测试示例"""
    result = benchmark(function_to_test, arg1, arg2)
    assert result is not None
```

### 比较基准

```bash
# 保存基准
pytest --benchmark-autosave

# 与之前比较
pytest --benchmark-compare=0001

# 只显示比较
pytest --benchmark-compare-fail=min:5%
```

### 内存分析

```python
import memory_profiler

@profile
def test_memory_usage():
    """测试内存使用"""
    large_list = [i for i in range(1000000)]
    return large_list
```

---

## 安全审计

### 运行安全审计

```bash
# 完整安全审计
python security_audit.py

# 只扫描依赖
python security_audit.py --dependencies-only

# 只扫描代码
python security_audit.py --code-only

# 生成详细报告
python security_audit.py --detailed --output security_report.txt
```

### 安全检查项

1. **依赖漏洞扫描** (Safety)
   - 检查已知的依赖漏洞
   - 建议升级版本

2. **代码安全扫描** (Bandit)
   - SQL 注入风险
   - 硬编码密码
   - 不安全的函数使用
   - 权限问题

3. **敏感信息检测**
   - API 密钥
   - 密码
   - 令牌
   - 私钥

4. **文件权限检查**
   - 配置文件权限
   - 密钥文件权限

5. **配置安全检查**
   - .env 文件保护
   - 加密配置使用
   - 密钥管理

---

## 持续集成

### GitHub Actions 配置

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.10

    - name: Install dependencies
      run: |
        pip install -r server/requirements-test.txt

    - name: Run tests
      run: |
        python run_tests.py --coverage

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./server/tests/coverage.xml
```

### 测试矩阵

```yaml
strategy:
  matrix:
    python-version: [3.10, 3.11, 3.12]
    os: [ubuntu-latest, windows-latest, macos-latest]
```

---

## 故障排查

### 常见问题

#### 1. 测试失败：Import Error

**问题**: `ModuleNotFoundError: No module named 'uplifted'`

**解决**:
```bash
# 确保在项目根目录
cd /path/to/Uplifted

# 设置 PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:${PWD}/server"

# 或使用 pytest
pytest server/tests/
```

#### 2. 异步测试失败

**问题**: `RuntimeError: Event loop is closed`

**解决**:
```python
# 确保使用 pytest-asyncio
@pytest.mark.asyncio
async def test_async():
    pass

# 检查 conftest.py 中的 event_loop fixture
```

#### 3. 覆盖率报告为空

**问题**: 覆盖率报告显示 0%

**解决**:
```bash
# 检查源代码路径
pytest --cov=server/uplifted --cov-report=term

# 检查 .coveragerc 配置
cat .coveragerc
```

#### 4. 性能测试超时

**问题**: 性能测试运行时间过长

**解决**:
```python
# 使用 pytest-timeout
@pytest.mark.timeout(10)  # 10秒超时
def test_performance():
    pass
```

### 调试技巧

```bash
# 进入调试模式
pytest --pdb

# 在失败时进入调试
pytest --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb

# 显示print输出
pytest -s

# 显示详细的断言信息
pytest -vv

# 显示本地变量
pytest -l --tb=long
```

---

## 最佳实践

### 1. 测试隔离

```python
# ✓ 好的做法
def test_isolated():
    """每个测试独立"""
    data = create_test_data()
    result = process_data(data)
    assert result is not None

# ✗ 避免
class TestBad:
    shared_state = []  # 避免共享状态

    def test_one(self):
        self.shared_state.append(1)

    def test_two(self):
        # 依赖于 test_one 的结果
        assert len(self.shared_state) > 0
```

### 2. 清晰的断言

```python
# ✓ 好的做法
def test_clear_assertion():
    """清晰的断言消息"""
    result = calculate(10, 5)
    assert result == 15, f"Expected 15, got {result}"

# ✗ 避免
def test_vague():
    assert calculate(10, 5)  # 不清楚预期是什么
```

### 3. 使用 Fixtures

```python
# ✓ 好的做法
@pytest.fixture
def db_connection():
    """提供数据库连接"""
    conn = create_connection()
    yield conn
    conn.close()

def test_with_fixture(db_connection):
    """使用 fixture"""
    result = db_connection.query("SELECT 1")
    assert result is not None

# ✗ 避免
def test_manual_setup():
    """手动设置和清理"""
    conn = create_connection()
    result = conn.query("SELECT 1")
    conn.close()
    assert result is not None
```

### 4. 测试边界条件

```python
def test_boundary_conditions():
    """测试边界条件"""
    # 空输入
    assert process([]) == []

    # 单个元素
    assert process([1]) == [1]

    # 大量元素
    assert len(process(range(10000))) == 10000

    # 无效输入
    with pytest.raises(ValueError):
        process(None)
```

---

## 资源

### 文档
- [pytest 文档](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)

### 工具
- [Bandit](https://bandit.readthedocs.io/) - 代码安全扫描
- [Safety](https://pyup.io/safety/) - 依赖漏洞扫描
- [Coverage.py](https://coverage.readthedocs.io/) - 覆盖率工具

### 内部文档
- [Week 7-8 总结](./WEEK7_8_SUMMARY.md)
- [项目进度](./PROJECT_PROGRESS.md)
- [架构文档](./ARCHITECTURE.md)

---

**文档维护**: Uplifted Team
**最后更新**: 2025-10-28
