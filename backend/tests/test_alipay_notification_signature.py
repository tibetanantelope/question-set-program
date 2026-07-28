import base64

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from backend.core.alipay_client import AlipaySandboxClient
from backend.core.exceptions import BusinessError


def signed_parameters():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    parameters = {
        "app_id": "sandbox-app-1",
        "out_trade_no": "ZXB202607250001",
        "trade_no": "20260725220001",
        "trade_status": "TRADE_SUCCESS",
        "total_amount": "19.90",
        "sign_type": "RSA2",
    }
    content = "&".join(
        f"{key}={parameters[key]}"
        for key in sorted(parameters)
        if key not in {"sign", "sign_type"}
    )
    parameters["sign"] = base64.b64encode(
        private_key.sign(content.encode(), padding.PKCS1v15(), hashes.SHA256())
    ).decode()
    return parameters, private_key.public_key()


def test_valid_alipay_notification_signature():
    parameters, public_key = signed_parameters()
    client = AlipaySandboxClient()
    client._public_key = lambda: public_key

    client.verify_notification(parameters)


def test_tampered_alipay_notification_is_rejected():
    parameters, public_key = signed_parameters()
    parameters["total_amount"] = "0.01"
    client = AlipaySandboxClient()
    client._public_key = lambda: public_key

    with pytest.raises(BusinessError) as exc:
        client.verify_notification(parameters)

    assert exc.value.code == "PAYMENT_VERIFY_FAILED"
