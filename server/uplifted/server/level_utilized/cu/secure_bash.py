"""
安全的Bash工具包装器

在原有BashTool基础上添加安全验证层，防止命令注入攻击。
"""

import logging
from typing import ClassVar, Literal, Optional
from anthropic.types.beta import BetaToolBash20241022Param

from .base import BaseAnthropicTool, ToolError, ToolResult
from .bash import BashTool
from ....security.command_validator import (
    CommandValidator,
    SecureBashExecutor,
    SecurityError,
    CommandRiskLevel
)


class SecureBashTool(BaseAnthropicTool):
    """
    安全的Bash命令执行工具

    在原有BashTool基础上添加：
    1. 命令白名单验证
    2. 危险模式检测
    3. 参数安全验证
    4. 审计日志记录
    5. 可配置的安全策略

    使用方式:
        secure_bash = SecureBashTool(allow_dangerous=False)
        result = await secure_bash(command="ls -la")
    """

    name: ClassVar[Literal["bash"]] = "bash"
    api_type: ClassVar[Literal["bash_20241022"]] = "bash_20241022"

    def __init__(self,
                 allow_dangerous: bool = False,
                 enable_audit_log: bool = True,
                 custom_whitelist: Optional[set] = None,
                 logger: Optional[logging.Logger] = None):
        """
        初始化安全Bash工具

        Args:
            allow_dangerous: 是否允许危险命令（默认False，生产环境禁用）
            enable_audit_log: 是否启用审计日志（默认True）
            custom_whitelist: 自定义命令白名单
            logger: 日志记录器
        """
        super().__init__()

        self.logger = logger or logging.getLogger(__name__)

        # 创建底层Bash工具
        self._bash_tool = BashTool()

        # 创建命令验证器
        self._validator = CommandValidator(
            allow_dangerous=allow_dangerous,
            custom_whitelist=custom_whitelist,
            logger=self.logger
        )

        # 创建安全执行器
        self._executor = SecureBashExecutor(
            bash_tool=self._bash_tool,
            validator=self._validator,
            enable_audit_log=enable_audit_log,
            logger=self.logger
        )

        self.logger.info(
            f"SecureBashTool initialized (allow_dangerous={allow_dangerous})"
        )

    async def __call__(
        self,
        command: str | None = None,
        restart: bool = False,
        **kwargs
    ):
        """
        执行Bash命令（带安全验证）

        Args:
            command: 要执行的命令
            restart: 是否重启Bash会话
            **kwargs: 其他参数

        Returns:
            ToolResult: 命令执行结果

        Raises:
            ToolError: 命令验证失败或执行错误
        """
        # 重启会话不需要验证
        if restart:
            return await self._bash_tool(restart=True, **kwargs)

        if command is None:
            raise ToolError("未提供任何命令")

        # 安全执行命令
        try:
            result = await self._executor.execute(command, **kwargs)
            return result

        except SecurityError as e:
            # 返回安全错误信息
            self.logger.error(f"Security violation: {e}")
            return ToolResult(
                error=f"安全错误: {str(e)}",
                system="命令被安全策略拒绝"
            )

        except Exception as e:
            self.logger.exception(f"Command execution failed: {e}")
            raise ToolError(f"命令执行失败: {str(e)}")

    def to_params(self) -> BetaToolBash20241022Param:
        """返回工具参数（与原BashTool兼容）"""
        return {
            "type": self.api_type,
            "name": self.name,
        }

    def get_audit_log(self, limit: int = 100):
        """
        获取审计日志

        Args:
            limit: 返回的日志条数

        Returns:
            List[Dict]: 审计日志列表
        """
        return self._executor.get_audit_log(limit=limit)

    def add_to_whitelist(self, commands: set):
        """
        动态添加命令到白名单

        Args:
            commands: 要添加的命令集合
        """
        self._validator.whitelist.update(commands)
        self.logger.info(f"Added commands to whitelist: {commands}")

    def remove_from_whitelist(self, commands: set):
        """
        从白名单移除命令

        Args:
            commands: 要移除的命令集合
        """
        self._validator.whitelist -= commands
        self.logger.info(f"Removed commands from whitelist: {commands}")


# 便捷函数：创建默认安全配置的Bash工具
def create_secure_bash_tool(
    profile: Literal["strict", "moderate", "permissive"] = "strict",
    logger: Optional[logging.Logger] = None
) -> SecureBashTool:
    """
    创建预配置的安全Bash工具

    Args:
        profile: 安全配置档案
            - strict: 严格模式，只允许只读命令（生产环境推荐）
            - moderate: 中等模式，允许部分写命令
            - permissive: 宽松模式，允许更多命令（开发环境）
        logger: 日志记录器

    Returns:
        SecureBashTool: 配置好的安全工具实例
    """
    if profile == "strict":
        # 严格模式：只读操作
        return SecureBashTool(
            allow_dangerous=False,
            enable_audit_log=True,
            logger=logger
        )

    elif profile == "moderate":
        # 中等模式：允许基本文件操作
        tool = SecureBashTool(
            allow_dangerous=True,  # 允许危险命令
            enable_audit_log=True,
            logger=logger
        )
        # 但只添加基本的文件操作命令
        tool.add_to_whitelist({'mkdir', 'touch', 'cp'})
        return tool

    elif profile == "permissive":
        # 宽松模式：允许更多命令（仅用于开发）
        tool = SecureBashTool(
            allow_dangerous=True,
            enable_audit_log=True,
            custom_whitelist={'mkdir', 'touch', 'cp', 'mv', 'ln'},
            logger=logger
        )
        return tool

    else:
        raise ValueError(f"Unknown profile: {profile}")
