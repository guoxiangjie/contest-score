"""P11 stdio 全链路验证:用官方 MCP 客户端以 stdio 方式拉起 server.py,
走真实 MCP 协议完成 initialize → 列工具 → 调用工具。
魔搭等托管平台即以此方式运行,本脚本通过 = 平台可跑。
运行: python test_stdio_client.py
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "stdio_db.json")

SERVER = Path(__file__).parent / "contest_score_server" / "server.py"


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)],
                                   env={**os.environ})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("✅ initialize 成功,工具清单:", names)
            assert len(names) == 6, "应有 6 个工具"

            r1 = await session.call_tool("record_score",
                                         {"name": "张三", "stage": "理论",
                                          "score": 95, "judge_token": "judge-2026"})
            print("✅ 录入:", r1.content[0].text)
            r2 = await session.call_tool("record_score",
                                         {"name": "张三", "stage": "理论",
                                          "score": 80, "judge_token": "judge-2026"})
            print("✅ 幂等:", r2.content[0].text)
            r3 = await session.call_tool("query_score", {"name": "张"})
            print("✅ 查询:", r3.content[0].text)
            r4 = await session.call_tool("top_ranking", {"stage": "理论", "n": 3})
            print("✅ 榜单:", r4.content[0].text)
            assert "已录入" in r1.content[0].text and "不生效" in r2.content[0].text
            print("\nstdio 全链路验证通过 ✔(魔搭托管模式可用)")


asyncio.run(main())
