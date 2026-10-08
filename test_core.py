"""P11 本地自测:只测 core_* 纯函数,不依赖网络与机器人。

运行: python test_core.py   (自动使用临时 DB,不动真实数据)
"""
import os
import tempfile
from pathlib import Path

# 用临时库,避免污染真实数据
_TMP = Path(tempfile.mkdtemp()) / "test_db.json"
os.environ["DB_PATH"] = str(_TMP)

from contest_score_server.server import (  # noqa: E402
    core_current, core_query, core_ranking, core_record, core_register,
    core_schedule,
)

PASS = []


def check(name, cond):
    assert cond, f"❌ {name}"
    PASS.append(name)
    print(f"✅ {name}")


# ---- 校验链 ----
check("错误令牌录入被拒绝", "令牌无效" in core_record("张三", "理论", 95, "wrong"))
core_register("王五", "judge-2026")
check("未报名选手录入被拦截", "尚未报名" in core_record("赵六", "理论", 90, "judge-2026"))
check("非法环节名被拒绝", "环节名只能是" in core_record("张三", "笔试", 90, "judge-2026"))
check("非法分数被拒绝", "0 到 100" in core_record("张三", "理论", 150, "judge-2026"))

# ---- 多轮:空令牌追问 + 中文别名(语音说"郭向杰") ----
check("报名缺令牌返回追问", "请说出裁判令牌" in core_register("小红", ""))
check("录入缺令牌返回追问", "请说出裁判令牌" in core_record("张三", "理论", 92, ""))
check("中文别名'郭向杰'报名成功", "报名成功" in core_register("小红", "郭向杰"))
check("中文别名重复报名幂等", "已报名" in core_register("小红", "郭向杰"))
check("中文别名录入成功", "已录入" in core_record("小红", "实操", 92, "郭向杰"))
check("空令牌不泄露选手状态", "尚未报名" not in core_record("赵六", "理论", 90, ""))

# ---- 录入与幂等 ----
check("正常录入成功", "已录入:张三 理论环节 95 分" in core_record("张三", "理论", 95, "judge-2026"))
check("重复录入幂等(不覆盖)", "已有成绩 95 分,本次录入不生效" in core_record("张三", "理论", 80, "judge-2026"))
check("幂等后分数仍是首次值", "95分" in core_query("张三"))

# ---- 持久化 ----
check("数据已落盘", _TMP.exists() and "张三" in _TMP.read_text(encoding="utf-8"))

# ---- 并列排名 ----
core_record("李四", "理论", 95, "judge-2026")
core_record("王五", "理论", 87, "judge-2026")
r = core_ranking("理论", 3)
check("并列分数同名次(两个第1名,下一名第3)", r.count("第1名") == 2 and "第3名" in r and "第2名" not in r)
check("榜单含三人", all(n in r for n in ("张三", "李四", "王五")))

# ---- 模糊查询 ----
check("模糊查询:姓可命中", "李四" in core_query("李"))
check("无匹配提示", "未找到" in core_query("不存在的人"))

# ---- 报名幂等 ----
check("重复报名提示", "已报名" in core_register("王五", "judge-2026"))
check("报名令牌错误拒绝", "令牌无效" in core_register("钱七", "bad"))

# ---- 赛程与时间感知 ----
s = core_schedule()
check("赛程返回三个环节", all(k in s for k in ("09:00", "13:30", "16:00")))
c = core_current()
check("当前环节有结论", ("进行中的环节" in c) or ("尚未开赛" in c))

print(f"\n全部通过:{len(PASS)} 项 ✔  (临时 DB: {_TMP})")
