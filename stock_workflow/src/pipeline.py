"""
核心管线 — 将数据获取、评分、摘要、推送串联为一次执行
"""
import logging
from datetime import datetime

import pytz

from . import fetcher
from . import scorer
from . import summarizer
from . import push_channels

logger = logging.getLogger(__name__)


def run_pipeline(config: dict) -> dict:
    """
    执行一次完整的数据采集 -> 评分 -> 摘要 -> 推送管线。

    返回执行结果统计。
    """
    result = {
        "success": False,
        "board_found": False,
        "stocks_count": 0,
        "ranked_count": 0,
        "push_results": {},
        "error": None,
    }

    tz = pytz.timezone("Asia/Shanghai")
    now = datetime.now(tz)
    logger.info("=" * 55)
    logger.info(
        "开始执行智能体概念监控管线: %s",
        now.strftime("%Y-%m-%d %H:%M:%S %Z"),
    )

    try:
        # 1. 大盘参考
        logger.info("[1/7] 获取大盘概况")
        overview = fetcher.get_market_overview()

        # 2. 查找概念板块
        logger.info("[2/7] 查找智能体概念板块")
        keywords = config.get("concept_board", {}).get(
            "keywords", ["智能体", "AIAgent"]
        )
        board_code = fetcher.find_concept_board(keywords)

        if not board_code:
            board_code = config.get("concept_board", {}).get(
                "fallback_code"
            )
            if board_code:
                logger.info("使用备用板块代码: %s", board_code)
            else:
                msg = "未找到智能体概念板块，请更新关键词或手动添加板块代码"
                logger.error(msg)
                result["error"] = msg
                return result

        result["board_found"] = True
        logger.info("板块代码: %s", board_code)

        # 3. 获取成分股
        logger.info("[3/7] 获取板块成分股行情数据")
        stocks = fetcher.fetch_board_stocks(board_code, top_n=50)
        result["stocks_count"] = len(stocks)

        if not stocks:
            msg = "未获取到成分股数据"
            logger.error(msg)
            result["error"] = msg
            return result

        # 4. 获取新闻热度
        logger.info("[4/7] 获取各股新闻提及数")
        for i, stock in enumerate(stocks):
            if i % 10 == 0:
                logger.info("  进度: %d/%d", i, len(stocks))
            count = fetcher.fetch_news_mentions_count(
                stock["name"], stock["code"]
            )
            stock["news_mentions_count"] = count
            news = fetcher.fetch_stock_news(stock["code"], page_size=3)
            stock["news"] = news

        # 5. 评分排序
        logger.info("[5/7] 多维度评分排序")
        weights = config.get("scoring", {}).get("weights", {})
        top_n = config.get("scoring", {}).get("top_n", 10)
        ranked = scorer.score_and_rank(stocks, weights=weights, top_n=top_n)
        result["ranked_count"] = len(ranked)

        # 6. 生成摘要
        logger.info("[6/7] 生成摘要和报告")
        ranked = summarizer.generate_all_summaries(ranked)
        text_report = summarizer.generate_report_text(
            ranked, overview=overview
        )
        md_report = summarizer.generate_markdown_report(
            ranked, overview=overview
        )

        date_str = now.strftime("%Y%m%d")
        report_dir = "outputs"
        import os
        os.makedirs(report_dir, exist_ok=True)
        report_file = f"{report_dir}/aiagent_report_{date_str}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(md_report)
        logger.info("报告已保存至: %s", report_file)

        # 7. 多渠道推送
        logger.info("[7/7] 推送报告")
        push_results = push_channels.push_to_all_channels(
            config, text_report, md_report
        )
        result["push_results"] = push_results

        result["success"] = True
        logger.info("管线执行完成 SUCCESS")

    except Exception as e:
        logger.exception("管线执行异常")
        result["error"] = str(e)

    return result
