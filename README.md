# 智学伴

智学伴是一个基于 FastAPI、LangGraph 和大模型API的个性化学习课程项目。系统通过 ReAct Agent 调用知识点抽取、练习生成、用户画像和记忆工具，并使用腾讯云 MySQL、Redis及本地Chroma保存学习数据。

## 开发环境

- Python 3.11
- Node.js 20或更高版本
- 腾讯云 MySQL 8
- 腾讯云 Redis 7
- 本地 Chroma

## 目录

```text
backend/
├─ api/          请求校验与路由
├─ services/     确定性业务规则
├─ dao/          数据库访问
├─ model/        SQLAlchemy模型
├─ schemas/      请求与响应模型
├─ agents/       Agent、工具、Skill和记忆
├─ core/         异常、安全与公共能力
└─ tests/        自动化测试
frontend/        Vue前端
database/        共享MySQL升级脚本
设计图/          业务文档与静态原型
```

## 后端启动

项目配置由组长统一提供。将拿到的配置文件保存为 `backend/.env`，不要提交其中的数据库密码、Redis密码和模型密钥。

```powershell
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:PYTHONPATH='.'
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

接口文档：<http://127.0.0.1:8000/api>

依赖检查：<http://127.0.0.1:8000/health>

`/health`中的状态含义：

- `ok`：依赖正常；
- `degraded`：MySQL或Redis不可用；
- `not_initialized`：本地Chroma目录尚未初始化；
- `missing`：本地大模型配置不完整。

## 前端启动

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问 <http://127.0.0.1:5173>。

## 运行测试

在项目根目录执行：

```powershell
$env:PYTHONPATH='.'
backend\.venv\Scripts\python.exe -m pytest backend\tests -q -p no:cacheprovider
```

每个业务任务应同时提交对应测试，至少覆盖成功、参数错误和越权三种情况。

## 数据库升级

程序启动时的 `Base.metadata.create_all()`只创建不存在的表，不会清空数据，也不会修改已有表。

后续结构变更使用 `database/` 中的编号SQL脚本。详细规则见 [database/README.md](database/README.md)。

核心要求：

1. 不修改已经执行的SQL文件；
2. 每次变更新建递增编号；
3. 由指定数据库负责人执行；
4. 执行成功后写入`schema_version`；
5. 禁止直接删除共享数据库和业务数据。

## 代码分层规则

```text
API → Service → DAO → Model
          ↑
      Agent Tool
```

- API负责请求校验和返回响应；
- Service负责积分、掌握度、VIP等确定性规则和事务；
- DAO负责数据库读写；
- Model只定义数据库结构；
- Agent Tool负责理解和调度，通过Service执行业务，不直接堆积SQL和计费规则。

新增业务API统一返回：

```json
{
  "code": "OK",
  "message": "success",
  "data": {}
}
```

业务失败使用 `backend.core.exceptions.BusinessError`，不要在不同接口中自行设计错误格式。

## Agent约定

- 当前有效入口是 `backend/agents/agent/react_agent.py`；
- 使用模型原生Tool Calling；
- 用户身份只能从Token注入，不能信任前端或模型提供的用户ID；
- 工具返回统一的 `success/code/message/data/tool` JSON；
- Redis保存短期会话，MySQL保存结构化画像，Chroma保存本地长期语义记忆；
- 权限、积分、VIP、使用次数等确定性规则必须由Service完成。

## Git协作建议

- `main`：稳定演示版本；
- `develop`：小组联调版本；
- `feature/<name>`：个人功能分支。

不要直接在腾讯云服务器修改代码或手工修改共享表结构。合并前先运行相关测试，并确认SQL升级脚本已交给数据库负责人。
