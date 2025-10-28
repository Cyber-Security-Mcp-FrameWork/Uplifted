"""
插件和工具管理 API

提供 REST API 端点用于查询和管理插件、工具信息。

端点:
    GET /api/v1/plugins - 列出所有插件
    GET /api/v1/plugins/{plugin_id} - 获取插件详情
    GET /api/v1/plugins/{plugin_id}/tools - 获取插件的工具列表

    GET /api/v1/tools - 列出所有工具
    GET /api/v1/tools/{tool_name} - 获取工具详情
    GET /api/v1/tools/{tool_name}/source - 查询工具来源插件

    GET /api/v1/system/status - 获取插件系统状态

作者: Uplifted Team
日期: 2025-10-28
版本: 1.0.0
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from ..extensions import (
    get_global_plugin_manager,
    get_global_mcp_bridge,
    get_plugin_system_status
)
from ..extensions.plugin_manager import PluginStatus


# 创建路由器
router = APIRouter(prefix="/api/v1", tags=["plugins"])


# ============================================================================
# 数据模型
# ============================================================================

class PluginInfo(BaseModel):
    """插件信息响应模型"""
    name: str = Field(..., description="插件名称")
    version: str = Field(..., description="版本号")
    description: str = Field("", description="插件描述")
    author: str = Field("", description="作者")
    status: str = Field(..., description="插件状态")
    dependencies: List[str] = Field(default_factory=list, description="依赖的其他插件")


class PluginDetail(PluginInfo):
    """插件详细信息响应模型"""
    config_schema: Optional[Dict[str, Any]] = Field(None, description="配置架构")
    min_api_version: str = Field("1.0.0", description="最小 API 版本")
    max_api_version: str = Field("2.0.0", description="最大 API 版本")
    tools_count: int = Field(0, description="提供的工具数量")


class ToolInfo(BaseModel):
    """工具信息响应模型"""
    name: str = Field(..., description="工具全名")
    plugin_id: str = Field(..., description="所属插件 ID")
    description: str = Field("", description="工具描述")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="输入参数架构")
    registered_at: str = Field(..., description="注册时间")
    active: bool = Field(True, description="是否激活")


class ToolDetail(ToolInfo):
    """工具详细信息响应模型"""
    entry_point: str = Field("", description="入口点")
    mcp_command: Optional[str] = Field(None, description="MCP 命令")
    mcp_args: List[str] = Field(default_factory=list, description="MCP 参数")
    requires_approval: bool = Field(False, description="是否需要审批")


class SystemStatus(BaseModel):
    """系统状态响应模型"""
    plugin_count: int = Field(..., description="插件总数")
    active_plugin_count: int = Field(..., description="活跃插件数")
    total_tools: int = Field(..., description="工具总数")
    active_tools: int = Field(..., description="活跃工具数")
    mcp_available: bool = Field(..., description="MCP 桥接器是否可用")


# ============================================================================
# 插件管理端点
# ============================================================================

@router.get("/plugins", response_model=List[PluginInfo])
async def list_plugins(
    status: Optional[str] = Query(None, description="按状态过滤（active, loaded, inactive 等）")
) -> List[PluginInfo]:
    """
    列出所有插件

    查询参数:
        status: 可选，按状态过滤插件

    返回:
        插件信息列表

    示例:
        GET /api/v1/plugins
        GET /api/v1/plugins?status=active
    """
    plugin_manager = get_global_plugin_manager()
    all_plugins = plugin_manager.registry.get_all_plugins()

    result = []
    for name, plugin in all_plugins.items():
        # 按状态过滤
        if status and plugin.status.value != status:
            continue

        result.append(PluginInfo(
            name=plugin.info.name,
            version=plugin.info.version,
            description=plugin.info.description,
            author=plugin.info.author,
            status=plugin.status.value,
            dependencies=plugin.info.dependencies
        ))

    return result


@router.get("/plugins/{plugin_id}", response_model=PluginDetail)
async def get_plugin_detail(plugin_id: str) -> PluginDetail:
    """
    获取插件详细信息

    路径参数:
        plugin_id: 插件 ID 或名称

    返回:
        插件详细信息

    示例:
        GET /api/v1/plugins/com.uplifted.examples.hello_world
    """
    plugin_manager = get_global_plugin_manager()
    plugin = plugin_manager.registry.get_plugin(plugin_id)

    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found")

    # 获取工具数量
    tools_count = 0
    bridge = get_global_mcp_bridge()
    if bridge:
        tools = bridge.get_plugin_tools(plugin_id)
        tools_count = len(tools)

    return PluginDetail(
        name=plugin.info.name,
        version=plugin.info.version,
        description=plugin.info.description,
        author=plugin.info.author,
        status=plugin.status.value,
        dependencies=plugin.info.dependencies,
        config_schema=plugin.info.config_schema,
        min_api_version=plugin.info.min_api_version,
        max_api_version=plugin.info.max_api_version,
        tools_count=tools_count
    )


@router.get("/plugins/{plugin_id}/tools", response_model=List[str])
async def get_plugin_tools(plugin_id: str) -> List[str]:
    """
    获取插件提供的工具列表

    路径参数:
        plugin_id: 插件 ID

    返回:
        工具名称列表

    示例:
        GET /api/v1/plugins/com.uplifted.examples.hello_world/tools
        => ["com.uplifted.examples.hello_world.greet", "com.uplifted.examples.hello_world.echo"]
    """
    bridge = get_global_mcp_bridge()
    if not bridge:
        raise HTTPException(status_code=503, detail="MCP bridge not available")

    tools = bridge.get_plugin_tools(plugin_id)

    if tools is None:
        raise HTTPException(status_code=404, detail=f"Plugin {plugin_id} not found or has no tools")

    return tools


# ============================================================================
# 工具管理端点
# ============================================================================

@router.get("/tools", response_model=List[ToolInfo])
async def list_tools(
    plugin_id: Optional[str] = Query(None, description="按插件 ID 过滤"),
    active_only: bool = Query(True, description="仅显示激活的工具")
) -> List[ToolInfo]:
    """
    列出所有工具

    查询参数:
        plugin_id: 可选，按插件 ID 过滤
        active_only: 是否仅显示激活的工具（默认 True）

    返回:
        工具信息列表

    示例:
        GET /api/v1/tools
        GET /api/v1/tools?plugin_id=com.uplifted.examples.hello_world
        GET /api/v1/tools?active_only=false
    """
    bridge = get_global_mcp_bridge()
    if not bridge:
        raise HTTPException(status_code=503, detail="MCP bridge not available")

    all_tools = bridge.get_all_registered_tools()

    result = []
    for tool in all_tools:
        # 按插件过滤
        if plugin_id and tool.plugin_id != plugin_id:
            continue

        # 按激活状态过滤
        if active_only and not tool.active:
            continue

        result.append(ToolInfo(
            name=tool.tool_name,
            plugin_id=tool.plugin_id,
            description=tool.tool_def.description,
            input_schema=tool.tool_def.input_schema,
            registered_at=tool.registered_at.isoformat(),
            active=tool.active
        ))

    return result


@router.get("/tools/{tool_name:path}", response_model=ToolDetail)
async def get_tool_detail(tool_name: str) -> ToolDetail:
    """
    获取工具详细信息

    路径参数:
        tool_name: 工具名称（全名或短名）

    返回:
        工具详细信息

    示例:
        GET /api/v1/tools/com.uplifted.examples.hello_world.greet
        GET /api/v1/tools/greet  (如果唯一)
    """
    bridge = get_global_mcp_bridge()
    if not bridge:
        raise HTTPException(status_code=503, detail="MCP bridge not available")

    tool_info = bridge.get_tool_info(tool_name)

    # 如果精确匹配未找到，尝试短名匹配
    if not tool_info:
        plugin_id = bridge.get_tool_source(tool_name)
        if plugin_id:
            # 构建完整工具名
            full_name = f"{plugin_id}.{tool_name}"
            tool_info = bridge.get_tool_info(full_name)

    if not tool_info:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    return ToolDetail(
        name=tool_info.tool_name,
        plugin_id=tool_info.plugin_id,
        description=tool_info.tool_def.description,
        input_schema=tool_info.tool_def.input_schema,
        registered_at=tool_info.registered_at.isoformat(),
        active=tool_info.active,
        entry_point=tool_info.tool_def.entry_point,
        mcp_command=tool_info.tool_def.mcp_command,
        mcp_args=tool_info.tool_def.mcp_args or [],
        requires_approval=tool_info.tool_def.requires_approval
    )


@router.get("/tools/{tool_name:path}/source")
async def get_tool_source(tool_name: str) -> Dict[str, str]:
    """
    查询工具来源插件

    路径参数:
        tool_name: 工具名称（全名或短名）

    返回:
        包含插件 ID 和工具全名的字典

    示例:
        GET /api/v1/tools/greet/source
        => {"plugin_id": "com.uplifted.examples.hello_world", "tool_name": "com.uplifted.examples.hello_world.greet"}
    """
    bridge = get_global_mcp_bridge()
    if not bridge:
        raise HTTPException(status_code=503, detail="MCP bridge not available")

    plugin_id = bridge.get_tool_source(tool_name)

    if not plugin_id:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

    # 获取完整工具名
    tool_info = bridge.get_tool_info(tool_name)
    full_name = tool_info.tool_name if tool_info else f"{plugin_id}.{tool_name}"

    return {
        "plugin_id": plugin_id,
        "tool_name": full_name
    }


# ============================================================================
# 系统状态端点
# ============================================================================

@router.get("/system/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """
    获取插件系统状态

    返回:
        系统状态信息，包括插件数、工具数等

    示例:
        GET /api/v1/system/status
    """
    status = get_plugin_system_status()

    mcp_stats = status.get('mcp_stats', {})

    return SystemStatus(
        plugin_count=status['plugin_count'],
        active_plugin_count=status['active_plugin_count'],
        total_tools=mcp_stats.get('total_tools', 0),
        active_tools=mcp_stats.get('active_tools', 0),
        mcp_available=status['mcp_available']
    )


@router.get("/system/statistics")
async def get_detailed_statistics() -> Dict[str, Any]:
    """
    获取详细的系统统计信息

    返回:
        完整的系统状态字典，包括所有插件和工具的详细信息

    示例:
        GET /api/v1/system/statistics
    """
    return get_plugin_system_status()


# 导出路由器
__all__ = ['router']
