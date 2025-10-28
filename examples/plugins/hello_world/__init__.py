"""
Hello World Plugin - 示例插件

这是一个完整的示例插件，展示如何：
1. 使用 PluginManifest 定义插件
2. 实现 Plugin 基类
3. 提供工具函数
4. 处理配置

作者: Uplifted Team
版本: 1.0.0
"""

from uplifted.extensions.plugin_manager import Plugin
from uplifted.extensions.plugin_manifest import PluginManifest


class HelloWorldPlugin(Plugin):
    """
    Hello World 插件实现

    展示插件的基本生命周期：初始化、激活、停用、清理
    """

    async def initialize(self) -> bool:
        """
        初始化插件

        在插件加载时调用，用于执行初始化操作。

        返回:
            True 表示初始化成功，False 表示失败
        """
        if self.logger:
            self.logger.info(f"Initializing {self.manifest.name}...")

        # 从配置中读取默认语言
        default_lang = self.get_config_value('default_language', 'en')

        if self.logger:
            self.logger.info(f"Default language set to: {default_lang}")

        return True

    async def activate(self) -> bool:
        """
        激活插件

        在插件准备就绪后调用，插件的工具此时可以被使用。

        返回:
            True 表示激活成功，False 表示失败
        """
        if self.logger:
            self.logger.info(f"{self.manifest.name} activated successfully!")
            self.logger.info(f"Available tools: {[t.name for t in self.manifest.tools]}")

        return True

    async def deactivate(self) -> bool:
        """
        停用插件

        在插件需要停止服务时调用。

        返回:
            True 表示停用成功
        """
        if self.logger:
            self.logger.info(f"{self.manifest.name} deactivated")

        return True

    async def cleanup(self) -> bool:
        """
        清理插件资源

        在插件卸载时调用，用于清理资源。

        返回:
            True 表示清理成功
        """
        if self.logger:
            self.logger.info(f"{self.manifest.name} cleaned up")

        return True


# 插件信息（供自动发现使用）
PLUGIN_MANIFEST = PluginManifest.from_json_file(
    __file__.replace('__init__.py', 'manifest.json')
)
