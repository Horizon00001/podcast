# AI Podcast Studio

> 从 RSS 资讯到可播放播客：自动抓取内容、规划节目、生成双人剧本，并合成为完整音频。

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=111111)
![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Dev-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-Apache--2.0-blue?style=for-the-badge)

`AI Podcast Studio` 是一个全栈 AI 播客生成系统。它把 RSS 订阅源中的文章转换成结构化节目策划，再调用大模型生成播客脚本，最后通过 TTS 合成完整音频。项目同时提供 FastAPI 后端、React 管理界面和命令行流水线，适合做资讯播客、学习摘要、产品周报、技术日报等场景。

## Highlights

| 能力 | 说明 |
| --- | --- |
| RSS 聚合 | 从 `config/feed.json` 读取订阅源，抓取并整理资讯内容 |
| 主题策划 | 根据主题配置和内容聚类生成节目编排 |
| AI 剧本 | 使用 `pydantic-ai` + DeepSeek 生成结构化播客脚本 |
| 语音合成 | 支持 DashScope CosyVoice 和 Edge TTS |
| 音频包装 | 自动加入开场、转场、结尾音乐并合成完整节目 |
| Web 管理 | 前端支持播客列表、详情、生成任务、订阅、模型、设置、点赞、收藏 |
| 任务进度 | 生成任务支持状态查询、取消和 SSE 日志流 |
| 推荐系统 | 结合用户交互、内容相似度、热度、新鲜度和时段上下文推荐播客 |

## Preview

项目演示素材位于 `docs/`：

| 文件 | 说明 |
| --- | --- |
| `docs/demo.mp4` | 项目演示视频 |
| `docs/image.png` | 页面截图 |
| `docs/api_contract.md` | API 契约说明 |
| `docs/deployment.md` | 部署说明 |

## How It Works

```text
RSS Feeds
   |
   v
Fetch & Clean Articles
   |
   v
Topic Selection & Episode Planning
   |
   v
LLM Script Generation
   |
   v
TTS Segment Synthesis
   |
   v
Music Mixing & Final MP3
   |
   v
Web Playback / API / Output Files
```

完整流水线由 `backend/app/pipelines/podcast_pipeline.py` 驱动，大致分为四步：

1. 读取 `config/feed.json` 并抓取 RSS 内容。
2. 按主题和聚类结果生成 `episode_plan.json`。
3. 调用大模型生成 `podcast_script.json` 和 `podcast_script.txt`。
4. 调用 TTS 分段合成语音，再用 `ffmpeg` 合并为完整音频。

## Tech Stack

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11+, FastAPI, SQLAlchemy, Pydantic v2, pytest |
| 前端 | React 19, TypeScript, Vite, React Router, Vitest |
| AI | pydantic-ai, DeepSeek compatible OpenAI API |
| TTS | DashScope CosyVoice, Edge TTS |
| 数据库 | SQLite by default, PostgreSQL optional |
| 音频 | ffmpeg, mutagen, imageio-ffmpeg |

## Project Structure

```text
podcast/
├── backend/                 # FastAPI API、CLI、数据库、生成流水线
│   ├── app/
│   │   ├── api/v1/          # 路由：podcasts、generation、likes、favorites 等
│   │   ├── cli/             # 命令行入口
│   │   ├── core/            # 配置加载
│   │   ├── db/              # 数据库初始化与迁移
│   │   ├── models/          # SQLAlchemy ORM 模型
│   │   ├── pipelines/       # RSS -> 策划 -> 剧本 -> TTS
│   │   ├── repositories/    # 数据访问层
│   │   ├── schemas/         # Pydantic 请求与响应模型
│   │   └── services/        # 业务逻辑
│   └── tests/               # 后端测试
├── frontend/                # Vite + React 管理界面
│   └── src/
│       ├── components/      # 播放器、脚本面板、时间线等组件
│       ├── context/         # User、Player、Favorites、Likes 状态
│       ├── pages/           # 列表、详情、生成、订阅、模型、设置等页面
│       ├── router/          # 前端路由
│       ├── services/        # API 客户端
│       └── types/           # TypeScript 类型
├── assets/audio/            # 开场、转场、结尾音乐素材
├── config/                  # RSS 源和主题配置
├── docs/                    # 演示、部署、API 文档
├── output/                  # 生成产物：脚本、音频、中间 JSON
├── prompt.txt               # 播客剧本生成 Prompt
└── README.md
```

