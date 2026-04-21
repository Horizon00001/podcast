# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 播客生成系统：抓取 RSS → 分类聚类 → 生成剧本 → TTS 合成音频。

- **Backend**: FastAPI + SQLAlchemy + Pydantic v2，API 版本化部署于 `/api/v1`
- **Frontend**: React 19 + TypeScript + Vite + React Router 7
- **AI**: pydantic-ai + DeepSeek 生成剧本
- **TTS**: DashScope cosyvoice-v2（主要） + Edge TTS（备用），通过 `SpeechProvider` 协议抽象

## 架构模式

Routes → Services → Repositories（三层架构）

```
HTTP Request → FastAPI Route → Service → Repository → SQLAlchemy Session → SQLite/PostgreSQL
```

## 常用命令

```bash
# Backend - 必须使用 backend venv 中的 Python
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload          # 开发服务器
pytest                                  # 运行所有测试
pytest tests/test_health.py             # 单个测试文件

# Frontend
cd frontend
npm install                              # 安装依赖
npm run dev                              # 开发服务器 (localhost:5173)
npm run lint && npm run build           # 检查 + 构建

# Standalone 管道（无需 Web UI）
cd /home/default/Projects/podcast/backend && python -m app.cli run-pipeline
```

## 关键约定

### Python Runtime
- **必须使用**: `backend/.venv/bin/python`
- 系统 conda 和 pip 缺少 `pydantic_ai`、`dashscope` 等依赖
- venv 二进制: `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/uvicorn`

### 数据库
- SQLite 默认: `sqlite:///./podcast.db`（相对于 cwd）
- 从 `backend/` 运行时数据库在 `backend/podcast.db`
- 启动时调用 `init_db()` → `Base.metadata.create_all()` + `run_migrations()`

### 静态文件
- 音频文件: `/audio` 路径映射到 `output/audio/`（repo 根目录）

### 配置文件
- `config/feed.json` - RSS 源配置（前端通过 `/api/v1/generation/sources` 读取）
- `config/topics.json` - 话题定义
- `prompt.txt` - AI 生成规则（pydantic-ai 读取）
- `.env` - 环境变量（DashScope API key 等）

## 数据库模型

### SQLAlchemy Models

**User** (`backend/app/models/user.py`)
- `id`: Integer, PK
- `username`: String(64), unique
- `email`: String(128), unique
- `created_at`: DateTime

**Podcast** (`backend/app/models/podcast.py`)
- `id`: Integer, PK
- `title`: String(200)
- `summary`: Text
- `category`: String(64), default="general"
- `audio_url`: String(500)
- `script_path`: String(500)
- `published_at`: DateTime

**Interaction** (`backend/app/models/interaction.py`)
- `id`: Integer, PK
- `user_id`: FK → users.id
- `podcast_id`: FK → podcasts.id
- `action`: String(32) ("play", "like", "favorite", "skip")
- `created_at`: DateTime

## 前端架构

### Context Providers

**PlayerContext** (`frontend/src/context/PlayerContext.tsx`)
- 管理全局音频播放状态：`currentPodcast`, `isPlaying`, `progress`, `duration`, `currentTime`, `playbackRate`
- 使用 HTMLAudioElement + useRef 实现

**UserContext** (`frontend/src/context/UserContext.tsx`)
- 管理用户身份：自动 get-or-create 用户
- `ensureUser(username)` 模式

### 核心组件

**GlobalPlayer** (`frontend/src/components/GlobalPlayer.tsx`)
- 固定底部播放条（90px）
- 显示播客标题/摘要、播放控制、进度条、播放速率

**TimelineHighlighter** (`frontend/src/components/TimelineHighlighter.tsx`)
- 脚本时间线同步高亮
- 根据 `currentTime` 定位当前行并自动滚动
- 点击任意行跳转播放

### API 客户端 (`frontend/src/services/api.ts`)

Base URL: `VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'`

关键方法:
- `listPodcasts()`, `getPodcast(id)` - 播客 CRUD
- `getRecommendations(userId)` - 个性化推荐
- `reportInteraction(payload)` - 上报交互
- `ensureUser(username)` - get-or-create
- `getRSSSources()`, `getTopics()` - 生成配置
- `triggerGeneration(payload)` - 触发生成
- `getGenerationStatus(taskId)` - 轮询状态
- `createEventSource(taskId)` - SSE 实时日志

## Pipeline 管道

4 步流水线（当前由后端 CLI 调度）：

### Step 1: RSS Fetch (`python -m app.cli fetch-rss`)
- 读取 `config/feed.json`
- 抓取所有 `enabled: true` 的 RSS 源
- 输出 `output/rss_data.json`

### Step 2: Episode Planning
- 读取 `output/rss_data.json`
- **分类**：基于关键词分类（tech_ai, business, sports, general）
- **聚类**：TF-IDF + 余弦相似度 + 并查集（阈值 0.5）
- 按 anchor 正则分组
- 输出 per-group `episode_plan.json` 到 `output/podcasts/<category>/<slug>/`
- 不足 2 条的聚类存入 `pending_groups.json` 跨运行合并

### Step 3: Script Generation (`python -m app.cli generate-text`)
- 读取 `episode_plan.json` 和 `rss_data.json`
- 使用 `pydantic-ai` + `openai:deepseek-chat`
- 流式输出 `PodcastScript`（Pydantic 模型）
- 输出 `podcast_script.txt` 和 `podcast_script.json`

**PodcastScript 模型**:
```
PodcastScript
  ├── title: str
  ├── intro: str
  ├── sections: List[PodcastSection]
  └── total_duration: str

PodcastSection
  ├── section_type: "opening" | "transition" | "main_content" | "closing"
  ├── dialogues: List[DialogueTurn]  # 必须严格交替 A/B
  └── audio_effect: Optional[AudioEffect]

DialogueTurn
  ├── speaker: "A" | "B"
  ├── content: str
  └── emotion: Optional[str]
```

### Step 4: TTS Synthesis (`python -m app.cli synthesize-tts`)
- 读取 `podcast_script.json`
- 调用 `TTSService.synthesize_podcast()`
- 输出 `output/podcasts/<category>/<slug>/audio/podcast_full.mp3`

## TTS 抽象

`SpeechProvider` 协议（`backend/app/services/speech_provider.py`）:
```python
async def synthesize(text, output_path, voice, style) -> str: ...
```

- **DashScopeTTSProvider**: Alibaba cosyvoice-v2（主要）
- **EdgeTTSProvider**: Microsoft Edge TTS（备用）
- `TTS_PROVIDER` 环境变量切换

Voice 映射:
- `voice="male"` → `loongdavid_v2`
- `voice="female"` 或 unset → `longanwen`

## 推荐算法

`RecommendationService` 混合推荐：

```
final_score = 0.45*CF + 0.30*content + 0.20*hot + 0.05*fresh
```

- **CF**: 协同过滤
- **content**: TF-IDF 余弦相似度
- **hot**: 用户行为热度
- **fresh**: 时间衰减新鲜度

## 注意事项

- `AGENTS.md` 是开发者笔记的权威来源
- `frontend/README.md` 是 Vite 默认模板，非项目指导
- `output/` 下的生成文件已 git-ignored
- API keys 暴露需轮换
