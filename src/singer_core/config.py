"""应用配置：通过 pydantic-settings 从 .env 文件和环境变量加载所有运行参数。

支持的配置项：
    - 目标站点 URL（base_url / detail_url / request_url）
    - 认证凭据（auth_key / auth_secret）
    - 采集参数（page_size / delay_seconds）
    - 输出设置（output_dir / output_filename / progress_file）
    - 导出字段映射（export_fields / export_headers）

所有敏感信息和目标 URL 均从 .env 读取，源码中不包含任何硬编码值。
"""

from __future__ import annotations

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """全局配置模型，字段自动映射到同名环境变量。

    示例 .env:
        BASE_URL=https://example.com/#/index/list
        REQUEST_URL=https://example.com/api/queryDataList
        AUTH_KEY=your_key
        AUTH_SECRET=your_secret
    """

    # ── 目标站点 ──
    base_url: str
    detail_url: str
    request_url: str

    # ── 认证 ──
    # auth_key 默认为空，运行时由 scraper 从前端请求头自动捕获
    # 如需手动指定也可在 .env 中设置
    auth_key: str = ""
    auth_secret: str = "ylfwxxpt"

    # ── 采集参数 ──
    page_size: int = 10
    delay_seconds: float = 1.0

    # ── 输出 ──
    output_dir: str = "output"
    output_filename: str = "data.csv"
    progress_file: str = "progress.txt"

    # ── CSV 字段映射 ──
    # export_fields: 要从 API 响应中提取并写入 CSV 的字段名列表
    # export_headers: 字段名 → CSV 列标题 的映射，用于生成人类可读的表头
    export_fields: list[str] = Field(
        default_factory=lambda: [
            "axbe0003",
            "axbe0013",
            "ahae0012",
            "point",
            "ahae0633Name",
            "tag",
        ]
    )
    export_headers: dict[str, str] = Field(
        default_factory=lambda: {
            "axbe0003": "名称",
            "axbe0013": "地址",
            "ahae0012": "电话",
            "point": "经纬度",
            "ahae0633Name": "服务类型",
            "tag": "标签",
        }
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_config() -> AppConfig:
    """先加载 .env 到进程环境，再用 pydantic-settings 解析配置。"""
    load_dotenv()
    return AppConfig()
