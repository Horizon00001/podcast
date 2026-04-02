# 部署与运行说明（草案）

## 本地开发

### 后端
1. 进入 `backend/`
2. 使用清华源安装依赖：
   - `pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt`
3. 启动服务：
   - `uvicorn app.main:app --reload`

### 前端
1. 进入 `frontend/`
2. 安装依赖：
   - `npm install`
3. 启动开发服务器：
   - `npm run dev`

## Docker（占位）

后续补充：
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`

当前阶段先保证本地双端可运行联调。
