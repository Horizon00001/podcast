# 团队模块分工建议（基于 WBS）

## 后端组（1.x）
- `backend/app/api/v1/`：接口路由
- `backend/app/services/`：业务逻辑
- `backend/app/repositories/`：数据访问层
- `backend/app/models/`、`backend/app/db/`：模型与数据库配置

## 资讯与脚本组（2.x）
- 后端 CLI `backend/app/cli`
- `config/feed.json`：RSS 源管理
- `common/examples/`：脚本格式样例维护

## 音频组（3.x）
- 后端 CLI `backend/app/cli`
- `output/audio/`：音频产物目录

## 推荐组（4.x）
- `backend/app/api/v1/recommendations.py`
- `backend/app/services/recommendation_service.py`
- 后续训练代码建议放在 `backend/app/recommendation/`

## 前端组（5.x）
- `frontend/src/pages/`：页面
- `frontend/src/components/`：组件
- `frontend/src/services/`：接口调用
- `frontend/src/types/`：类型契约

## 测试与文档组（6.x）
- `backend/tests/`：后端测试
- `docs/`：技术文档与部署文档
- 根目录 `README.md`：总入口文档
