"""
缓存模块单元测试
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from uplifted.cache.managers import CacheManager, RedisCacheManager, MemoryCacheManager
from uplifted.cache.decorators import cache_result, invalidate_cache
from uplifted.cache.exceptions import CacheError, ConnectionError, SerializationError


@pytest.mark.asyncio
class TestCacheManager:
    """缓存管理器基类测试"""
    
    def setup_method(self):
        self.cache_manager = CacheManager()
    
    async def test_abstract_methods(self):
        """测试抽象方法"""
        # 基类的抽象方法应该抛出NotImplementedError
        with pytest.raises(NotImplementedError):
            await self.cache_manager.get("key")
        
        with pytest.raises(NotImplementedError):
            await self.cache_manager.set("key", "value")
        
        with pytest.raises(NotImplementedError):
            await self.cache_manager.delete("key")
        
        with pytest.raises(NotImplementedError):
            await self.cache_manager.exists("key")
        
        with pytest.raises(NotImplementedError):
            await self.cache_manager.clear()


@pytest.mark.asyncio
class TestRedisCacheManager:
    """Redis缓存管理器测试"""
    
    def setup_method(self):
        self.config = {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None,
            'max_connections': 10
        }
        self.cache_manager = RedisCacheManager(self.config)
    
    async def test_initialize_success(self):
        """测试成功初始化Redis连接"""
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis
            
            await self.cache_manager.initialize()
            
            assert self.cache_manager.redis is mock_redis
            mock_from_url.assert_called_once()
    
    async def test_initialize_connection_error(self):
        """测试Redis连接失败"""
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")
            
            with pytest.raises(ConnectionError, match="Redis连接失败"):
                await self.cache_manager.initialize()
    
    async def test_close_connection(self):
        """测试关闭Redis连接"""
        # 先初始化
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            # 测试关闭
            await self.cache_manager.close()
            
            mock_redis.close.assert_called_once()
            mock_redis.wait_closed.assert_called_once()
            assert self.cache_manager.redis is None
    
    async def test_get_existing_key(self):
        """测试获取存在的键"""
        key = "test_key"
        value = {"data": "test_value"}
        serialized_value = json.dumps(value)
        
        # 初始化Redis
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = serialized_value.encode()
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.get(key)
            
            assert result == value
            mock_redis.get.assert_called_once_with(key)
    
    async def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        key = "nonexistent_key"
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.get(key)
            
            assert result is None
            mock_redis.get.assert_called_once_with(key)
    
    async def test_get_with_default(self):
        """测试获取不存在的键并返回默认值"""
        key = "nonexistent_key"
        default_value = "default"
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.get.return_value = None
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.get(key, default=default_value)
            
            assert result == default_value
    
    async def test_set_with_ttl(self):
        """测试设置键值对并指定TTL"""
        key = "test_key"
        value = {"data": "test_value"}
        ttl = 3600
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.setex.return_value = True
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.set(key, value, ttl=ttl)
            
            assert result is True
            mock_redis.setex.assert_called_once_with(key, ttl, json.dumps(value))
    
    async def test_set_without_ttl(self):
        """测试设置键值对不指定TTL"""
        key = "test_key"
        value = {"data": "test_value"}
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.set.return_value = True
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.set(key, value)
            
            assert result is True
            mock_redis.set.assert_called_once_with(key, json.dumps(value))
    
    async def test_delete_existing_key(self):
        """测试删除存在的键"""
        key = "test_key"
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.delete.return_value = 1  # 删除了1个键
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.delete(key)
            
            assert result is True
            mock_redis.delete.assert_called_once_with(key)
    
    async def test_delete_nonexistent_key(self):
        """测试删除不存在的键"""
        key = "nonexistent_key"
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.delete.return_value = 0  # 没有删除任何键
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.delete(key)
            
            assert result is False
    
    async def test_exists_true(self):
        """测试检查存在的键"""
        key = "test_key"
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.exists.return_value = 1
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.exists(key)
            
            assert result is True
            mock_redis.exists.assert_called_once_with(key)
    
    async def test_exists_false(self):
        """测试检查不存在的键"""
        key = "nonexistent_key"
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.exists.return_value = 0
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.exists(key)
            
            assert result is False
    
    async def test_clear_all(self):
        """测试清空所有缓存"""
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.flushdb.return_value = True
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.clear()
            
            assert result is True
            mock_redis.flushdb.assert_called_once()
    
    async def test_get_many(self):
        """测试批量获取"""
        keys = ["key1", "key2", "key3"]
        values = [
            json.dumps({"data": "value1"}).encode(),
            None,  # key2不存在
            json.dumps({"data": "value3"}).encode()
        ]
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.mget.return_value = values
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.get_many(keys)
            
            expected = {
                "key1": {"data": "value1"},
                "key2": None,
                "key3": {"data": "value3"}
            }
            assert result == expected
            mock_redis.mget.assert_called_once_with(*keys)
    
    async def test_set_many(self):
        """测试批量设置"""
        data = {
            "key1": {"data": "value1"},
            "key2": {"data": "value2"}
        }
        ttl = 3600
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.mset.return_value = True
            mock_redis.expire.return_value = True
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.set_many(data, ttl=ttl)
            
            assert result is True
            # 验证mset调用
            expected_mapping = {k: json.dumps(v) for k, v in data.items()}
            mock_redis.mset.assert_called_once_with(expected_mapping)
            # 验证expire调用
            assert mock_redis.expire.call_count == len(data)
    
    async def test_increment(self):
        """测试递增操作"""
        key = "counter"
        amount = 5
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.incrby.return_value = 10  # 新值
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.increment(key, amount)
            
            assert result == 10
            mock_redis.incrby.assert_called_once_with(key, amount)
    
    async def test_decrement(self):
        """测试递减操作"""
        key = "counter"
        amount = 3
        
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.decrby.return_value = 7  # 新值
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            result = await self.cache_manager.decrement(key, amount)
            
            assert result == 7
            mock_redis.decrby.assert_called_once_with(key, amount)
    
    async def test_health_check_healthy(self):
        """测试健康检查 - 健康状态"""
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            is_healthy = await self.cache_manager.health_check()
            
            assert is_healthy is True
            mock_redis.ping.assert_called_once()
    
    async def test_health_check_unhealthy(self):
        """测试健康检查 - 不健康状态"""
        with patch('uplifted.cache.managers.aioredis.from_url') as mock_from_url:
            mock_redis = AsyncMock()
            mock_redis.ping.side_effect = Exception("Connection error")
            mock_from_url.return_value = mock_redis
            await self.cache_manager.initialize()
            
            is_healthy = await self.cache_manager.health_check()
            
            assert is_healthy is False


@pytest.mark.asyncio
class TestMemoryCacheManager:
    """内存缓存管理器测试"""
    
    def setup_method(self):
        self.config = {
            'max_size': 1000,
            'default_ttl': 3600
        }
        self.cache_manager = MemoryCacheManager(self.config)
    
    async def test_initialize(self):
        """测试初始化内存缓存"""
        await self.cache_manager.initialize()
        
        assert self.cache_manager._cache == {}
        assert self.cache_manager._expiry == {}
    
    async def test_set_and_get(self):
        """测试设置和获取"""
        await self.cache_manager.initialize()
        
        key = "test_key"
        value = {"data": "test_value"}
        
        # 设置值
        result = await self.cache_manager.set(key, value)
        assert result is True
        
        # 获取值
        retrieved_value = await self.cache_manager.get(key)
        assert retrieved_value == value
    
    async def test_set_with_ttl(self):
        """测试设置带TTL的值"""
        await self.cache_manager.initialize()
        
        key = "test_key"
        value = {"data": "test_value"}
        ttl = 1  # 1秒
        
        # 设置值
        await self.cache_manager.set(key, value, ttl=ttl)
        
        # 立即获取应该成功
        retrieved_value = await self.cache_manager.get(key)
        assert retrieved_value == value
        
        # 模拟时间过去
        import time
        with patch('time.time', return_value=time.time() + 2):  # 2秒后
            retrieved_value = await self.cache_manager.get(key)
            assert retrieved_value is None
    
    async def test_delete(self):
        """测试删除"""
        await self.cache_manager.initialize()
        
        key = "test_key"
        value = {"data": "test_value"}
        
        # 设置值
        await self.cache_manager.set(key, value)
        
        # 确认存在
        assert await self.cache_manager.exists(key) is True
        
        # 删除
        result = await self.cache_manager.delete(key)
        assert result is True
        
        # 确认不存在
        assert await self.cache_manager.exists(key) is False
    
    async def test_exists(self):
        """测试检查键是否存在"""
        await self.cache_manager.initialize()
        
        key = "test_key"
        value = {"data": "test_value"}
        
        # 键不存在
        assert await self.cache_manager.exists(key) is False
        
        # 设置键
        await self.cache_manager.set(key, value)
        
        # 键存在
        assert await self.cache_manager.exists(key) is True
    
    async def test_clear(self):
        """测试清空缓存"""
        await self.cache_manager.initialize()
        
        # 设置一些值
        await self.cache_manager.set("key1", "value1")
        await self.cache_manager.set("key2", "value2")
        
        # 确认存在
        assert await self.cache_manager.exists("key1") is True
        assert await self.cache_manager.exists("key2") is True
        
        # 清空
        result = await self.cache_manager.clear()
        assert result is True
        
        # 确认都不存在
        assert await self.cache_manager.exists("key1") is False
        assert await self.cache_manager.exists("key2") is False
    
    async def test_max_size_limit(self):
        """测试最大大小限制"""
        config = {'max_size': 2, 'default_ttl': 3600}
        cache_manager = MemoryCacheManager(config)
        await cache_manager.initialize()
        
        # 设置3个值，应该只保留最新的2个
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")
        await cache_manager.set("key3", "value3")
        
        # key1应该被淘汰
        assert await cache_manager.exists("key1") is False
        assert await cache_manager.exists("key2") is True
        assert await cache_manager.exists("key3") is True


@pytest.mark.asyncio
class TestCacheDecorators:
    """缓存装饰器测试"""
    
    def setup_method(self):
        self.mock_cache = AsyncMock()
    
    async def test_cache_result_decorator_cache_hit(self):
        """测试缓存装饰器 - 缓存命中"""
        cached_value = {"result": "cached_data"}
        self.mock_cache.get.return_value = cached_value
        
        @cache_result(cache=self.mock_cache, ttl=3600)
        async def test_function(arg1, arg2):
            return {"result": "fresh_data"}
        
        result = await test_function("value1", "value2")
        
        assert result == cached_value
        # 验证缓存被查询
        self.mock_cache.get.assert_called_once()
        # 验证函数没有被实际执行（没有设置新值）
        self.mock_cache.set.assert_not_called()
    
    async def test_cache_result_decorator_cache_miss(self):
        """测试缓存装饰器 - 缓存未命中"""
        self.mock_cache.get.return_value = None
        fresh_value = {"result": "fresh_data"}
        
        @cache_result(cache=self.mock_cache, ttl=3600)
        async def test_function(arg1, arg2):
            return fresh_value
        
        result = await test_function("value1", "value2")
        
        assert result == fresh_value
        # 验证缓存被查询
        self.mock_cache.get.assert_called_once()
        # 验证新值被设置到缓存
        self.mock_cache.set.assert_called_once()
    
    async def test_cache_result_decorator_with_key_prefix(self):
        """测试缓存装饰器 - 自定义键前缀"""
        self.mock_cache.get.return_value = None
        
        @cache_result(cache=self.mock_cache, key_prefix="custom", ttl=3600)
        async def test_function(arg1):
            return {"result": "data"}
        
        await test_function("test_arg")
        
        # 验证使用了自定义前缀
        expected_key = "custom:test_function:test_arg"
        self.mock_cache.get.assert_called_with(expected_key)
    
    async def test_invalidate_cache_decorator(self):
        """测试缓存失效装饰器"""
        @invalidate_cache(cache=self.mock_cache, pattern="user:*")
        async def update_user(user_id):
            return {"updated": True}
        
        result = await update_user("user123")
        
        assert result == {"updated": True}
        # 验证缓存被删除
        self.mock_cache.delete.assert_called_once_with("user:*")


class TestCacheExceptions:
    """缓存异常测试"""
    
    def test_cache_error(self):
        """测试缓存错误"""
        error = CacheError("Cache operation failed")
        assert str(error) == "Cache operation failed"
        assert isinstance(error, Exception)
    
    def test_connection_error(self):
        """测试连接错误"""
        error = ConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, CacheError)
    
    def test_serialization_error(self):
        """测试序列化错误"""
        error = SerializationError("Serialization failed")
        assert str(error) == "Serialization failed"
        assert isinstance(error, CacheError)


@pytest.mark.asyncio
class TestCacheIntegration:
    """缓存集成测试"""
    
    async def test_cache_manager_factory(self):
        """测试缓存管理器工厂"""
        from uplifted.cache.managers import create_cache_manager
        
        # 测试Redis缓存管理器创建
        redis_config = {
            'type': 'redis',
            'host': 'localhost',
            'port': 6379
        }
        
        redis_manager = create_cache_manager(redis_config)
        assert isinstance(redis_manager, RedisCacheManager)
        
        # 测试内存缓存管理器创建
        memory_config = {
            'type': 'memory',
            'max_size': 1000
        }
        
        memory_manager = create_cache_manager(memory_config)
        assert isinstance(memory_manager, MemoryCacheManager)
    
    async def test_cache_key_generation(self):
        """测试缓存键生成"""
        from uplifted.cache.utils import generate_cache_key
        
        # 测试简单参数
        key1 = generate_cache_key("function_name", "arg1", "arg2")
        assert key1 == "function_name:arg1:arg2"
        
        # 测试复杂参数
        key2 = generate_cache_key("function_name", {"key": "value"}, [1, 2, 3])
        assert "function_name" in key2
        
        # 测试键前缀
        key3 = generate_cache_key("function_name", "arg1", prefix="custom")
        assert key3 == "custom:function_name:arg1"
    
    async def test_cache_serialization(self):
        """测试缓存序列化"""
        from uplifted.cache.serializers import JSONSerializer
        
        serializer = JSONSerializer()
        
        # 测试序列化
        data = {"key": "value", "number": 123, "list": [1, 2, 3]}
        serialized = serializer.serialize(data)
        assert isinstance(serialized, str)
        
        # 测试反序列化
        deserialized = serializer.deserialize(serialized)
        assert deserialized == data
        
        # 测试无效数据
        with pytest.raises(SerializationError):
            serializer.deserialize("invalid json")
    
    async def test_cache_metrics(self):
        """测试缓存指标"""
        cache_manager = MemoryCacheManager({'max_size': 100})
        await cache_manager.initialize()
        
        # 设置一些值
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")
        
        # 获取指标
        metrics = await cache_manager.get_metrics()
        
        assert metrics['total_keys'] == 2
        assert metrics['memory_usage'] > 0
        assert 'hit_rate' in metrics
        assert 'miss_rate' in metrics