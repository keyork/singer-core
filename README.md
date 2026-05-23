# Singer-Core

基于 Playwright 请求拦截的批量数据采集工具。

## 工作原理

Singer-Core 不通过 DOM 模拟点击翻页，而是利用 Playwright 的 `page.route()` 拦截 API 请求，直接修改 POST body 中的分页参数，从响应 JSON 中提取结构化数据。

这种方式绕过了所有 DOM 操作，速度更快、更稳定。

## 功能特性

- **请求拦截采集**：Playwright route 拦截，无需模拟鼠标/键盘
- **自动签名认证**：MD5(key + secret + timestamp + nonce) 四请求头鉴权，Auth Key 从前端请求自动捕获
- **断点续抓**：通过 `progress.txt` 记录已完成页码，中断后自动恢复
- **全量 CSV 导出**：自动收集 API 返回的所有字段，UTF-8 BOM 编码，Excel 直接打开无乱码
- **全配置驱动**：URL、密钥、字段映射均从 `.env` 读取，源码零硬编码
- **Rich 终端美化**：彩色日志 + 进度条 + 采集汇总

## 快速开始

### 1. 安装依赖

```bash
uv sync
uv run playwright install chromium
```

### 2. 配置环境变量

编辑 `.env`：

```bash
# 目标站点
BASE_URL=https://example.com/#/index/list
DETAIL_URL=https://example.com/#/index/detail?id={}
REQUEST_URL=https://example.com/api/queryDataList

# 签名盐值
AUTH_SECRET=your_secret
```

`AUTH_KEY` 无需手动填写，运行时自动从前端请求中捕获。

### 3. 运行

```bash
uv run python -m singer_core
```

采集结果输出到 `output/data.csv`，进度记录在 `progress.txt`。

## 项目结构

```
src/singer_core/
├── __init__.py       # 包入口
├── __main__.py       # CLI 入口（rich 日志 + 汇总）
├── config.py         # pydantic-settings 配置加载
├── auth.py           # MD5 签名生成
├── scraper.py        # Playwright 请求拦截引擎
├── exporter.py       # CSV 追加写入（全量字段）
└── progress.py       # 断点续抓
```

## 开发

```bash
uv run pytest                    # 运行测试
uv run ruff check .              # 代码检查
uv run ruff format .             # 代码格式化
uv run mypy src/singer_core      # 类型检查
```

## 许可证

Apache License 2.0
