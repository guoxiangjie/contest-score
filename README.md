# P11 · 赛事成绩管理 MCP Server

### 服务介绍

> ⚠️ 本节与下一节的标题名是平台要求的字段名,不要改:提交到魔搭 ModelScope MCP 广场时,「从 GitHub 仓库快速创建」会按名字从根 README 提取这两节内容。

具身智能大赛「赛事成绩管理」MCP 服务:为比赛现场提供选手登记、成绩录入、成绩查询(支持姓名模糊匹配)、榜单排名(并列名次)、赛程咨询、当前环节 6 个工具。成绩录入带裁判令牌校验链与幂等防重(语音重复播报不覆盖成绩),全部工具直接返回自然语言文本,适合机器人语音场景。

### 服务配置

```json
{
  "mcpServers": {
    "contest-score": {
      "command": "uvx",
      "args": ["contest-score"],
      "env": {
        "JUDGE_TOKEN": "judge-2026"
      }
    }
  }
}
```

## 1. 本地运行与自测

```bash
cd p11_mcp_score_server
python3 -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt

python test_core.py        # ① 本地自测:校验链/幂等/榜单/持久化(不需要机器人)
python contest_score_server/server.py   # ② 启动服务
# 日志: [contest-score] listening on http://0.0.0.0:9000/mcp
```

可选环境变量:`JUDGE_TOKEN`(默认 judge-2026)、`DB_PATH`(数据文件)、`HOST`/`PORT`(默认 0.0.0.0:9000)。

## 2. MCP Inspector 本地调试(验收 6 个工具)

```bash
npx @modelcontextprotocol/inspector python contest_score_server/server.py
# 或连接已启动的 HTTP 服务:Transport 选 Streamable HTTP,URL 填 http://127.0.0.1:9000/mcp
```

在 Inspector 里逐个验证:
- `record_score` 填错误令牌 → 返回"裁判令牌无效"
- 正确录入 `张三 / 理论 / 95 / judge-2026` → "已录入"
- 再录 `张三 / 理论 / 80 / judge-2026` → "已有成绩 95 分,本次录入不生效"(幂等)
- `query_score` 填"李" → 模糊命中李四
- `top_ranking` 填 `理论` → 并列排名
- `current_stage` → 当前时间对应环节

## 3. 公网部署(给灵心调用)

灵心云端无法访问内网 IP,三选一(详见题库 P11「部署与网络说明」):

**方式 A · ModelScope「创建 MCP Server」+ 可托管部署(国内首选)**
1. 本仓库已推送到 GitHub,根 README 含「服务介绍」「服务配置」两节(魔搭按名字解析);
2. 魔搭 → MCP 广场 → 创建 MCP Server → 从 GitHub 仓库快速创建:填仓库地址,托管类型选**可托管部署**(选"仅分发展示"不会给公网 URL,灵心无法调用);
3. 平台构建托管实例并分配公网 URL 后,进入下一步。

**方式 B · 云服务器/VPS**:`pip install -e . && contest-score`,开放 9000 端口。

**方式 C · 内网穿透(应急)**:cpolar/natapp/frp 把 127.0.0.1:9000 映射到公网。

## 4. 绑定灵心(端到端)

1. 灵心平台 → 资源中心 → 插件管理 → 添加:
   - 名称:赛事成绩管理
   - 描述:查询大赛选手成绩、榜单与赛程,支持裁判报名与成绩录入
   - 识别示例:当裁判说"报名/登记某选手""录入某选手某环节多少分"时调用对应工具;当选手或观众问"某选手多少分""排名榜单""今天赛程/现在比到哪"时调用查询类工具;与赛事成绩无关的问题(闲聊、天气)不调用任何工具
   - 插件 URL:`http://<公网地址>/mcp`,鉴权按需
2. 工具列表确认 6 个工具"已连接",点「调试」验证;
3. 智能体编辑 → 资源配置 → 插件 → 勾选并保存;
4. 语音验收:"裁判令牌 judge-2026,张三理论环节 95 分"→ 录入;再说一遍 → 幂等提示;
   "查一下张三的成绩" → 播报;"李四排第几" → 两步工具调用后报名次。

## 5. 注意事项

- 平台要求 MCP 工具**直接返回文本**,本服务已全部返回自然语言字符串;
- 云端容器重启后 DB 文件会丢:"持久化"考核点用本地自测(①)验收,云端只演示链路;
- 隧道地址变化后,灵心插件工具列表点「刷新」。
