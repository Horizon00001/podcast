# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## 项目概述

AI 播客生成系统：抓取 RSS -> 分类聚类 -> 生成剧本 -> TTS 合成音频。

- **Backend**: FastAPI + SQLAlchemy + Pydantic v2，API 前缀 `/api/v1`
- **Frontend**: React 19 + TypeScript + Vite + React Router
- **AI**: `pydantic-ai`，默认脚本模型 `openai:deepseek-chat`
- **TTS**: DashScope cosyvoice-v2 为主，Edge TTS 为备用
- **Database**: 开发默认 SQLite，可选 PostgreSQL；应用启动时自动建表并执行迁移

## 架构模式

Routes -> Services -> Repositories

```text
HTTP Request -> FastAPI Route -> Service -> Repository -> SQLAlchemy Session -> SQLite/PostgreSQL
```

- 路由层在 `backend/app/api/v1/`
- 业务层在 `backend/app/services/`
- 数据访问层在 `backend/app/repositories/`
- `app/db/session.py` 提供 `get_db()` 依赖注入

## 常用命令

```bash
# Backend - 必须使用 backend venv 中的 Python
cd /root/Projects/podcast/backend
.venv/bin/python -m uvicorn app.main:app --reload

# Backend tests
.venv/bin/pytest
.venv/bin/pytest tests/test_health.py -v
.venv/bin/pytest tests/test_generation_routes.py -v

# Frontend
cd /root/Projects/podcast/frontend
npm install
npm run dev
npm run lint
npm run build
npm test

# Standalone pipeline
cd /root/Projects/podcast/backend
.venv/bin/python -m app.cli run-pipeline --topic daily-news

# Focused pipeline steps
.venv/bin/python -m app.cli fetch-rss
.venv/bin/python -m app.cli generate-text --topic daily-news
.venv/bin/python -m app.cli synthesize-tts --json-path output/podcast_script.json --output-dir output
```

## 目录结构

```text
backend/
  app/
    api/v1/           FastAPI 路由（podcasts, users, interactions, recommendations, favorites, likes, generation）
    cli/              命令行入口（run-pipeline, fetch-rss, generate-text, synthesize-tts）
    core/             Settings 配置类
    db/               数据库初始化与迁移
    models/           SQLAlchemy ORM 模型
    pipelines/        RSS -> 分组策划 -> 剧本生成 -> TTS 合成
    repositories/     数据访问层
    schemas/          Pydantic 请求/响应模型
    services/         业务逻辑层
  tests/              后端 pytest 测试
frontend/
  src/
    components/       播放器、脚本面板、时间线等 UI 组件
    context/          User / Player / Favorites / Likes 状态管理
    pages/            列表、详情、生成、订阅、模型、设置、收藏、点赞页面
    router/           前端路由
    services/api.ts   API 客户端
    types/            TypeScript 类型定义
config/
  feed.json           RSS 源配置
  topics.json         话题配置
output/               生成产物（脚本、音频、rss_data 等）
prompt.txt            剧本生成 prompt
assets/audio/         开场、转场、结尾等音频素材
```

## 关键约定

### Python Runtime
- 必须使用 `backend/.venv/bin/python`
- 全局 Python 环境通常缺少 `pydantic_ai`、`dashscope` 等依赖
- backend 命令应从 `backend/` 目录执行

### 配置加载
- `backend/app/core/config.py` 会显式加载 `backend/.env`
- 默认配置包含：
  - `api_prefix=/api/v1`
  - `database_url=sqlite:///./podcast.db`
  - `tts_provider=dashscope`
  - `script_llm_model=openai:deepseek-chat`

### 数据库
- 默认 SQLite: `sqlite:///./podcast.db`
- 从 `backend/` 运行时数据库文件为 `backend/podcast.db`
- 应用启动时立即执行 `bootstrap_database()`
- `bootstrap_database()` 会调用：
  - `initialize_schema()`
  - `apply_migrations()`

