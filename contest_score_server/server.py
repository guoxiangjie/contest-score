"""P11 · 赛事成绩管理 MCP Server(题库参考答案 · 可运行版)

运行: python server.py   (或 pip install -e . 后执行 contest-score)
自测: python ../test_core.py(只测 core_* 纯函数,不依赖网络)
"""
import json
import os
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

JUDGE_TOKEN = os.environ.get("JUDGE_TOKEN", "judge-2026")
DB_PATH = Path(os.environ.get("DB_PATH", "contest_db.json"))
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "9000"))
STAGES = ("理论", "实操", "编程")

mcp = FastMCP("contest-score", host=HOST, port=PORT)

DEFAULT_DB = {
    "players": {"张三": {}, "李四": {}},   # 姓名 -> {环节: 分数}
    "schedule": [["09:00", "基础理论笔试"], ["13:30", "实操考核"], ["16:00", "编程题答辩"]],
}


# ---------------- 核心业务逻辑(纯函数,便于本地自测) ----------------

def load_db() -> dict:
    if not DB_PATH.exists():
        DB_PATH.write_text(json.dumps(DEFAULT_DB, ensure_ascii=False), encoding="utf-8")
    return json.loads(DB_PATH.read_text(encoding="utf-8"))


def save_db(db: dict) -> None:
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")


def core_register(name: str, judge_token: str) -> str:
    if judge_token != JUDGE_TOKEN:
        return "报名失败:裁判令牌无效。"
    db = load_db()
    name = name.strip()
    if name in db["players"]:
        return f"「{name}」已报名,无需重复登记。"
    db["players"][name] = {}
    save_db(db)
    return f"选手「{name}」报名成功。"


def core_record(name: str, stage: str, score: float, judge_token: str) -> str:
    """校验链:令牌 → 环节名 → 分数范围 → 选手存在 → 幂等(同环节不覆盖)"""
    if judge_token != JUDGE_TOKEN:
        return "录入失败:裁判令牌无效,请联系赛项组。"
    if stage not in STAGES:
        return f"录入失败:环节名只能是 {'/'.join(STAGES)}。"
    if not (0 <= score <= 100):
        return "录入失败:分数须在 0 到 100 之间。"
    db = load_db()
    player = db["players"].get(name.strip())
    if player is None:
        return f"录入失败:「{name}」尚未报名,请先登记。"
    if stage in player:                       # 幂等:语音"再说一遍"不覆盖
        return f"「{name}」{stage}环节已有成绩 {player[stage]} 分,本次录入不生效。"
    player[stage] = score
    save_db(db)
    return f"已录入:{name} {stage}环节 {score} 分。"


def core_query(name: str) -> str:
    db = load_db()
    hits = [n for n in db["players"] if name.strip() in n]   # 模糊匹配
    if not hits:
        return f"未找到与「{name}」匹配的选手。"
    lines = [f"{n}:{'、'.join(f'{s} {v}分' for s, v in db['players'][n].items()) or '暂无成绩'}"
             for n in hits]
    return ";".join(lines)


def core_ranking(stage: str, n: int = 3) -> str:
    if stage not in STAGES:
        return f"环节名只能是 {'/'.join(STAGES)}。"
    db = load_db()
    rows = sorted(((p[stage], name) for name, p in db["players"].items() if stage in p),
                  key=lambda kv: -kv[0])[: max(1, n)]
    out, rank, prev = [], 0, None
    for i, (score, name) in enumerate(rows):
        rank = i + 1 if score != prev else rank               # 并列同名次
        prev = score
        out.append(f"第{rank}名 {name} {score}分")
    return (f"{stage}环节榜单:" + ";".join(out)) if out else f"{stage}环节暂无成绩。"


def core_schedule() -> str:
    db = load_db()
    return "今日赛程:" + ",".join(f"{t} {item}" for t, item in db["schedule"])


def core_current() -> str:
    now = time.strftime("%H:%M")
    db = load_db()
    current = "尚未开赛"
    for t, item in db["schedule"]:
        if now >= t:
            current = item
    return f"当前时间 {now},进行中的环节:{current}。"


# ---------------- MCP 工具包装(docstring 即"应调用/不应调用"边界) ----------------

@mcp.tool()
def register_player(name: str, judge_token: str) -> str:
    """裁判为选手报名登记。仅当裁判说"报名/登记某选手"时调用;
    查询成绩、榜单、赛程时不调用。name 为选手中文姓名,judge_token 为裁判令牌。"""
    return core_register(name, judge_token)


@mcp.tool()
def record_score(name: str, stage: str, score: float, judge_token: str) -> str:
    """裁判录入选手某环节成绩。仅当裁判报分、录入成绩意图时调用;
    选手查询自己成绩时不调用(应使用查成绩工具)。stage 只能是:理论/实操/编程;
    score 为 0 到 100 的分数;judge_token 为裁判令牌。同一选手同一环节重复录入
    不会覆盖,始终返回首次录入的结果(语音识别重试场景的幂等保护)。"""
    return core_record(name, stage, score, judge_token)


@mcp.tool()
def query_score(name: str) -> str:
    """查询选手成绩。当用户问"某选手考了多少分/成绩如何"时调用;
    问排名榜单、赛程安排时不调用。name 支持模糊匹配(说出姓氏即可)。"""
    return core_query(name)


@mcp.tool()
def top_ranking(stage: str, n: int = 3) -> str:
    """查询指定环节榜单前 N 名,并列名次相同。当用户问排名、榜单、谁最强时调用;
    查具体某人分数不调用(用查成绩工具)。stage 为:理论/实操/编程。"""
    return core_ranking(stage, n)


@mcp.tool()
def query_schedule() -> str:
    """查询今日赛程安排。当用户问几点比什么、接下来什么环节时调用。"""
    return core_schedule()


@mcp.tool()
def current_stage() -> str:
    """判断当前正在进行哪个赛程环节。当用户问"现在比到哪了/当前环节"时调用。"""
    return core_current()


def main():
    """默认 stdio(魔搭/ModelScope、Inspector 等托管平台标准模式);
    设 MCP_TRANSPORT=http 可切 streamable-http(云服务器直跑场景,监听 HOST:PORT/mcp)"""
    if os.environ.get("MCP_TRANSPORT", "stdio") == "http":
        print(f"[contest-score] listening on http://{HOST}:{PORT}/mcp  (DB: {DB_PATH.resolve()})")
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
