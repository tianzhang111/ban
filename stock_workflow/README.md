# A股 AI Agent / 智能体 概念热度监控 — 部署手册

每天 11:00（北京时间）自动抓取 A股 "AI Agent / 智能体" 概念板块成分股，按成交额、涨跌幅、资金净流入、新闻热度四维评分，生成 Top10 排行和摘要，推送至聊天平台。

---

## 1. 环境准备

### 1.1 确认 Python

打开 PowerShell，确认 Python 可用：

```powershell
python --version
```

如果看到 `Python 3.8+`，直接用 `python` 即可。  
如果报错或指向了 Windows Store 的 python 存根，用绝对路径：

```powershell
& "E:\python\python.exe" --version
```

找到你系统上正确的 Python 路径后，可以把它存为 `$env:Path` 或直接用全路径。本项目的 `setup_scheduler.ps1` 已经预设了 `E:\python\python.exe` 作为首选路径，如果不同请自行修改。

### 1.2 安装依赖

```powershell
cd C:\Users\86173\Documents\Codex\2026-07-16\ban\stock_workflow

# 如果用 python 命令
pip install -r requirements.txt

# 如果用全路径
& "E:\python\python.exe" -m pip install -r requirements.txt
```

### 1.3 验证模块导入

```powershell
& "E:\python\python.exe" -c "import sys; sys.path.insert(0, '.'); from src import fetcher, scorer, summarizer, push_channels, pipeline, scheduler; print('OK')"
```

看到 `OK` 表示环境就绪。

---

## 2. 配置文件填写

编辑 `config.yaml`。

### 2.1 板块搜索（一般不需要改）

```yaml
concept_board:
  keywords: ["智能体", "AIAgent", "AI Agent"]   # 搜索关键词
```

脚本会自动搜索东方财富的概念板块，找到匹配的板块代码（当前是 BK0809）。东方财富板块命名可能变化，如果以后搜不到，可改成实际名称。

### 2.2 评分权重（一般不需要改）

```yaml
scoring:
  weights:
    turnover: 0.40      # 成交额
    change_pct: 0.30    # 涨跌幅
    net_inflow: 0.20    # 主力资金净流入
    news_mentions: 0.10 # 新闻提及
  top_n: 10             # 取前 N 只
```

### 2.3 推送渠道配置

各渠道的获取方式如下。

---

#### 2.3.1 企业微信机器人

1. 打开企业微信，进入目标群聊
2. 点击群设置 > **群机器人** > **添加** > **新机器人**
3. 给机器人起名，复制 **Webhook URL**
4. 填到配置文件：

```yaml
wecom:
  enabled: true
  webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxxx-xxxx-xxxx"
```

---

#### 2.3.2 飞书机器人

1. 打开飞书，进入目标群聊
2. 点击群设置 > **群机器人** > **添加机器人** > **自定义机器人**
3. 填写名称描述，复制 **Webhook URL**
4. 填到配置文件：

```yaml
feishu:
  enabled: true
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-xxxx"
```

---

#### 2.3.3 钉钉机器人

1. 打开钉钉，进入目标群聊
2. 点击群设置 > **智能群助手** > **添加机器人** > **自定义**
3. 安全设置选 **自定义关键词**，填：`A股`
4. 复制 **Webhook URL**
5. 填到配置文件：

```yaml
dingtalk:
  enabled: true
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxxx"
```

---

#### 2.3.4 Telegram Bot

1. 在 Telegram 中搜索 `@BotFather`，发送 `/newbot`，按提示创建机器人
2. 创建成功后会收到 **Bot Token**，格式如 `123456:ABC-DEF1234ghI`
3. 搜索你刚创建的机器人用户名，点击 **Start**
4. 获取 Chat ID：

```powershell
# 将 BOT_TOKEN 换成你的
curl "https://api.telegram.org/bot<BOT_TOKEN>/getUpdates"
# 在返回的 JSON 中找到 chat.id
```

