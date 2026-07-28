# 支付宝沙箱密钥

本目录用于本地支付宝沙箱密钥，不得提交真实密钥。

请创建或替换以下两个本地文件的全部内容：

- `alipay_app_private_key.pem`：支付宝开放平台中的“应用私钥”；
- `alipay_public_key.pem`：支付宝开放平台中的“支付宝公钥”，不是应用公钥。

私钥文件格式：

```text
-----BEGIN PRIVATE KEY-----
完整应用私钥
-----END PRIVATE KEY-----
```

支付宝公钥文件格式：

```text
-----BEGIN PUBLIC KEY-----
完整支付宝公钥
-----END PUBLIC KEY-----
```

沙箱买家账号、登录密码和支付密码只用于手动登录沙箱收银台，不写入 `.env`。

本地开发不配置 `ALIPAY_NOTIFY_URL`，支付完成后通过同步返回页触发后端主动查询订单。
