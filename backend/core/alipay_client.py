import base64
import html
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from backend.core.exceptions import BusinessError
from backend.env import load_backend_env


PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


class AlipaySandboxClient:
    def __init__(self):
        load_backend_env()
        self.app_id = os.getenv("ALIPAY_APP_ID", "").strip()
        self.gateway_url = os.getenv("ALIPAY_GATEWAY_URL", "").strip()
        self.return_url = os.getenv("ALIPAY_RETURN_URL", "").strip()
        self.notify_url = os.getenv("ALIPAY_NOTIFY_URL", "").strip()
        self.private_key_path = self._resolve_path(os.getenv("ALIPAY_PRIVATE_KEY_PATH", ""))
        self.alipay_public_key_path = self._resolve_path(os.getenv("ALIPAY_PUBLIC_KEY_PATH", ""))

    @staticmethod
    def _resolve_path(raw_path: str) -> Path:
        path = Path(raw_path.strip())
        return path if path.is_absolute() else PROJECT_ROOT / path

    def _validate_config(self) -> None:
        if not self.app_id or not self.gateway_url:
            raise BusinessError("ALIPAY_NOT_CONFIGURED", "支付宝沙箱参数尚未配置", 503)
        if not self.private_key_path.is_file() or not self.alipay_public_key_path.is_file():
            raise BusinessError("ALIPAY_NOT_CONFIGURED", "支付宝沙箱密钥文件不存在", 503)

    def _private_key(self):
        self._validate_config()
        content = self.private_key_path.read_bytes()
        try:
            return serialization.load_pem_private_key(content, password=None)
        except (TypeError, ValueError):
            try:
                der_content = base64.b64decode(b"".join(content.split()), validate=True)
                return serialization.load_der_private_key(der_content, password=None)
            except (TypeError, ValueError) as exc:
                raise BusinessError("ALIPAY_KEY_INVALID", "支付宝应用私钥格式不正确", 503) from exc

    def _public_key(self):
        self._validate_config()
        content = self.alipay_public_key_path.read_bytes()
        try:
            return serialization.load_pem_public_key(content)
        except (TypeError, ValueError):
            try:
                der_content = base64.b64decode(b"".join(content.split()), validate=True)
                return serialization.load_der_public_key(der_content)
            except (TypeError, ValueError) as exc:
                raise BusinessError("ALIPAY_KEY_INVALID", "支付宝公钥格式不正确", 503) from exc

    @staticmethod
    def _unsigned_content(parameters: dict) -> str:
        return "&".join(
            f"{key}={parameters[key]}"
            for key in sorted(parameters)
            if parameters[key] not in (None, "") and key != "sign"
        )

    def _sign(self, parameters: dict) -> str:
        signature = self._private_key().sign(
            self._unsigned_content(parameters).encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def _parameters(self, method: str, biz_content: dict) -> dict:
        parameters = {
            "app_id": self.app_id,
            "method": method,
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
        }
        parameters["sign"] = self._sign(parameters)
        return parameters

    def create_page_pay_form(self, *, order_no: str, amount: str, subject: str) -> str:
        parameters = self._parameters(
            "alipay.trade.page.pay",
            {
                "out_trade_no": order_no,
                "total_amount": amount,
                "subject": subject,
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "timeout_express": "2h",
            },
        )
        if self.return_url:
            parameters["return_url"] = self.return_url
        if self.notify_url:
            parameters["notify_url"] = self.notify_url
        # return_url/notify_url are common parameters and must be part of the signature.
        parameters.pop("sign")
        parameters["sign"] = self._sign(parameters)
        inputs = "".join(
            f'<input type="hidden" name="{html.escape(key)}" value="{html.escape(str(value), quote=True)}">'
            for key, value in parameters.items()
        )
        return (
            f'<form id="alipay-submit" action="{html.escape(self.gateway_url, quote=True)}" '
            f'method="post">{inputs}</form>'
            '<script>document.getElementById("alipay-submit").submit();</script>'
        )

    def create_page_pay_url(self, *, order_no: str, amount: str, subject: str) -> str:
        parameters = self._parameters(
            "alipay.trade.page.pay",
            {
                "out_trade_no": order_no,
                "total_amount": amount,
                "subject": subject,
                "product_code": "FAST_INSTANT_TRADE_PAY",
                "timeout_express": "2h",
            },
        )
        if self.return_url:
            parameters["return_url"] = self.return_url
        if self.notify_url:
            parameters["notify_url"] = self.notify_url
        parameters.pop("sign")
        parameters["sign"] = self._sign(parameters)
        return f"{self.gateway_url}?{urlencode(parameters)}"

    @staticmethod
    def _extract_signed_content(raw: str, response_key: str) -> str:
        marker = f'"{response_key}"'
        key_at = raw.find(marker)
        if key_at < 0:
            raise ValueError("response node missing")
        start = raw.find("{", key_at + len(marker))
        if start < 0:
            raise ValueError("response object missing")
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(raw)):
            char = raw[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return raw[start : index + 1]
        raise ValueError("incomplete response object")

    def _verify_response(self, raw: str, payload: dict, response_key: str) -> None:
        signature = payload.get("sign")
        if not signature:
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝响应缺少签名", 400)
        try:
            signed_content = self._extract_signed_content(raw, response_key)
            self._public_key().verify(
                base64.b64decode(signature),
                signed_content.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception as exc:
            if isinstance(exc, BusinessError):
                raise
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝响应签名校验失败", 400) from exc

    def verify_notification(self, parameters: dict) -> None:
        """校验支付宝异步通知 RSA2 签名。"""
        signature = parameters.get("sign")
        sign_type = parameters.get("sign_type")
        if not signature or sign_type != "RSA2":
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝通知签名参数不完整", 400)
        signed_content = "&".join(
            f"{key}={parameters[key]}"
            for key in sorted(parameters)
            if key not in {"sign", "sign_type"} and parameters[key] not in (None, "")
        )
        try:
            self._public_key().verify(
                base64.b64decode(signature),
                signed_content.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
        except Exception as exc:
            if isinstance(exc, BusinessError):
                raise
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝通知签名校验失败", 400) from exc

    async def query_trade(self, order_no: str) -> dict:
        parameters = self._parameters(
            "alipay.trade.query",
            {"out_trade_no": order_no},
        )
        try:
            # 支付宝沙箱可直连；不要继承运行环境中的开发代理，否则
            # 支付成功后的主动查单会在到达支付宝前连接失败。
            async with httpx.AsyncClient(timeout=15.0, trust_env=False) as client:
                response = await client.post(
                    self.gateway_url,
                    content=urlencode(parameters),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BusinessError("ALIPAY_UNAVAILABLE", "支付宝沙箱暂时不可用", 503) from exc

        try:
            # 沙箱网关即使返回 JSON，Content-Type 仍可能标成
            # text/html;charset=GBK；显式按 JSON 文本解析，避免 httpx
            # 因错误媒体类型/编码误判导致已支付订单无法同步。
            try:
                raw_response = response.content.decode("utf-8")
                payload = json.loads(raw_response)
            except (UnicodeDecodeError, json.JSONDecodeError):
                raw_response = response.content.decode("gb18030")
                payload = json.loads(raw_response)
            result = payload["alipay_trade_query_response"]
        except (ValueError, KeyError, TypeError) as exc:
            logger.error(
                "支付宝查单响应无法解析: status=%s content_type=%s body=%r",
                response.status_code,
                response.headers.get("content-type"),
                response.text[:500],
            )
            raise BusinessError("PAYMENT_VERIFY_FAILED", "支付宝返回内容无法解析", 400) from exc
        self._verify_response(raw_response, payload, "alipay_trade_query_response")
        return result
