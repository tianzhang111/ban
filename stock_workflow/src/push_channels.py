"""
多渠道推送模块 — 企业微信 / 飞书 / 钉钉 / Telegram / 邮件
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests

logger = logging.getLogger(__name__)


def push_wecom(webhook_url: str, content: str) -> bool:
    """推送至企业微信机器人"""
    if not webhook_url:
        logger.warning("企业微信: webhook_url 未配置")
        return False
    payload = {
        "msgtype": "markdown",
        "markdown": {"content": content},
    }
    try:
        resp = requests.post(
            webhook_url, json=payload, timeout=10
        )
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info("企业微信推送成功")
            return True
        else:
            logger.warning(
                "企业微信推送失败: %s", result
            )
            return False
    except Exception as e:
        logger.error("企业微信推送异常: %s", e)
        return False


def push_feishu(webhook_url: str, content: str) -> bool:
    """推送至飞书机器人"""
    if not webhook_url:
        logger.warning("飞书: webhook_url 未配置")
        return False
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "content": [
                        [{"tag": "text", "text": content}]
                    ]
                }
            }
        },
    }
    try:
        resp = requests.post(
            webhook_url, json=payload, timeout=10
        )
        result = resp.json()
        if result.get("code") == 0:
            logger.info("飞书推送成功")
            return True
        else:
            logger.warning("飞书推送失败: %s", result)
            return False
    except Exception as e:
        logger.error("飞书推送异常: %s", e)
        return False


def push_dingtalk(webhook_url: str, content: str) -> bool:
    """推送至钉钉机器人"""
    if not webhook_url:
        logger.warning("钉钉: webhook_url 未配置")
        return False
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": "智能体概念热度日报",
            "text": content,
        },
    }
    try:
        resp = requests.post(
            webhook_url, json=payload, timeout=10
        )
        result = resp.json()
        if result.get("errcode") == 0:
            logger.info("钉钉推送成功")
            return True
        else:
            logger.warning("钉钉推送失败: %s", result)
            return False
    except Exception as e:
        logger.error("钉钉推送异常: %s", e)
        return False


def push_telegram(
    bot_token: str, chat_id: str, content: str
) -> bool:
    """推送至 Telegram Bot"""
    if not bot_token or not chat_id:
        logger.warning("Telegram: bot_token 或 chat_id 未配置")
        return False
    url = (
        f"https://api.telegram.org/bot{bot_token}/sendMessage"
    )
    payload = {
        "chat_id": chat_id,
        "text": content,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get("ok"):
            logger.info("Telegram 推送成功")
            return True
        else:
            logger.warning(
                "Telegram 推送失败: %s", result
            )
            return False
    except Exception as e:
        logger.error("Telegram 推送异常: %s", e)
        return False


def push_email(
    smtp_server: str,
    smtp_port: int,
    use_ssl: bool,
    sender: str,
    password: str,
    recipients: list[str],
    subject: str,
    content: str,
) -> bool:
    """推送至邮件（支持纯文本/HTML）"""
    if not all([smtp_server, sender, password, recipients]):
        logger.warning("邮件: 配置不完整")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    # 纯文本
    msg.attach(MIMEText(content, "plain", "utf-8"))

    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(
                smtp_server, smtp_port, timeout=15
            )
        else:
            server = smtplib.SMTP(
                smtp_server, smtp_port, timeout=15
            )
            server.starttls()

        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
        server.quit()

        logger.info(
            "邮件推送成功: %s", recipients
        )
        return True
    except Exception as e:
        logger.error("邮件推送异常: %s", e)
        return False


def push_to_all_channels(
    config: dict,
    text_report: str,
    markdown_report: str,
) -> dict[str, bool]:
    """
    推送到所有已启用的渠道。

    返回: {channel_name: success_or_not}
    """
    results = {}
    push_config = config.get("push", {})

    # 1. 企业微信
    ww = push_config.get("wecom", {})
    if ww.get("enabled", False):
        url = ww.get("webhook_url", "")
        results["wecom"] = push_wecom(url, markdown_report)

    # 2. 飞书
    fs = push_config.get("feishu", {})
    if fs.get("enabled", False):
        url = fs.get("webhook_url", "")
        results["feishu"] = push_feishu(url, text_report)

    # 3. 钉钉
    dd = push_config.get("dingtalk", {})
    if dd.get("enabled", False):
        url = dd.get("webhook_url", "")
        results["dingtalk"] = push_dingtalk(url, markdown_report)

    # 4. Telegram
    tg = push_config.get("telegram", {})
    if tg.get("enabled", False):
        token = tg.get("bot_token", "")
        chat = tg.get("chat_id", "")
        results["telegram"] = push_telegram(
            token, chat, text_report
        )

    # 5. 邮件
    em = push_config.get("email", {})
    if em.get("enabled", False):
        results["email"] = push_email(
            smtp_server=em.get("smtp_server", ""),
            smtp_port=em.get("smtp_port", 465),
            use_ssl=em.get("smtp_use_ssl", True),
            sender=em.get("sender", ""),
            password=em.get("password", ""),
            recipients=em.get("recipients", []),
            subject="A股【AI Agent / 智能体】概念热度日报",
            content=text_report,
        )

    if not results:
        logger.warning("没有已启用的推送渠道")

    return results
