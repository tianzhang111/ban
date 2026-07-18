"""
摘要生成模块 — 为每只股票生成 <50 字摘要 + 关键新闻链接
"""
import logging
from datetime import datetime

import pytz

logger = logging.getLogger(__name__)

BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def _fmt_yi(value: float) -> str:
    """将元转换为亿并格式化，返回如 '3.45亿' 或 '-1.23亿'"""
    yi = value / 100_000_000
    sign = "+" if yi > 0 else ""
    if abs(yi) >= 1:
        return f"{sign}{yi:.2f}亿"
    else:
        wan = value / 10_000
        return f"{sign}{wan:.0f}万"


def generate_summary(stock: dict) -> str:
    """
    根据股票数据生成 <50 字的中文摘要。

    格式:
      [名称] 收[价格]元，涨跌幅 [±x.xx%]，主力净 [±x.xx亿]。
    """
    name = stock.get("name", "未知")
    price = stock.get("price", "-")
    change_pct = stock.get("change_pct", 0)
    turnover = stock.get("turnover", 0) or 0
    net_inflow = stock.get("net_inflow", 0) or 0

    price_str = f"{price}" if price != "-" else "N/A"
    chg_sign = "+" if change_pct > 0 else ""
    chg_str = f"{chg_sign}{change_pct:.2f}%"

    turnover_str = _fmt_yi(turnover)
    inflow_str = _fmt_yi(net_inflow)

    # Build short summary
    summary = (
        f"{name} 收{price_str}元 "
        f"({chg_str}) "
        f"额{turnover_str} "
        f"流{inflow_str}"
    )

    # Ensure < 50 chars (with Chinese = 2 chars each)
    if len(summary) > 48:
        summary = summary[:46] + ".."

    return summary


def generate_all_summaries(stocks: list[dict]) -> list[dict]:
    """为所有股票生成摘要和新闻链接"""
    for stock in stocks:
        stock["summary"] = generate_summary(stock)

        news = stock.get("news", [])
        news_links = []
        for n in news[:3]:
            title = n.get("title", "")
            url = n.get("url", "")
            if title:
                news_links.append({"title": title, "url": url})
        stock["news_links"] = news_links

    logger.info("已为 %d 只股票生成摘要", len(stocks))
    return stocks


def _now_beijing() -> str:
    """返回北京时间字符串"""
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d %H:%M")


def generate_report_text(
    stocks: list[dict],
    board_name: str = "AI Agent / 智能体",
    overview: dict | None = None,
) -> str:
    """
    生成纯文本格式推送报告（适合 Telegram / 邮件）。
    """
    lines = []
    header = f"A股【{board_name}】概念热度日报"
    sep = "=" * 40

    lines.append(header)
    lines.append(sep)
    lines.append("")

    if overview:
        lines.append("大盘参考：")
        for name, data in overview.items():
            cp = data.get("change_pct", 0)
            sign = "+" if cp > 0 else ""
            lines.append(
                f"  {name} {data.get('price', '-')} ({sign}{cp:.2f}%)"
            )
        lines.append("")

    lines.append(f"热度排行 Top {len(stocks)}：")
    lines.append("")

    for stock in stocks:
        rank = stock.get("rank", "?")
        name = stock.get("name", "?")
        code = stock.get("code", "?")
        score = stock.get("composite_score", 0)
        summary = stock.get("summary", "")

        lines.append(f"  #{rank} {name}({code}) - 综合分 {score:.1f}")
        lines.append(f"    {summary}")

        news_links = stock.get("news_links", [])
        if news_links:
            lines.append("    相关公告：")
            for n in news_links[:2]:
                lines.append(f"    - {n['title'][:40]}")
                if n.get("url"):
                    lines.append(f"      {n['url']}")
        lines.append("")

    lines.append(sep)
    lines.append(f"数据来源：东方财富 | {_now_beijing()}")
    lines.append("仅供参考，不构成投资建议")

    return "\n".join(lines)


def generate_markdown_report(
    stocks: list[dict],
    board_name: str = "AI Agent / 智能体",
    overview: dict | None = None,
) -> str:
    """
    生成 Markdown 格式推送报告（适用于企业微信、飞书、钉钉等 Markdown 渠道）。
    """
    parts = []
    parts.append(f"# A股【{board_name}】概念热度日报\n")

    if overview:
        parts.append("## 大盘参考\n")
        parts.append("| 指数 | 最新价 | 涨跌幅 |")
        parts.append("|------|--------|--------|")
        for name, data in overview.items():
            cp = data.get("change_pct", 0)
            sign = "+" if cp > 0 else ""
            parts.append(
                f"| {name} | {data.get('price', '-')} | {sign}{cp:.2f}% |"
            )
        parts.append("")

    parts.append(f"## 热度排行 Top {len(stocks)}\n")

    for stock in stocks:
        rank = stock.get("rank", "?")
        name = stock.get("name", "?")
        code = stock.get("code", "?")
        score = stock.get("composite_score", 0)
        summary = stock.get("summary", "")

        parts.append(
            f"### {rank}. {name}({code}) - 综合分 {score:.1f}\n"
        )
        parts.append(f"> {summary}\n")

        news_links = stock.get("news_links", [])
        if news_links:
            parts.append("**相关公告：**\n")
            for n in news_links[:3]:
                if n.get("url"):
                    parts.append(f"- [{n['title']}]({n['url']})")
                else:
                    parts.append(f"- {n['title']}")
            parts.append("")

    parts.append("---\n")
    parts.append(f"_数据来源：东方财富 | {_now_beijing()}_\n")
    parts.append("_仅供参考，不构成投资建议_\n")

    return "\n".join(parts)
