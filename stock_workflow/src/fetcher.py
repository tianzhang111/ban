"""
数据源模块 — 东方财富 API 获取智能体板块成分股
"""
import logging
import re
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# 东方财富 API 基础地址
PUSH2_BASE = "http://push2.eastmoney.com/api/qt/clist/get"
SEARCH_BASE = "http://searchadapter.eastmoney.com/api/suggest/get"
ANNOUNCE_BASE = "https://np-anotice-stock.eastmoney.com/api/security/ann"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json, text/plain, */*",
}

SEARCH_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
MARKET_INDICES = {
    "上证指数": "1.000001",
    "深证成指": "0.399001",
    "创业板指": "0.399006",
    "科创50": "1.000688",
}


def _request(url: str, params: dict, timeout: int = 15) -> Optional[dict]:
    """通用 GET 请求"""
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("请求失败 [%s]: %s", url, e)
        return None


def find_concept_board(keywords: list[str]) -> Optional[str]:
    """
    通过东方财富搜索 API 查找概念板块代码。

    返回板块代码如 BK0809。
    """
    for kw in keywords:
        params = {
            "input": kw,
            "type": 14,
            "token": SEARCH_TOKEN,
            "count": 3,
        }
        data = _request(SEARCH_BASE, params)
        if not data:
            continue

        try:
            records = (
                data.get("QuotationCodeTable", {})
                .get("Data", [])
            )
            for item in records:
                code = item.get("Code", "")
                name = item.get("Name", "")
                classify = item.get("Classify", "")
                if classify == "BK" and code.startswith("BK"):
                    logger.info("搜索到板块: %s (代码: %s, 关键词: %s)", name, code, kw)
                    return code
        except Exception:
            continue

    logger.warning("未找到匹配的板块，关键词: %s", keywords)
    return None


def fetch_board_stocks(board_code: str, top_n: int = 50) -> list[dict]:
    """
    获取板块成分股实时行情数据。

    字段说明:
      f12=股票代码, f14=名称, f2=最新价, f3=涨跌幅(%),
      f4=涨跌额, f5=成交量(手), f6=成交额(万元),
      f62=主力净流入(万元), f184=主力净占比(%),
      f66=超大单净流入, f69=小单净流入,
      f15=最高, f16=最低, f17=开盘, f18=昨收,
      f20=总市值, f21=流通市值, f168=换手率(%)
    """
    fields = (
        "f12,f14,f2,f3,f4,f5,f6,f62,f184,f66,f69,f15,"
        "f16,f17,f18,f20,f21,f168"
    )
    params = {
        "pn": 1,
        "pz": top_n,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        "fs": f"b:{board_code}",
        "fields": fields,
        "_": int(time.time() * 1000),
    }
    data = _request(PUSH2_BASE, params)
    if not data or "data" not in data or "diff" not in data["data"]:
        logger.error("获取板块成分股失败: %s", board_code)
        return []

    raw_list = data["data"]["diff"]
    logger.info("获取到 %d 只成分股", len(raw_list))

    stocks = []
    for item in raw_list:
        stock = {
            "code": item.get("f12", ""),
            "name": item.get("f14", ""),
            "price": item.get("f2", "-"),
            "change_pct": item.get("f3", 0) or 0,
            "change_amt": item.get("f4", 0) or 0,
            "volume": item.get("f5", 0) or 0,
            "turnover": item.get("f6", 0) or 0,
            "net_inflow": item.get("f62", 0) or 0,
            "net_inflow_pct": item.get("f184", 0) or 0,
            "net_huge": item.get("f66", 0) or 0,
            "net_small": item.get("f69", 0) or 0,
            "high": item.get("f15", "-"),
            "low": item.get("f16", "-"),
            "open": item.get("f17", "-"),
            "pre_close": item.get("f18", "-"),
            "market_cap": item.get("f20", 0) or 0,
            "circ_cap": item.get("f21", 0) or 0,
            "turnover_rate": item.get("f168", 0) or 0,
        }
        stocks.append(stock)

    return stocks


def fetch_news_mentions_count(stock_name: str, stock_code: str) -> int:
    """统计近期该股票的公告数量（近似新闻热度）"""
    params = {
        "page_index": 1,
        "page_size": 10,
        "stock_list": stock_code,
        "ann_type": "A",
    }
    data = _request(ANNOUNCE_BASE, params)
    if data and data.get("data") and data["data"].get("list"):
        return len(data["data"]["list"])
    return 0


def fetch_stock_news(stock_code: str, page_size: int = 3) -> list[dict]:
    """
    获取个股相关公告新闻。

    返回: [{title, url, date, source}]
    """
    params = {
        "page_index": 1,
        "page_size": page_size,
        "stock_list": stock_code,
        "ann_type": "A",
    }
    data = _request(ANNOUNCE_BASE, params)
    news_list = []
    if data and data.get("data") and data["data"].get("list"):
        for item in data["data"]["list"]:
            title = item.get("title_ch") or item.get("title", "")
            art_code = item.get("art_code", "")
            notice_date = item.get("notice_date", "")

            # 构造东方财富公告详情页 URL
            url = ""
            if art_code and stock_code:
                url = (
                    f"https://np-anotice.eastmoney.com/api/security/ann/"
                    f"art/{art_code}"
                )

            if title:
                news_list.append({
                    "title": title,
                    "url": url,
                    "date": notice_date,
                    "source": "东方财富",
                })
    logger.info("股票 %s 获取到 %d 条公告", stock_code, len(news_list))
    return news_list


def get_market_overview() -> dict:
    """获取大盘概况（非交易时段可能返回空数据）"""
    overview = {}
    for name, secid in MARKET_INDICES.items():
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fltt": 2,
            "invt": 2,
            "fields": "f2,f3,f4,f6",
            "_": int(time.time() * 1000),
        }
        data = _request(url, params)
        if data and data.get("data") and data["data"].get("f2") is not None:
            d = data["data"]
            overview[name] = {
                "price": d.get("f2", "-"),
                "change_pct": d.get("f3", 0) or 0,
                "turnover": d.get("f6", 0) or 0,
            }
    if overview:
        logger.info("大盘概况: %s", {k: v["change_pct"] for k, v in overview.items()})
    else:
        logger.info("大盘概况: 当前非交易时段或无数据")
    return overview
