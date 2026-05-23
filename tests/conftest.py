from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture()
def sample_records() -> list[dict[str, Any]]:
    return [
        {
            "axbe0003": "Test Org A",
            "axbe0013": "123 Test Street",
            "ahae0012": "010-12345678",
            "point": "116.39,39.92",
            "ahae0633Name": "机构服务",
            "tag": "公办民营",
        },
        {
            "axbe0003": "Test Org B",
            "axbe0013": "456 Another Ave",
            "ahae0012": "021-87654321",
            "point": "121.47,31.23",
            "ahae0633Name": "喘息服务",
            "tag": "医养结合",
        },
    ]


@pytest.fixture()
def mock_response_single_page() -> dict[str, Any]:
    return {
        "code": 200,
        "data": {
            "total": 2,
            "size": 10,
            "current": 1,
            "pages": 1,
            "records": [
                {
                    "axbe0003": "Test Org",
                    "axbe0013": "123 Test St",
                    "ahae0012": "010-12345678",
                    "point": "116.39,39.92",
                    "ahae0633Name": "机构服务",
                    "tag": "公办民营",
                },
            ],
        },
    }


@pytest.fixture()
def mock_response_multi_page() -> list[dict[str, Any]]:
    record = {
        "axbe0003": "Test Org",
        "axbe0013": "123 Test St",
        "ahae0012": "010-12345678",
        "point": "116.39,39.92",
        "ahae0633Name": "机构服务",
        "tag": "公办民营",
    }
    return [
        {
            "code": 200,
            "data": {
                "total": 20,
                "size": 10,
                "current": i,
                "pages": 2,
                "records": [record] * 10,
            },
        }
        for i in range(1, 3)
    ]


@pytest.fixture()
def env_vars(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    vals = {
        "BASE_URL": "https://example.com/#/index/list",
        "DETAIL_URL": "https://example.com/#/index/detail?id={}",
        "REQUEST_URL": "https://example.com/api/queryDataList",
        "AUTH_KEY": "test_key_123",
        "AUTH_SECRET": "test_secret_456",
    }
    for k, v in vals.items():
        monkeypatch.setenv(k, v)
    return vals
