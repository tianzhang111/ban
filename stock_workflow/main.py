"""
A股智能体概念监控 — 入口
"""
import argparse
import logging
import logging.handlers
import os
import sys

import yaml


def setup_logging(config: dict):
    """配置日志"""
    log_cfg = config.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    log_file = log_cfg.get("file", "logs/stock_workflow.log")
    max_bytes = log_cfg.get("max_bytes", 10 * 1024 * 1024)
    backup_count = log_cfg.get("backup_count", 7)

    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件日志（轮转）
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count,
        encoding="utf-8",
    )
    fh.setFormatter(formatter)

    # 控制台日志
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(fh)
    root.addHandler(ch)


def load_config(path: str) -> dict:
    """加载 YAML 配置"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_once(config_path: str):
    """单次执行入口"""
    config = load_config(config_path)
    setup_logging(config)

    from src.pipeline import run_pipeline

    logger = logging.getLogger(__name__)
    logger.info("=" * 55)
    logger.info("智能体概念监控 — 单次执行")
    logger.info("=" * 55)

    result = run_pipeline(config)

    if result["success"]:
        print(f"\n执行成功!")
        print(f"  板块找到: {result['board_found']}")
        print(f"  原始股票: {result['stocks_count']}")
        print(f"  排行数量: {result['ranked_count']}")
        print(f"  推送结果: {result['push_results']}")
    else:
        print(f"\n执行失败: {result.get('error', '未知错误')}")

    return result


def run_scheduler(config_path: str):
    """调度模式 — 每天 11:00 自动运行"""
    config = load_config(config_path)
    setup_logging(config)

    from src.scheduler import start_scheduler

    logger = logging.getLogger(__name__)
    logger.info("=" * 55)
    logger.info("智能体概念监控 — 调度模式启动")
    logger.info("=" * 55)

    start_scheduler(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A股智能体概念热度监控"
    )
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["once", "scheduler"],
        default="once",
        help="运行模式: once=单次, scheduler=调度 (默认: once)",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="立即运行一次（在调度启动之前）",
    )
    args = parser.parse_args()

    if args.mode == "once":
        run_once(args.config)
    else:
        # scheduler 模式
        config = load_config(args.config)
        setup_logging(config)
        from src.scheduler import start_scheduler

        if args.run_now:
            from src.pipeline import run_pipeline
            result = run_pipeline(config)
            print(f"Run-now result: {result['success']}")

        start_scheduler(config)
