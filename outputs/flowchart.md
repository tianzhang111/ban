# 脚本代码流程图

## 1. 整体架构流

```mermaid
flowchart TD
    T["Windows Task Scheduler<br/>每天 11:00 触发"] -->|Start-ScheduledTask| MAIN
    
    subgraph MAIN [main.py - 入口]
        P("[main.py] 解析参数")
        P --> C{"-m 参数?"}
        C -->|once| R1["run_once()"]
        C -->|scheduler| SCH["run_scheduler()<br/>→ scheduler.py"]
    end

    R1 --> PIPELINE

    subgraph PIPELINE [pipeline.py - 核心管线]
        S1["[1/7] 获取大盘概况<br/>fetcher.get_market_overview()"]
        S2["[2/7] 查找概念板块<br/>fetcher.find_concept_board()"]
        S2_F{"找到板块?"}
        S2_F -->|否| ERR1["返回: 板块未找到"]
        S2_F -->|是| S3["[3/7] 获取成分股<br/>fetcher.fetch_board_stocks()"]
        S3_F{"有成分股?"}
        S3_F -->|否| ERR2["返回: 无成分股数据"]
        S3_F -->|是| S4["[4/7] 获取新闻热度<br/>循环50只:<br/>fetch_news_mentions_count()<br/>fetch_stock_news()"]
        S4 --> S5["[5/7] 多维度评分排序<br/>scorer.score_and_rank()"]
        S5 --> S6["[6/7] 生成摘要与报告<br/>summarizer.generate_*()"]
        S6 --> S7["[7/7] 多渠道推送<br/>push_channels.push_to_all_channels()"]
    end

    PIPELINE --> RES{"执行成功?"}
    RES -->|是| DONE["输出: 成功结果"]
    RES -->|否| FAIL["输出: 错误信息"]
```

## 2. 数据获取模块 (fetcher.py)

```mermaid
flowchart LR
    subgraph FETCH [东方财富 API 调用]
        A["find_concept_board()<br/>searchadapter.eastmoney.com<br/>搜索: 智能体/AIAgent"] --> B{"已搜索到<br/>板块代码 BK0809?"}
        B -->|否| C["fallback_code<br/>(config.yaml)"]
        B -->|是| D["fetch_board_stocks()<br/>push2.eastmoney.com<br/>bk:BK0809"]
        C --> D
        D --> E["50只成分股<br/>行情 + 资金流"]
        E --> F["fetch_news_mentions_count()<br/>公告API: 获取公告数量"]
        E --> G["fetch_stock_news()<br/>公告API: 获取公告详情"]
        F --> H["返回 stocks[]<br/>(含 news, mentions)"]
        G --> H
    end
```

## 3. 评分排序模块 (scorer.py)

```mermaid
flowchart LR
    subgraph SCORE [评分排序]
        I["输入: stocks[]<br/>50只成分股"] --> J1["提取成交额<br/>normalize()"]
        I --> J2["提取涨跌幅<br/>normalize()"]
        I --> J3["提取资金净流入<br/>normalize()"]
        I --> J4["提取新闻提及数<br/>normalize()"]
        
        J1 --> K1["归一化值 × 0.40"]
        J2 --> K2["归一化值 × 0.30"]
        J3 --> K3["归一化值 × 0.20"]
        J4 --> K4["归一化值 × 0.10"]
        
        K1 --> SUM["综合分 = 加权求和 × 100<br/>0 - 100分"]
        K2 --> SUM
        K3 --> SUM
        K4 --> SUM
        
        SUM --> SORT["降序排列"]
        SORT --> TOP["取 Top 10"]
        TOP --> OUT["输出: ranked[]<br/>(含 composite_score)"]
    end
```

## 4. 摘要与报告生成 (summarizer.py)

```mermaid
flowchart LR
    subgraph SUMMARY [摘要生成]
        IN["输入: ranked[]<br/>Top 10 股票"] --> SUMM["generate_summary()<br/>&lt;50字摘要<br/>名称+价格+涨跌+金额"]
        SUMM --> LINK["组装 news_links<br/>最多3条公告链接"]
        LINK --> TEXT["generate_report_text()<br/>纯文本报告"]
        LINK --> MD["generate_markdown_report()<br/>Markdown报告"]
        TEXT --> SAVE["保存到 outputs/"]
        MD --> SAVE
    end
```

## 5. 推送模块 (push_channels.py)