5. 填到配置文件：

```yaml
telegram:
  enabled: true
  bot_token: "123456:ABC-DEF1234ghI"
  chat_id: "123456789"
```

---

#### 2.3.5 邮件（SMTP）

以 QQ 邮箱为例：

1. 登录 QQ 邮箱，进入 **设置** > **账户** > **POP3/IMAP/SMTP 服务**
2. 开启 **SMTP 服务**，生成 **授权码**
3. 填到配置文件：

```yaml
email:
  enabled: true
  smtp_server: "smtp.qq.com"
  smtp_port: 465
  smtp_use_ssl: true
  sender: "your_email@qq.com"
  password: "xxxxxx"           # 这里填授权码，不是 QQ 密码
  recipients:
    - "your_email@qq.com"
    - "other@example.com"      # 可以多个收件人
```

其他常见邮箱的 SMTP 配置：

| 邮箱 | SMTP 服务器 | 端口 | SSL |
|------|------------|------|-----|
| QQ | smtp.qq.com | 465 | 是 |
| 163 | smtp.163.com | 465 | 是 |
| Gmail | smtp.gmail.com | 587 | 否（需 STARTTLS） |
| Outlook | smtp.office365.com | 587 | 否（需 STARTTLS） |

> 如果使用 587 端口（非 SSL），将 `smtp_use_ssl` 设为 `false`，脚本会自动使用 STARTTLS。

---

## 3. 首次测试（不加推送）

先将所有推送渠道设为 `enabled: false`，确认数据能正常拉取：

```powershell
& "E:\python\python.exe" main.py
```

成功时输出类似：

```
执行成功!
  板块找到: True
  原始股票: 50
  排行数量: 10
  推送结果: {}
```

报告会保存到 `outputs/` 目录，如 `aiagent_report_20260716.md`。可以打开看看数据是否合理。

### 常见问题

**报错 `No module named 'src.fetcher'`**

```powershell
cd C:\Users\86173\Documents\Codex\2026-07-16\ban\stock_workflow
```

确保工作目录是项目根目录。

**报错 `板块未找到`**

东方财富的概念板块名称可能已更新。手动搜索：

```powershell
& "E:\python\python.exe" -c "import sys; sys.path.insert(0, '.'); from src.fetcher import find_concept_board; print(find_concept_board(['智能体', 'AI', '人工智能']))"
```

如果找不到，在 `config.yaml` 中加一个 `fallback_code`：

```yaml
concept_board:
  keywords: ["智能体", "AIAgent"]
  fallback_code: "BK0809"    # 手动指定板块代码
```

---

## 4. 推送验证

数据确认无误后，开启一个推送渠道，再跑一次确认消息能正常送达：

```powershell
& "E:\python\python.exe" main.py
```

成功时输出包含：

```
  推送结果: {'wecom': True}   # 或 feishu / dingtalk / telegram / email
```

---

## 5. 设置定时任务

### 方式 A：Windows 任务计划（推荐，无需常驻）

**第一步：** 以 **管理员身份** 打开 PowerShell

**第二步：** 执行注册脚本

```powershell
cd C:\Users\86173\Documents\Codex\2026-07-16\ban\stock_workflow
.\setup_scheduler.ps1
```

成功时显示：

```
任务计划 [AIAgentStockMonitor] 已注册成功！
触发时间: 每天 11:00
```

**第三步：** 验证任务已注册

```powershell
Get-ScheduledTask -TaskName "AIAgentStockMonitor" | Format-List
```

**第四步：** 立即触发一次，测试任务是否能正常运行

```powershell
Start-ScheduledTask -TaskName "AIAgentStockMonitor"
```

稍后检查日志：

```powershell
Get-Content "logs/stock_workflow.log" -Tail 20
```

**管理命令：**

