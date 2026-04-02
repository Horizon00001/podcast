# API 契约草案（v0）

## 1. 通用约定

- Base URL：`/api/v1`
- 数据格式：`application/json`
- 成功响应：HTTP 2xx + JSON
- 错误响应：HTTP 4xx/5xx + `{ "detail": "..." }`

## 2. 核心接口

### 2.1 播客列表
- `GET /podcasts`
- 响应：`Podcast[]`

### 2.2 播客详情
- `GET /podcasts/{podcast_id}`
- 响应：`Podcast`

### 2.3 行为上报
- `POST /interactions`
- 请求：
  - `user_id: number`
  - `podcast_id: number`
  - `action: "play" | "like" | "favorite" | "skip"`
- 响应：`Interaction`

### 2.4 推荐列表
- `GET /recommendations/{user_id}`
- 响应：
  - `user_id: number`
  - `strategy: string`
  - `items: RecommendationItem[]`

### 2.5 手动触发生成
- `POST /generation/trigger`
- 请求：
  - `rss_source: string`
  - `topic: string`
- 响应：
  - `task_id: string`
  - `status: string`
  - `message: string`