### 静态文件
- `/audio` 映射到 `output/audio`
- `/audio/podcasts` 映射到 `output/podcasts`

### 配置文件
- `config/feed.json`：RSS 源配置
- `config/topics.json`：可选主题配置
- `prompt.txt`：AI 剧本生成 prompt
- `backend/.env`：运行环境变量

### 注意事项
- 历史文档里如果出现 `/root/Projects/podcast`，当前环境应改看 `/root/Projects/podcast`
- `frontend/README.md` 只保留前端快速参考，项目总览看根目录 README
- `output/` 下内容是生成产物，通常不作为源码事实依据

## 后端 API

`backend/app/api/v1/router.py` 当前挂载的路由组：

- `podcasts`
- `users`
- `interactions`
- `recommendations`
- `favorites`
- `likes`
- `generation`

额外顶层路由：

- `GET /health`

## 数据库模型

### User
- `id`: Integer, PK
- `username`: String(64), unique
- `email`: String(128), unique
- `preferences`: Text，可为空，JSON 字符串
- `created_at`: DateTime

### Podcast
- `id`: Integer, PK
- `title`: String(200)
- `summary`: Text
- `category`: String(64)
- `audio_url`: String(500)
- `script_path`: String(500)
- `published_at`: DateTime

### Interaction
- `id`: Integer, PK
- `user_id`: FK -> users.id
- `podcast_id`: FK -> podcasts.id
- `action`: `play | pause | resume | like | favorite | skip | complete | click`
- `listen_duration_ms`: Integer，可为空
- `progress_pct`: Float，可为空
- `session_id`: String(64)，可为空
- `context_hour`: Integer，可为空
- `context_weekday`: Integer，可为空
- `context_bucket`: String(32)，可为空
- `recommendation_request_id`: String(64)，可为空
- `created_at`: DateTime

### Favorite
- 收藏关系单独建模在 `backend/app/models/favorite.py`
- 前端通过 `/favorites` 路由读取和维护收藏

### Like
- 点赞关系单独建模在 `backend/app/models/like.py`
- 前端通过 `/likes` 路由读取和维护点赞

### GenerationTask
- `task_id`: String(64), PK
- `status`: `queued | running | succeeded | failed | cancelled`
- `message`: Text
- `rss_source`: String(128)
- `topic`: String(128)
- `logs`: Text，JSON 字符串数组
- `created_at`: DateTime
- `updated_at`: DateTime

## 前端架构

### Context Providers

**UserContext**
- 自动确保用户存在
- 支持按用户名查找或创建用户
- 管理用户偏好读取与更新

**PlayerContext**
- 管理全局音频播放状态
- 维护当前播客、进度、时长、播放速率等信息

**FavoritesContext**
- 管理收藏状态
- 与 `/favorites` API 同步

**LikesContext**
- 管理点赞状态
- 与 `/likes` API 同步

### 主要页面

- `PodcastListPage`：播客列表
- `PodcastDetailPage`：单个播客详情与脚本
- `GeneratePage`：生成任务发起、日志展示、恢复活跃任务
- `SubscriptionPage`：RSS/订阅相关页面
- `ModelsPage`：脚本/TTS provider 能力与健康状态
- `SettingsPage`：用户偏好设置
- `FavoritesPage`：收藏列表
- `LikesPage`：点赞列表

### 生成页重点

`frontend/src/pages/GeneratePage.tsx` 不只是一个提交表单：

- 会把活跃任务 ID 和页面进度状态持久化到 `sessionStorage`
- 会根据后端日志流重建 RSS、分组、section、TTS 合成进度
- 如果修改后端日志格式，需要同步检查这里的解析逻辑

### API 客户端

`frontend/src/services/api.ts` 中的关键点：

