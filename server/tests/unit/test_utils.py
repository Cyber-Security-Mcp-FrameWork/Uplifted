"""
工具模块单元测试
"""

import pytest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open

from uplifted.utils.validators import (
    EmailValidator, PasswordValidator, URLValidator, PhoneValidator,
    ValidationError, validate_email, validate_password, validate_url
)
from uplifted.utils.helpers import (
    generate_uuid, generate_random_string, hash_password, verify_password,
    format_datetime, parse_datetime, sanitize_filename, truncate_text,
    deep_merge_dict, flatten_dict, chunk_list, retry_on_failure
)
from uplifted.utils.security import (
    SecurityUtils, encrypt_data, decrypt_data, generate_token,
    verify_token, hash_sensitive_data, mask_sensitive_data
)
from uplifted.utils.file_utils import (
    FileUtils, ensure_directory, read_file, write_file, delete_file,
    get_file_size, get_file_extension, is_safe_path
)


class TestEmailValidator:
    """邮箱验证器测试"""
    
    def setup_method(self):
        self.validator = EmailValidator()
    
    def test_valid_emails(self):
        """测试有效邮箱"""
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk",
            "user+tag@example.org",
            "123@example.com",
            "user_name@example-domain.com"
        ]
        
        for email in valid_emails:
            assert self.validator.validate(email) is True
    
    def test_invalid_emails(self):
        """测试无效邮箱"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user..double.dot@example.com",
            "user@.example.com",
            "user@example.",
            "",
            None
        ]
        
        for email in invalid_emails:
            with pytest.raises(ValidationError):
                self.validator.validate(email)
    
    def test_email_length_validation(self):
        """测试邮箱长度验证"""
        # 测试过长的邮箱
        long_email = "a" * 250 + "@example.com"
        with pytest.raises(ValidationError):
            self.validator.validate(long_email)
    
    def test_domain_validation(self):
        """测试域名验证"""
        # 测试无效域名
        invalid_domains = [
            "user@-example.com",
            "user@example-.com",
            "user@ex..ample.com"
        ]
        
        for email in invalid_domains:
            with pytest.raises(ValidationError):
                self.validator.validate(email)


class TestPasswordValidator:
    """密码验证器测试"""
    
    def setup_method(self):
        self.validator = PasswordValidator(
            min_length=8,
            require_uppercase=True,
            require_lowercase=True,
            require_digits=True,
            require_special=True
        )
    
    def test_valid_passwords(self):
        """测试有效密码"""
        valid_passwords = [
            "Password123!",
            "MySecure@Pass1",
            "Complex#Password9",
            "Strong$Pass123"
        ]
        
        for password in valid_passwords:
            assert self.validator.validate(password) is True
    
    def test_password_too_short(self):
        """测试密码过短"""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate("Pass1!")
        
        assert "at least 8 characters" in str(exc_info.value)
    
    def test_password_missing_uppercase(self):
        """测试密码缺少大写字母"""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate("password123!")
        
        assert "uppercase letter" in str(exc_info.value)
    
    def test_password_missing_lowercase(self):
        """测试密码缺少小写字母"""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate("PASSWORD123!")
        
        assert "lowercase letter" in str(exc_info.value)
    
    def test_password_missing_digits(self):
        """测试密码缺少数字"""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate("Password!")
        
        assert "digit" in str(exc_info.value)
    
    def test_password_missing_special(self):
        """测试密码缺少特殊字符"""
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate("Password123")
        
        assert "special character" in str(exc_info.value)
    
    def test_common_passwords(self):
        """测试常见密码"""
        common_passwords = [
            "password",
            "123456",
            "qwerty",
            "admin"
        ]
        
        for password in common_passwords:
            with pytest.raises(ValidationError) as exc_info:
                self.validator.validate(password)
            
            assert "too common" in str(exc_info.value)
    
    def test_password_strength_score(self):
        """测试密码强度评分"""
        weak_password = "password"
        medium_password = "Password123"
        strong_password = "MyVery$trong@Password123!"
        
        assert self.validator.get_strength_score(weak_password) < 3
        assert 3 <= self.validator.get_strength_score(medium_password) < 4
        assert self.validator.get_strength_score(strong_password) >= 4


class TestURLValidator:
    """URL验证器测试"""
    
    def setup_method(self):
        self.validator = URLValidator()
    
    def test_valid_urls(self):
        """测试有效URL"""
        valid_urls = [
            "https://www.example.com",
            "http://example.com",
            "https://subdomain.example.com/path",
            "https://example.com:8080/path?query=value",
            "ftp://files.example.com/file.txt"
        ]
        
        for url in valid_urls:
            assert self.validator.validate(url) is True
    
    def test_invalid_urls(self):
        """测试无效URL"""
        invalid_urls = [
            "not-a-url",
            "http://",
            "://example.com",
            "http://.com",
            "",
            None
        ]
        
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                self.validator.validate(url)
    
    def test_scheme_validation(self):
        """测试协议验证"""
        # 只允许特定协议
        validator = URLValidator(allowed_schemes=['https'])
        
        assert validator.validate("https://example.com") is True
        
        with pytest.raises(ValidationError):
            validator.validate("http://example.com")


class TestPhoneValidator:
    """电话号码验证器测试"""
    
    def setup_method(self):
        self.validator = PhoneValidator()
    
    def test_valid_phone_numbers(self):
        """测试有效电话号码"""
        valid_phones = [
            "+1234567890",
            "+86 138 0013 8000",
            "+44 20 7946 0958",
            "13800138000",
            "(555) 123-4567"
        ]
        
        for phone in valid_phones:
            assert self.validator.validate(phone) is True
    
    def test_invalid_phone_numbers(self):
        """测试无效电话号码"""
        invalid_phones = [
            "123",
            "abc123def",
            "+",
            "",
            None,
            "123-456-789-0123-4567"  # 太长
        ]
        
        for phone in invalid_phones:
            with pytest.raises(ValidationError):
                self.validator.validate(phone)


class TestHelpers:
    """辅助函数测试"""
    
    def test_generate_uuid(self):
        """测试UUID生成"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        
        assert uuid1 != uuid2
        assert len(uuid1) == 36  # UUID4格式长度
        assert "-" in uuid1
    
    def test_generate_random_string(self):
        """测试随机字符串生成"""
        # 测试默认长度
        random_str = generate_random_string()
        assert len(random_str) == 32
        
        # 测试指定长度
        random_str = generate_random_string(length=16)
        assert len(random_str) == 16
        
        # 测试只包含字母
        random_str = generate_random_string(length=10, include_digits=False)
        assert len(random_str) == 10
        assert random_str.isalpha()
        
        # 测试只包含数字
        random_str = generate_random_string(length=10, include_letters=False)
        assert len(random_str) == 10
        assert random_str.isdigit()
    
    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt哈希长度
        assert hashed.startswith("$2b$")
    
    def test_verify_password(self):
        """测试密码验证"""
        password = "test_password"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_format_datetime(self):
        """测试日期时间格式化"""
        dt = datetime(2023, 1, 1, 12, 30, 45)
        
        # 默认格式
        formatted = format_datetime(dt)
        assert "2023-01-01" in formatted
        assert "12:30:45" in formatted
        
        # 自定义格式
        formatted = format_datetime(dt, format_str="%Y/%m/%d")
        assert formatted == "2023/01/01"
    
    def test_parse_datetime(self):
        """测试日期时间解析"""
        # ISO格式
        dt_str = "2023-01-01T12:30:45"
        dt = parse_datetime(dt_str)
        
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1
        assert dt.hour == 12
        assert dt.minute == 30
        assert dt.second == 45
        
        # 自定义格式
        dt_str = "2023/01/01"
        dt = parse_datetime(dt_str, format_str="%Y/%m/%d")
        assert dt.year == 2023
        assert dt.month == 1
        assert dt.day == 1
    
    def test_sanitize_filename(self):
        """测试文件名清理"""
        # 测试危险字符
        filename = "file<>:\"|?*.txt"
        sanitized = sanitize_filename(filename)
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized
        assert "|" not in sanitized
        assert "?" not in sanitized
        assert "*" not in sanitized
        
        # 测试路径分隔符
        filename = "path/to/file.txt"
        sanitized = sanitize_filename(filename)
        assert "/" not in sanitized
        assert "\\" not in sanitized
    
    def test_truncate_text(self):
        """测试文本截断"""
        text = "This is a very long text that needs to be truncated"
        
        # 测试截断
        truncated = truncate_text(text, max_length=20)
        assert len(truncated) <= 23  # 20 + "..."
        assert truncated.endswith("...")
        
        # 测试不需要截断
        short_text = "Short text"
        truncated = truncate_text(short_text, max_length=20)
        assert truncated == short_text
    
    def test_deep_merge_dict(self):
        """测试字典深度合并"""
        dict1 = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3
            }
        }
        
        dict2 = {
            "b": {
                "d": 4,
                "e": 5
            },
            "f": 6
        }
        
        merged = deep_merge_dict(dict1, dict2)
        
        assert merged["a"] == 1
        assert merged["b"]["c"] == 2
        assert merged["b"]["d"] == 4  # 被覆盖
        assert merged["b"]["e"] == 5
        assert merged["f"] == 6
    
    def test_flatten_dict(self):
        """测试字典扁平化"""
        nested_dict = {
            "a": 1,
            "b": {
                "c": 2,
                "d": {
                    "e": 3
                }
            }
        }
        
        flattened = flatten_dict(nested_dict)
        
        assert flattened["a"] == 1
        assert flattened["b.c"] == 2
        assert flattened["b.d.e"] == 3
    
    def test_chunk_list(self):
        """测试列表分块"""
        data = list(range(10))  # [0, 1, 2, ..., 9]
        
        chunks = list(chunk_list(data, chunk_size=3))
        
        assert len(chunks) == 4  # 10/3 = 3余1，所以4块
        assert chunks[0] == [0, 1, 2]
        assert chunks[1] == [3, 4, 5]
        assert chunks[2] == [6, 7, 8]
        assert chunks[3] == [9]
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """测试失败重试装饰器"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.01)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = await failing_function()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_on_failure_max_retries(self):
        """测试重试达到最大次数"""
        @retry_on_failure(max_retries=2, delay=0.01)
        async def always_failing_function():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            await always_failing_function()


class TestSecurityUtils:
    """安全工具测试"""
    
    def setup_method(self):
        self.security = SecurityUtils()
    
    def test_encrypt_decrypt_data(self):
        """测试数据加密解密"""
        data = "sensitive information"
        key = "test_encryption_key_32_characters"
        
        encrypted = encrypt_data(data, key)
        assert encrypted != data
        assert len(encrypted) > len(data)
        
        decrypted = decrypt_data(encrypted, key)
        assert decrypted == data
    
    def test_generate_token(self):
        """测试令牌生成"""
        payload = {"user_id": "123", "role": "admin"}
        secret = "test_secret_key"
        
        token = generate_token(payload, secret)
        assert isinstance(token, str)
        assert len(token) > 50
    
    def test_verify_token(self):
        """测试令牌验证"""
        payload = {"user_id": "123", "role": "admin"}
        secret = "test_secret_key"
        
        token = generate_token(payload, secret)
        verified_payload = verify_token(token, secret)
        
        assert verified_payload["user_id"] == "123"
        assert verified_payload["role"] == "admin"
    
    def test_verify_invalid_token(self):
        """测试无效令牌验证"""
        invalid_token = "invalid.token.here"
        secret = "test_secret_key"
        
        with pytest.raises(Exception):  # JWT验证异常
            verify_token(invalid_token, secret)
    
    def test_hash_sensitive_data(self):
        """测试敏感数据哈希"""
        data = "sensitive_data"
        hashed = hash_sensitive_data(data)
        
        assert hashed != data
        assert len(hashed) == 64  # SHA256哈希长度
    
    def test_mask_sensitive_data(self):
        """测试敏感数据掩码"""
        # 测试邮箱掩码
        email = "user@example.com"
        masked = mask_sensitive_data(email, data_type="email")
        assert masked.startswith("u***")
        assert masked.endswith("@example.com")
        
        # 测试电话号码掩码
        phone = "13800138000"
        masked = mask_sensitive_data(phone, data_type="phone")
        assert masked.startswith("138")
        assert masked.endswith("8000")
        assert "***" in masked
        
        # 测试信用卡号掩码
        card = "1234567890123456"
        masked = mask_sensitive_data(card, data_type="card")
        assert masked.startswith("****")
        assert masked.endswith("3456")
    
    def test_generate_secure_random(self):
        """测试安全随机数生成"""
        random1 = self.security.generate_secure_random(32)
        random2 = self.security.generate_secure_random(32)
        
        assert len(random1) == 32
        assert len(random2) == 32
        assert random1 != random2
    
    def test_constant_time_compare(self):
        """测试常量时间比较"""
        string1 = "secret_value"
        string2 = "secret_value"
        string3 = "different_value"
        
        assert self.security.constant_time_compare(string1, string2) is True
        assert self.security.constant_time_compare(string1, string3) is False


class TestFileUtils:
    """文件工具测试"""
    
    def setup_method(self):
        self.file_utils = FileUtils()
    
    def test_ensure_directory(self):
        """测试确保目录存在"""
        with patch('os.makedirs') as mock_makedirs:
            with patch('os.path.exists', return_value=False):
                ensure_directory("/test/path")
                mock_makedirs.assert_called_once_with("/test/path", exist_ok=True)
    
    def test_read_file(self):
        """测试读取文件"""
        content = "test file content"
        
        with patch('builtins.open', mock_open(read_data=content)):
            result = read_file("/test/file.txt")
            assert result == content
    
    def test_write_file(self):
        """测试写入文件"""
        content = "test content"
        
        with patch('builtins.open', mock_open()) as mock_file:
            write_file("/test/file.txt", content)
            mock_file.assert_called_once_with("/test/file.txt", "w", encoding="utf-8")
            mock_file().write.assert_called_once_with(content)
    
    def test_delete_file(self):
        """测试删除文件"""
        with patch('os.remove') as mock_remove:
            with patch('os.path.exists', return_value=True):
                delete_file("/test/file.txt")
                mock_remove.assert_called_once_with("/test/file.txt")
    
    def test_get_file_size(self):
        """测试获取文件大小"""
        with patch('os.path.getsize', return_value=1024):
            size = get_file_size("/test/file.txt")
            assert size == 1024
    
    def test_get_file_extension(self):
        """测试获取文件扩展名"""
        assert get_file_extension("file.txt") == ".txt"
        assert get_file_extension("document.pdf") == ".pdf"
        assert get_file_extension("archive.tar.gz") == ".gz"
        assert get_file_extension("no_extension") == ""
    
    def test_is_safe_path(self):
        """测试路径安全检查"""
        # 安全路径
        assert is_safe_path("/safe/path/file.txt", "/safe") is True
        assert is_safe_path("/safe/subdir/file.txt", "/safe") is True
        
        # 不安全路径（路径遍历）
        assert is_safe_path("/safe/../etc/passwd", "/safe") is False
        assert is_safe_path("../../../etc/passwd", "/safe") is False
    
    def test_file_operations_with_errors(self):
        """测试文件操作错误处理"""
        # 测试读取不存在的文件
        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                read_file("/nonexistent/file.txt")
        
        # 测试写入权限不足
        with patch('builtins.open', side_effect=PermissionError):
            with pytest.raises(PermissionError):
                write_file("/readonly/file.txt", "content")


class TestValidationFunctions:
    """验证函数测试"""
    
    def test_validate_email_function(self):
        """测试邮箱验证函数"""
        assert validate_email("user@example.com") is True
        
        with pytest.raises(ValidationError):
            validate_email("invalid-email")
    
    def test_validate_password_function(self):
        """测试密码验证函数"""
        assert validate_password("StrongPass123!") is True
        
        with pytest.raises(ValidationError):
            validate_password("weak")
    
    def test_validate_url_function(self):
        """测试URL验证函数"""
        assert validate_url("https://example.com") is True
        
        with pytest.raises(ValidationError):
            validate_url("not-a-url")


class TestUtilsIntegration:
    """工具模块集成测试"""
    
    def test_password_workflow(self):
        """测试密码完整工作流"""
        # 验证密码强度
        password = "MySecure@Pass123"
        assert validate_password(password) is True
        
        # 哈希密码
        hashed = hash_password(password)
        assert hashed != password
        
        # 验证密码
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False
    
    def test_data_security_workflow(self):
        """测试数据安全工作流"""
        sensitive_data = "user_credit_card_number"
        encryption_key = "secure_encryption_key_32_chars!!"
        
        # 加密敏感数据
        encrypted = encrypt_data(sensitive_data, encryption_key)
        assert encrypted != sensitive_data
        
        # 解密数据
        decrypted = decrypt_data(encrypted, encryption_key)
        assert decrypted == sensitive_data
        
        # 掩码显示
        masked = mask_sensitive_data("1234567890123456", "card")
        assert "****" in masked
        assert masked.endswith("3456")
    
    def test_file_processing_workflow(self):
        """测试文件处理工作流"""
        filename = "user<input>file.txt"
        content = "File content with sensitive data"
        
        # 清理文件名
        safe_filename = sanitize_filename(filename)
        assert "<" not in safe_filename
        assert ">" not in safe_filename
        
        # 模拟文件操作
        with patch('builtins.open', mock_open()) as mock_file:
            write_file(f"/safe/path/{safe_filename}", content)
            mock_file.assert_called_once()
    
    def test_validation_chain(self):
        """测试验证链"""
        user_data = {
            "email": "user@example.com",
            "password": "SecurePass123!",
            "website": "https://example.com",
            "phone": "+1234567890"
        }
        
        # 验证所有字段
        assert validate_email(user_data["email"]) is True
        assert validate_password(user_data["password"]) is True
        assert validate_url(user_data["website"]) is True
        
        phone_validator = PhoneValidator()
        assert phone_validator.validate(user_data["phone"]) is True