## Requirements

运行前请确认本机已有：

| 依赖 | 版本建议 | 用途 |
| --- | --- | --- |
| Python | 3.11+ | 后端 API、CLI、流水线 |
| Node.js | 18+ | 前端开发与构建 |
| npm | 9+ | 前端依赖管理 |
| ffmpeg | 最新稳定版 | 音频拼接与混音 |

后端必须使用 `backend/.venv` 中的 Python。全局 Python 环境通常缺少 `pydantic_ai`、`dashscope` 等依赖。

## Quick Start

### 1. Clone

```bash
cd /home/default/Projects
git clone <repo-url> podcast
cd podcast
```

如果已经在本仓库中，直接进入项目目录即可：

```bash
cd /home/default/Projects/podcast
```

### 2. Backend

```bash
cd /home/default/Projects/podcast/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --reload
```

启动后可访问：

| 地址 | 说明 |
| --- | --- |
| `http://localhost:8000/health` | 健康检查 |
| `http://localhost:8000/docs` | Swagger / OpenAPI 文档 |

### 3. Frontend

```bash
cd /home/default/Projects/podcast/frontend
npm install
npm run dev
```

前端默认地址：`http://localhost:5173`

## Configuration

后端配置由 `backend/app/core/config.py` 管理，默认读取 `backend/.env`。可以参考根目录的 `.env.example` 创建配置：

```bash
cd /home/default/Projects/podcast
cp .env.example backend/.env
```

常用配置项：

| 变量 | 说明 |
| --- | --- |
| `APP_NAME` | 应用名称 |
| `APP_ENV` | 运行环境，例如 `dev` |
| `API_PREFIX` | API 前缀，默认 `/api/v1` |
| `CORS_ORIGINS` | 允许访问后端的前端地址 |
| `DATABASE_URL` | 数据库地址，开发默认 `sqlite:///./podcast.db` |
| `POSTGRES_URL` | 可选 PostgreSQL 地址 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | DeepSeek API Base URL |
| `SCRIPT_LLM_MODEL` | 剧本生成模型 |
| `TTS_PROVIDER` | TTS 服务，支持 `dashscope` 或 `edge` |
| `TTS_MODEL` | TTS 模型 |
| `DASHSCOPE_API_KEY` | DashScope API Key |

重要路径说明：

| 路径 | 说明 |
| --- | --- |
| `config/feed.json` | RSS 源配置 |
| `config/topics.json` | 主题配置 |
| `prompt.txt` | AI 剧本生成 Prompt |
| `output/` | 生成文件输出目录 |
| `assets/audio/opening/` | 开场音乐 |
| `assets/audio/transition/` | 转场音乐 |
| `assets/audio/closing/` | 结尾音乐 |

## CLI Usage

所有后端 CLI 命令建议从 `backend/` 目录运行：

```bash
cd /home/default/Projects/podcast/backend
.venv/bin/python -m app.cli --help
```

常用命令：

```bash
# 抓取 RSS
.venv/bin/python -m app.cli fetch-rss

# 只生成文本脚本
.venv/bin/python -m app.cli generate-text --topic daily-news

# 根据脚本合成语音
.venv/bin/python -m app.cli synthesize-tts --json-path output/podcast_script.json --output-dir output

# 运行完整流水线
.venv/bin/python -m app.cli run-pipeline --topic daily-news
```

常见输出文件：