| 操作 | 命令 |
|------|------|
| 查看下次运行时间 | `Get-ScheduledTask "AIAgentStockMonitor" \| Get-ScheduledTaskInfo` |
| 手动立即执行 | `Start-ScheduledTask "AIAgentStockMonitor"` |
| 停止正在执行的任务 | `Stop-ScheduledTask "AIAgentStockMonitor"` |
| 删除任务计划 | `Unregister-ScheduledTask "AIAgentStockMonitor" -Confirm:$false` |
| 禁用但保留 | `Disable-ScheduledTask "AIAgentStockMonitor"` |
| 重新启用 | `Enable-ScheduledTask "AIAgentStockMonitor"` |

### 方式 B：APScheduler 常驻模式（调试用）

如果需要在前台观察运行过程，用调度模式：

```powershell
& "E:\python\python.exe" main.py -m scheduler
```

按 `Ctrl+C` 停止。

如果想启动时立即跑一次再进入调度，加 `--run-now`：

```powershell
& "E:\python\python.exe" main.py -m scheduler --run-now
```

---

## 6. 日常维护

### 6.1 检查日志

```powershell
# 查看最近的运行记录
Get-Content "logs/stock_workflow.log" -Tail 30

# 实时跟踪
Get-Content "logs/stock_workflow.log" -Tail 0 -Wait
```

### 6.2 查看历史报告

```powershell
Get-ChildItem outputs\*.md | Select-Object Name, Length, @{N="Modified";E={$_.LastWriteTime}} | Sort-Object Modified -Descending
```

### 6.3 更新配置

修改 `config.yaml` 后，无需重启任务计划，下次执行会自动读取最新配置。如果需要立即生效，手动执行一次：

```powershell
Start-ScheduledTask -TaskName "AIAgentStockMonitor"
```

### 6.4 推送渠道故障排查

| 问题 | 检查项 |
|------|--------|
| 企业微信推送失败 | Webhook URL 是否正确？机器人是否被移除？ |
| 飞书推送失败 | Webhook URL 是否正确？群机器人是否启用？ |
| 钉钉推送失败 | 是否设置了自定义关键词？关键词必须包含在消息中（已内置"A股"） |
| Telegram 推送失败 | Token 是否有效？Chat ID 是否正确？Bot 是否已 Start？ |
| 邮件推送失败 | 是否用了授权码而非密码？163/QQ 是否开启了 SMTP 服务？ |

---

## 7. 整体架构

```
                     [Windows Task Scheduler]
                     每天早上 11:00 触发
                              |
                     +--------v--------+
                     |    main.py      |
                     |  -m once        |
                     +--------+--------+
                              |
                     +--------v--------+
                     |   pipeline.py   |
                     |  7 步执行管线   |
                     +--------+--------+
                              |
          +-------------------+-------------------+
          |                   |                   |
  +-------v-------+   +------v------+   +--------v--------+
  |   fetcher.py   |   |  scorer.py  |   | summarizer.py   |
  | 东方财富 API   |   | 归一化+加权  |   | <50字摘要+报告  |
  +----------------+   +-------------+   +-----------------+
          |
          v
  +-------------------+
  |  push_channels.py |
  | 企微/飞书/钉钉/   |
  | Telegram/邮件     |
  +-------------------+
```

### 数据流

1. fetcher 通过东方财富搜索 API 找到 `AI智能体` 板块代码（BK0809）
2. 拉取 50 只成分股的行情：股价、涨跌幅、成交额、主力净流入
3. 获取每只股票的公告数量和详情
4. scorer 对四项指标做 Min-Max 归一化，按权重加权得到 0-100 综合分
5. 取 Top 10，summarizer 为每只生成 `<50 字` 摘要
6. 组装纯文本 + Markdown 两版报告
7. push_channels 逐一向已启用的渠道推送

---

## 8. 免责声明

- 数据来源为东方财富公开 API，仅供学习和研究参考
- 不构成任何投资建议，使用风险自负
- 实际交易决策请咨询专业机构
