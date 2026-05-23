"""API 认证签名生成：MD5(key + secret + timestamp + nonce)。

目标接口使用四请求头鉴权方案：
    - X-Auth-Key:       固定的 API Key
    - X-Auth-Timestamp: 毫秒级时间戳
    - X-Auth-Nonce:     随机 UUID
    - X-Auth-Signature: MD5(key + secret + timestamp + nonce)

签名不绑定请求体，因此同一组 timestamp + nonce 可用于任意分页参数。
"""

from __future__ import annotations

import hashlib
import time
import uuid


def generate_auth_headers(key: str, secret: str) -> dict[str, str]:
    """根据 key 和 secret 生成一组完整的认证请求头。

    Args:
        key:    API Key，对应请求头 X-Auth-Key。
        secret: 签名盐值，参与 MD5 计算。

    Returns:
        包含四个认证头的字典，可直接合并到请求 headers 中。
    """
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    raw = key + secret + timestamp + nonce
    signature = hashlib.md5(raw.encode()).hexdigest()
    return {
        "X-Auth-Key": key,
        "X-Auth-Timestamp": timestamp,
        "X-Auth-Nonce": nonce,
        "X-Auth-Signature": signature,
    }