- `BASE_URL = VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'`
- `MEDIA_BASE_URL` 会主动去掉 `/api/v1`
- 请求默认 8 秒超时
- generation 相关接口除了状态查询，还包含：
  - `getGenerationCapabilities()`
  - `getTTSProviderCapabilities()`
  - `getProviderHealth()`
- 收藏相关接口：
  - `getFavorites(userId)`
  - `addFavorite(userId, podcastId)`
  - `removeFavorite(userId, podcastId)`
- 点赞相关接口：
  - `getLikes(userId)`
  - `addLike(userId, podcastId)`
  - `removeLike(userId, podcastId)`

## Generation API

当前 generation 路由除了基本任务接口，还包括 provider 能力与健康检查：

- `GET /generation/sources`
- `GET /generation/topics`
- `GET /generation/tts/providers`
- `GET /generation/capabilities`
- `GET /generation/provider-health`
- `POST /generation/trigger`
- `GET /generation/{task_id}`
- `GET /generation/{task_id}/stream`
- `DELETE /generation/{task_id}`

后台任务通过 `generation_service` 驱动，前端主要依赖状态轮询和 SSE 日志流感知进度。

## Pipeline 管道

4 步流水线位于 `backend/app/pipelines/podcast_pipeline.py`。

### Step 1: RSS Fetch
- 读取 `config/feed.json`
- 拉取启用的 RSS 源
- 输出 `output/rss_data.json`

### Step 2: Episode Planning
- 对 RSS 内容做分类与聚类
- 生成每组节目的 `episode_plan.json`
- 小组结果可进入 pending groups，等待后续合并

### Step 3: Script Generation
- 使用 `pydantic-ai` 生成结构化播客剧本
- 生成文本和 JSON 结果
- 支持 section 级别回调，便于流式推进 TTS

### Step 4: TTS Synthesis
- 分段合成音频
- 最后借助 `ffmpeg` 合并为完整节目

## TTS 抽象

`backend/app/services/speech_provider.py` 定义了 provider 抽象。

- `DashScopeTTSProvider`：主力 provider
- `EdgeTTSProvider`：备用 provider
- provider 选择依赖 `TTS_PROVIDER`

语音映射：

- `male` -> `loongdavid_v2`
- `female` 或未指定 -> `longanwen`

## 推荐系统

`RecommendationService` 是混合推荐，结合交互记录、内容相似度、热度、新鲜度和时段上下文。

已有实现重点包括：

- 冷启动策略
- warm-up 过渡策略
- 混合推荐主策略
- 时段画像
- skip 等负反馈处理

如果要改推荐行为，优先看：

- `backend/app/services/recommendation_service.py`
- `backend/app/services/recommendation/`

## 测试说明

### Backend
- `backend/pytest.ini` 固定了测试根路径，必须从 `backend/` 运行
- 常用：
  - `.venv/bin/pytest`
  - `.venv/bin/pytest tests/test_health.py -v`
  - `.venv/bin/pytest tests/test_generation_routes.py -v`
  - `.venv/bin/pytest tests/test_podcast_routes.py -v`
  - `.venv/bin/pytest tests/test_recommendation_routes.py -v`
  - `.venv/bin/pytest tests/test_tts_provider.py -v`
- `backend/tests/conftest.py` 使用内存 SQLite，不复用 `backend/podcast.db`

### Frontend
- 在 `frontend/` 下运行：
  - `npm run lint`
  - `npm run build`
  - `npm test`
- `npm run build` 会先执行 `tsc -b`

## 音频素材

`assets/audio/` 按用途分目录：

- `opening/`
- `transition/`
- `closing/`

优先从对应目录选文件；目录为空时回退到 `assets/audio/` 根目录候选。

当前混音参数：

- `opening_theme`: `volume=0.24`, `fade_out=1800ms`
- `transition_sting`: `volume=0.20`, `fade_out=350ms`
- `closing_tail`: `volume=0.20`, `fade_out=2600ms`
- 其他角色: `volume=0.22`, `fade_out=1300ms`
