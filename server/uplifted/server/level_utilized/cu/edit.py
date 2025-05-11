from collections import defaultdict
from pathlib import Path
from typing import Literal, get_args

from anthropic.types.beta import BetaToolTextEditor20241022Param

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from .run import maybe_truncate, run

Command = Literal[
    "view",
    "create",
    "str_replace",
    "insert",
    "undo_edit",
]
SNIPPET_LINES: int = 4


class EditTool(BaseAnthropicTool):
    """
    一个文件系统编辑工具，允许代理查看、创建和编辑文件。
    工具参数由 Anthropic 定义且不可编辑。
    """

    api_type: Literal["text_editor_20241022"] = "text_editor_20241022"
    name: Literal["str_replace_editor"] = "str_replace_editor"

    _file_history: dict[Path, list[str]]

    def __init__(self):
        self._file_history = defaultdict(list)
        super().__init__()

    def to_params(self) -> BetaToolTextEditor20241022Param:
        return {
            "name": self.name,
            "type": self.api_type,
        }

    async def __call__(
        self,
        *,
        command: Command,
        path: str,
        file_text: str | None = None,
        view_range: list[int] | None = None,
        old_str: str | None = None,
        new_str: str | None = None,
        insert_line: int | None = None,
        **kwargs,
    ):
        _path = Path(path)
        self.validate_path(command, _path)
        if command == "view":
            return await self.view(_path, view_range)
        elif command == "create":
            if file_text is None:
                raise ToolError("命令 create 需要参数 `file_text`")
            self.write_file(_path, file_text)
            self._file_history[_path].append(file_text)
            return ToolResult(output=f"文件已成功创建于: {_path}")
        elif command == "str_replace":
            if old_str is None:
                raise ToolError("命令 str_replace 需要参数 `old_str`")
            return self.str_replace(_path, old_str, new_str)
        elif command == "insert":
            if insert_line is None:
                raise ToolError("命令 insert 需要参数 `insert_line`")
            if new_str is None:
                raise ToolError("命令 insert 需要参数 `new_str`")
            return self.insert(_path, insert_line, new_str)
        elif command == "undo_edit":
            return self.undo_edit(_path)
        raise ToolError(
            f"无法识别的命令 {command}。对于工具 {self.name}，允许的命令有：{', '.join(get_args(Command))}"
        )

    def validate_path(self, command: str, path: Path):
        """
        检查路径和命令的组合是否有效。
        """
        # 检查路径是否为绝对路径
        if not path.is_absolute():
            suggested_path = Path("") / path
            raise ToolError(
                f"路径 {path} 不是绝对路径，应以 `/` 开头。或许你想输入 {suggested_path}？"
            )
        # 检查路径是否存在
        if not path.exists() and command != "create":
            raise ToolError(
                f"路径 {path} 不存在，请提供一个有效的路径。"
            )
        if path.exists() and command == "create":
            raise ToolError(
                f"文件已存在于 {path}。不能使用命令 create 覆盖文件。"
            )
        # 检查路径是否指向一个目录
        if path.is_dir():
            if command != "view":
                raise ToolError(
                    f"路径 {path} 是一个目录，只有命令 view 可用于目录。"
                )

    async def view(self, path: Path, view_range: list[int] | None = None):
        """实现 view 命令"""
        if path.is_dir():
            if view_range:
                raise ToolError(
                    "当路径指向目录时，不允许使用 `view_range` 参数。"
                )

            _, stdout, stderr = await run(
                rf"find {path} -maxdepth 2 -not -path '*/\.*'"
            )
            if not stderr:
                stdout = f"以下是在 {path} 中（最多两层深度且不包含隐藏项）的文件和目录：\n{stdout}\n"
            return CLIResult(output=stdout, error=stderr)

        file_content = self.read_file(path)
        init_line = 1
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError(
                    "无效的 `view_range`。它应该是由两个整数组成的列表。"
                )
            file_lines = file_content.split("\n")
            n_lines_file = len(file_lines)
            init_line, final_line = view_range
            if init_line < 1 or init_line > n_lines_file:
                raise ToolError(
                    f"无效的 `view_range`: {view_range}。第一个元素 `{init_line}` 应在文件行号范围 [1, {n_lines_file}] 内。"
                )
            if final_line > n_lines_file:
                raise ToolError(
                    f"无效的 `view_range`: {view_range}。第二个元素 `{final_line}` 应小于等于文件的总行数 {n_lines_file}。"
                )
            if final_line != -1 and final_line < init_line:
                raise ToolError(
                    f"无效的 `view_range`: {view_range}。第二个元素 `{final_line}` 应大于或等于第一个元素 `{init_line}`。"
                )

            if final_line == -1:
                file_content = "\n".join(file_lines[init_line - 1 :])
            else:
                file_content = "\n".join(file_lines[init_line - 1 : final_line])

        return CLIResult(
            output=self._make_output(file_content, str(path), init_line=init_line)
        )

    def str_replace(self, path: Path, old_str: str, new_str: str | None):
        """实现 str_replace 命令，在文件内容中将 old_str 替换为 new_str"""
        # 读取文件内容
        file_content = self.read_file(path).expandtabs()
        old_str = old_str.expandtabs()
        new_str = new_str.expandtabs() if new_str is not None else ""

        # 检查 old_str 在文件中是否唯一
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(
                f"未执行任何替换操作，old_str `{old_str}` 在 {path} 中未按原样出现。"
            )
        elif occurrences > 1:
            file_content_lines = file_content.split("\n")
            lines = [
                idx + 1
                for idx, line in enumerate(file_content_lines)
                if old_str in line
            ]
            raise ToolError(
                f"未执行替换操作。old_str `{old_str}` 在以下行 {lines} 中出现了多次，请确保它是唯一的。"
            )

        # 将 old_str 替换为 new_str
        new_file_content = file_content.replace(old_str, new_str)

        # 将新内容写入文件
        self.write_file(path, new_file_content)

        # 将原内容保存到历史记录中
        self._file_history[path].append(file_content)

        # 创建编辑区域的摘录
        replacement_line = file_content.split(old_str)[0].count("\n")
        start_line = max(0, replacement_line - SNIPPET_LINES)
        end_line = replacement_line + SNIPPET_LINES + new_str.count("\n")
        snippet = "\n".join(new_file_content.split("\n")[start_line : end_line + 1])

        # 构造成功信息
        success_msg = f"文件 {path} 已被编辑。"
        success_msg += self._make_output(
            snippet, f"{path} 的摘录", start_line + 1
        )
        success_msg += "请检查更改，确保符合预期，如有必要请再次编辑文件。"

        return CLIResult(output=success_msg)

    def insert(self, path: Path, insert_line: int, new_str: str):
        """实现 insert 命令，在文件的指定行插入 new_str"""
        file_text = self.read_file(path).expandtabs()
        new_str = new_str.expandtabs()
        file_text_lines = file_text.split("\n")
        n_lines_file = len(file_text_lines)

        if insert_line < 0 or insert_line > n_lines_file:
            raise ToolError(
                f"无效的 `insert_line` 参数：{insert_line}。它应在文件行数范围 [0, {n_lines_file}] 内。"
            )

        new_str_lines = new_str.split("\n")
        new_file_text_lines = (
            file_text_lines[:insert_line]
            + new_str_lines
            + file_text_lines[insert_line:]
        )
        snippet_lines = (
            file_text_lines[max(0, insert_line - SNIPPET_LINES) : insert_line]
            + new_str_lines
            + file_text_lines[insert_line : insert_line + SNIPPET_LINES]
        )

        new_file_text = "\n".join(new_file_text_lines)
        snippet = "\n".join(snippet_lines)

        self.write_file(path, new_file_text)
        self._file_history[path].append(file_text)

        success_msg = f"文件 {path} 已被编辑。"
        success_msg += self._make_output(
            snippet,
            "编辑后文件的摘录",
            max(1, insert_line - SNIPPET_LINES + 1),
        )
        success_msg += "请检查改动，确保符合预期（如正确缩进、无重复行等），如有需要请再次编辑文件。"
        return CLIResult(output=success_msg)

    def undo_edit(self, path: Path):
        """实现 undo_edit 命令，将对文件的最后一次编辑撤销"""
        if not self._file_history[path]:
            raise ToolError(f"未找到 {path} 的编辑历史。")

        old_text = self._file_history[path].pop()
        self.write_file(path, old_text)

        return CLIResult(
            output=f"对 {path} 的最后一次编辑已成功撤销。{self._make_output(old_text, str(path))}"
        )

    def read_file(self, path: Path):
        """从给定路径读取文件内容；如果出错则抛出 ToolError。"""
        try:
            return path.read_text()
        except Exception as e:
            raise ToolError(f"在尝试读取 {path} 时遇到错误：{e}") from None

    def write_file(self, path: Path, file: str):
        """将文件内容写入给定路径；如果出错则抛出 ToolError。"""
        try:
            path.write_text(file)
        except Exception as e:
            raise ToolError(f"在尝试写入 {path} 时遇到错误：{e}") from None

    def _make_output(
        self,
        file_content: str,
        file_descriptor: str,
        init_line: int = 1,
        expand_tabs: bool = True,
    ):
        """根据文件内容生成 CLI 输出。"""
        file_content = maybe_truncate(file_content)
        if expand_tabs:
            file_content = file_content.expandtabs()
        file_content = "\n".join(
            [
                f"{i + init_line:6}\t{line}"
                for i, line in enumerate(file_content.split("\n"))
            ]
        )
        return (
            f"以下是执行 `cat -n` 命令后对 {file_descriptor} 输出的结果：\n"
            + file_content
            + "\n"
        )