```mermaid
flowchart TD
    PUSH_IN["输入: config + 两版报告"] --> CHECK{"遍历 push 渠道<br/>检查每个 enabled"}
    
    CHECK --> WECOM{"企业微信<br/>启用?"}
    WECOM -->|是| W1["POST Webhook<br/>msgtype=markdown"]
    WECOM -->|否| FEISHU{"飞书<br/>启用?"}
    W1 --> R1["记录结果"]
    
    FEISHU -->|是| F1["POST Webhook<br/>msg_type=post"]
    FEISHU -->|否| DINGTALK{"钉钉<br/>启用?"}
    F1 --> R2["记录结果"]
    
    DINGTALK -->|是| D1["POST Webhook<br/>msgtype=markdown"]
    DINGTALK -->|否| TELEGRAM{"Telegram<br/>启用?"}
    D1 --> R3["记录结果"]
    
    TELEGRAM -->|是| T1["POST api.telegram.org<br/>parse_mode=Markdown"]
    TELEGRAM -->|否| EMAIL{"邮件<br/>启用?"}
    T1 --> R4["记录结果"]
    
    EMAIL -->|是| E1["SMTP 登录<br/>发送纯文本报告"]
    EMAIL -->|否| DONE2["返回所有渠道的<br/>推送成功/失败状态"]
    E1 --> R5["记录结果"]
```

## 6. 调度模块 (scheduler.py)

```mermaid
flowchart LR
    subgraph SCHED [APScheduler 调度]
        S_IN["start_scheduler()"] --> TRIG["CronTrigger<br/>hour=11, minute=0<br/>Asia/Shanghai"]
        TRIG --> JOB["定时触发 → run_pipeline()"]
        JOB --> WAIT["等待下一次触发<br/>(sleep 60s)"]
        WAIT --> JOB
        
        S_IN --> CTRL{"Ctrl+C?"}
        CTRL -->|是| STOP["shutdown()"]
    end
```

## 完整数据流

```mermaid
flowchart TD
    subgraph D1 [东方财富 API]
        API1["searchadapter<br/>搜索板块"]
        API2["push2<br/>行情 + 资金流"]
        API3["Announce API<br/>公告新闻"]
    end

    subgraph FS [文件系统]
        LOG["logs/stock_workflow.log<br/>运行日志"]
        RPT["outputs/aiagent_report_*.md<br/>每日报告"]
    end

    subgraph PUSH [推送目的地]
        P1["企业微信"]
        P2["飞书"]
        P3["钉钉"]
        P4["Telegram"]
        P5["邮件"]
    end

    D1 -->|HTTP| FETCH["fetcher.py<br/>数据采集"]
    FETCH --> SCORER["scorer.py<br/>四维评分"]
    SCORER --> SUMM["summarizer.py<br/>摘要生成"]
    SUMM -->|Markdown| RPT
    FETCH -->|log| LOG
    SUMM --> PUSH
    PUSH --> P1
    PUSH --> P2
    PUSH --> P3
    PUSH --> P4
    PUSH --> P5
    PUSH -->|send| P1
    PUSH -->|send| P2
    PUSH -->|send| P3
    PUSH -->|send| P4
    PUSH -->|send| P5
```

## 模块依赖图

```mermaid
flowchart TD
    subgraph 入口层
        MAIN["main.py<br/>入口"]
    end
    
    subgraph 业务层
        PIPELINE["pipeline.py<br/>管线编排"]
        SCHED["scheduler.py<br/>定时调度"]
    end
    
    subgraph 功能层
        FETCHER["fetcher.py<br/>东方财富 API"]
        SCORER["scorer.py<br/>评分算法"]
        SUMMARIZER["summarizer.py<br/>摘要 + 报告"]
        PUSH["push_channels.py<br/>多渠道推送"]
    end

    subgraph 外部依赖
        REQ["requests<br/>HTTP 请求"]
        YAML["PyYAML<br/>配置解析"]
        APS["APScheduler<br/>定时任务"]
        PYTZ["pytz<br/>时区"]
    end

    MAIN --> PIPELINE
    MAIN --> SCHED
    
    PIPELINE --> FETCHER
    PIPELINE --> SCORER
    PIPELINE --> SUMMARIZER
    PIPELINE --> PUSH
    
    FETCHER --> REQ
    SCHED --> APS
    SCHED --> PYTZ
    MAIN --> YAML
```

## 评分公式

```mermaid
flowchart LR
    T["成交额 T"] --> TN["Min-Max 归一化<br/>T_norm = (T - T_min)/(T_max - T_min)"]
    C["涨跌幅 C"] --> CN["C_norm"]
    N["资金净流入 N"] --> NN["N_norm"]
    M["新闻提及 M"] --> MN["M_norm"]

    TN --> W1["× 0.40"]
    CN --> W2["× 0.30"]
    NN --> W3["× 0.20"]
    MN --> W4["× 0.10"]

    W1 --> SC["综合分 = 各项加权和 × 100<br/>范围: 0 - 100"]
    W2 --> SC
    W3 --> SC
    W4 --> SC
```