| 文件 | 说明 |
| --- | --- |
| `output/rss_data.json` | RSS 抓取结果 |
| `output/episode_plan.json` | 节目策划结果 |
| `output/podcast_script.json` | 结构化脚本 |
| `output/podcast_script.txt` | 可读文本脚本 |
| `output/audio/podcast_full.mp3` | 合成后的完整音频 |

## API Overview

后端 API 前缀默认为 `/api/v1`。

| 模块 | 端点示例 |
| --- | --- |
| 健康检查 | `GET /health` |
| 播客 | `GET /api/v1/podcasts`, `GET /api/v1/podcasts/{podcast_id}` |
| 脚本 | `GET /api/v1/podcasts/{podcast_id}/script` |
| 用户 | `GET /api/v1/users` |
| 交互 | `GET /api/v1/interactions` |
| 推荐 | `GET /api/v1/recommendations/{user_id}` |
| 收藏 | `GET /api/v1/favorites?user_id=...`, `POST /api/v1/favorites` |
| 点赞 | `GET /api/v1/likes?user_id=...`, `POST /api/v1/likes` |
| 生成任务 | `POST /api/v1/generation/trigger`, `GET /api/v1/generation/{task_id}` |
| 日志流 | `GET /api/v1/generation/{task_id}/stream` |
| Provider | `GET /api/v1/generation/provider-health` |

触发生成任务的请求示例：

```json
{
  "rss_source": "default",
  "topic": "daily-news",
  "user_id": 1,
  "use_subscriptions": false,
  "custom_rss": []
}
```

## Frontend Routes

| 路由 | 页面 |
| --- | --- |
| `/` | 播客列表 |
| `/podcasts/:id` | 播客详情和脚本 |
| `/generate` | 生成任务 |
| `/subscriptions` | RSS / 订阅管理 |
| `/models` | 模型和 TTS Provider 状态 |
| `/settings` | 用户偏好设置 |
| `/likes` | 点赞列表 |
| `/favorites` | 收藏列表 |

前端 API 客户端位于 `frontend/src/services/api.ts`。默认 API 地址为 `http://localhost:8000/api/v1`，可通过 `VITE_API_BASE_URL` 覆盖。

## Testing

### Backend

后端测试必须在 `backend/` 目录运行，因为 `pytest.ini` 固定了测试路径和 `pythonpath`。

```bash
cd /home/default/Projects/podcast/backend
.venv/bin/pytest
```

常用单项测试：

```bash
.venv/bin/pytest tests/test_health.py -v
.venv/bin/pytest tests/test_generation_routes.py -v
.venv/bin/pytest tests/test_podcast_routes.py -v
.venv/bin/pytest tests/test_recommendation_routes.py -v
.venv/bin/pytest tests/test_tts_provider.py -v
```

### Frontend

```bash
cd /home/default/Projects/podcast/frontend
npm run lint
npm run build
npm test
```

`npm run build` 会先执行 TypeScript 检查，再执行 Vite 构建。

## Development Notes

| 注意点 | 原因 |
| --- | --- |
| 后端命令从 `backend/` 运行 | 默认 SQLite 文件会落在当前工作目录下 |
| 不要把 `output/` 当成源码事实依据 | 它主要保存生成产物和中间结果 |
| 修改生成日志格式要同步看前端 | `GeneratePage` 会根据 SSE 日志重建进度 |
| TTS 合成传入 `output/` 而不是 `output/audio/` | `TTSService` 会自己创建 `audio/` 子目录 |
| 音频合并需要 `ffmpeg` | 缺少时最终 MP3 合成会失败 |

## Open Source

| 文档 | 说明 |
| --- | --- |
| `LICENSE` | Apache-2.0 开源协议 |
| `CONTRIBUTING.md` | 贡献说明 |
| `SECURITY.md` | 安全问题报告方式 |

提交问题前建议先查看已有 issue，避免重复反馈。
