from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from okdata_api import runner


class WechatAccountArticlesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        yield from runner.run(self, runner.SPECS["wechat_account_articles"], tool_parameters)
