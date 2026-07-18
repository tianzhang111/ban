"""
评分排序模块 — 按多维权重计算综合热度分
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


def normalize(values: list[float]) -> list[float]:
    """
    Min-Max 归一化到 [0, 1]。
    如果所有值相同则返回 0.5。
    """
    if not values:
        return []
    arr = np.array(values, dtype=float)
    mn, mx = arr.min(), arr.max()
    if mx == mn:
        return [0.5] * len(values)
    return ((arr - mn) / (mx - mn)).tolist()


def score_and_rank(
    stocks: list[dict],
    weights: dict | None = None,
    top_n: int = 10,
) -> list[dict]:
    """
    按权重公式计算综合分并排序。

    评分公式（满分 100）:
      score = turnover_norm * w_turnover
            + change_pct_norm * w_change
            + net_inflow_norm * w_inflow
            + news_mentions_norm * w_news

    权重默认: 成交额 40% + 涨跌幅 30% + 资金净流入 20% + 新闻提及 10%
    """
    if weights is None:
        weights = {
            "turnover": 0.40,
            "change_pct": 0.30,
            "net_inflow": 0.20,
            "news_mentions": 0.10,
        }

    if not stocks:
        logger.warning("评分: 无股票数据")
        return []

    # 提取原始值
    turnovers = [s.get("turnover", 0) or 0 for s in stocks]
    change_pcts = [s.get("change_pct", 0) or 0 for s in stocks]
    net_inflows = [s.get("net_inflow", 0) or 0 for s in stocks]
    news_counts = [
        s.get("news_mentions_count", 0) or 0
        for s in stocks
    ]

    # 归一化
    t_norm = normalize(turnovers)
    c_norm = normalize(change_pcts)
    n_norm = normalize(net_inflows)
    m_norm = normalize(news_counts)

    # 计算综合分 (0~100)
    for i, stock in enumerate(stocks):
        score = (
            t_norm[i] * weights["turnover"]
            + c_norm[i] * weights["change_pct"]
            + n_norm[i] * weights["net_inflow"]
            + m_norm[i] * weights["news_mentions"]
        )
        stock["composite_score"] = round(score * 100, 2)

        # 拆解各项得分（方便调试）
        stock["score_details"] = {
            "turnover_score": round(t_norm[i] * weights["turnover"] * 100, 2),
            "change_score": round(c_norm[i] * weights["change_pct"] * 100, 2),
            "inflow_score": round(n_norm[i] * weights["net_inflow"] * 100, 2),
            "news_score": round(m_norm[i] * weights["news_mentions"] * 100, 2),
        }

    # 按综合分降序排列
    stocks.sort(key=lambda s: s["composite_score"], reverse=True)

    ranked = stocks[:top_n]
    for idx, stock in enumerate(ranked, 1):
        stock["rank"] = idx

    logger.info(
        "评分完成: 共 %d 只股票, 取 Top%d",
        len(stocks), top_n
    )
    return ranked
