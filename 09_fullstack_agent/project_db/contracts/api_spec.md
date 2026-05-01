# Todo 应用 API 契约文档

---

## 1. 基础信息

| 项目 | 值 |
|------|-----|
| 协议 | HTTP/1.1 REST |
| 内容类型 | `application/json` |
| 字符编码 | UTF-8 |
| 后端地址 | `http://localhost:8000` |
| 前端地址 | `http://localhost:5173`（Vite 开发服务器） |
| API 前缀 | `/api` |

---

## 2. 通用约定

### 2.1 错误响应格式

当发生错误时，后端统一返回：

```json
{
  "detail": "错误描述信息"
}
```

HTTP 状态码：
- `400` — 请求参数校验失败
- `404` — 资源不存在
- `422` — Pydantic 校验失败（FastAPI 自动处理）
- `500` — 服务器内部错误

### 2.2 CORS 配置

后端允许 `http://localhost:5173` 的跨域请求，允许的方法：`GET, POST, PUT, DELETE, OPTIONS`，允许的头部：`*`。

---

## 3. Pydantic 模型定义

### 3.1 TodoBase（创建/更新的基础字段）

```python
from pydantic import BaseModel, Field
from typing import Optional

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Todo 标题")
    description: Optional[str] = Field(None, max_length=1000, description="详细描述")
    completed: bool = Field(False, description="是否完成")
```

### 3.2 TodoCreate（创建请求体）

```python
class TodoCreate(TodoBase):
    pass
```

### 3.3 TodoUpdate（更新请求体，所有字段可选）

```python
class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    completed: Optional[bool] = None
```

### 3.4 TodoResponse（响应体）

```python
from datetime import datetime

class TodoResponse(TodoBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

### 3.5 TodoListResponse（列表响应）

```python
class TodoListResponse(BaseModel):
    total: int
    todos: list[TodoResponse]
```

---

## 4. API 接口定义

---

### 4.1 获取所有 Todo

| 属性 | 值 |
|------|-----|
| **Method** | `GET` |
| **Path** | `/api/todos` |
| **Query Parameters** | `completed` (bool, 可选) — 按完成状态过滤；`search` (str, 可选) — 按标题模糊搜索 |
| **Request Body** | 无 |

**Response `200 OK`：**

```json
{
  "total": 2,
  "todos": [
    {
      "id": 1,
      "title": "学习 FastAPI",
      "description": "阅读官方文档并完成练习",
      "completed": false,
      "created_at": "2025-01-15T10:00:00",
      "updated_at": "2025-01-15T10:00:00"
    },
    {
      "id": 2,
      "title": "学习 Vue3",
      "description": "搭建前端项目",
      "completed": true,
      "created_at": "2025-01-15T09:00:00",
      "updated_at": "2025-01-15T12:00:00"
    }
  ]
}
```

**前端调用示例：**

```js
// 获取全部
const res = await fetch('http://localhost:8000/api/todos');
const data = await res.json();

// 按条件过滤
const res = await fetch('http://localhost:8000/api/todos?completed=false&search=FastAPI');
const data = await res.json();
```

---

### 4.2 获取单个 Todo

| 属性 | 值 |
|------|-----|
| **Method** | `GET` |
| **Path** | `/api/todos/{todo_id}` |
| **Path Parameters** | `todo_id` (int) — Todo 的 ID |
| **Request Body** | 无 |

**Response `200 OK`：**

```json
{
  "id": 1,
  "title": "学习 FastAPI",
  "description": "阅读官方文档并完成练习",
  "completed": false,
  "created_at": "2025-01-15T10:00:00",
  "updated_at": "2025-01-15T10:00:00"
}
```

**Response `404 Not Found`：**

```json
{
  "detail": "Todo not found"
}
```

**前端调用示例：**

```js
const res = await fetch('http://localhost:8000/api/todos/1');
if (!res.ok) {
  const err = await res.json();
  console.error(err.detail);
  return;
}
const todo = await res.json();
```

---

### 4.3 创建 Todo

| 属性 | 值 |
|------|-----|
| **Method** | `POST` |
| **Path** | `/api/todos` |
| **Request Body** | `TodoCreate` |

**Request Body 示例：**

```json
{
  "title": "学习 FastAPI",
  "description": "阅读官方文档并完成练习",
  "completed": false
}
```

**Response `201 Created`：**

```json
{
  "id": 3,
  "title": "学习 FastAPI",
  "description": "阅读官方文档并完成练习",
  "completed": false,
  "created_at": "2025-01-15T14:30:00",
  "updated_at": "2025-01-15T14:30:00"
}
```

**Response `422 Unprocessable Entity`（title 为空时）：**

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "String should have at least 1 character",
      "input": ""
    }
  ]
}
```

**前端调用示例：**

```js
const res = await fetch('http://localhost:8000/api/todos', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: '新任务',
    description: '任务描述',
    completed: false
  })
});
const created = await res.json();
```

---

### 4.4 更新 Todo（全量更新）

| 属性 | 值 |
|------|-----|
| **Method** | `PUT` |
| **Path** | `/api/todos/{todo_id}` |
| **Path Parameters** | `todo_id` (int) — Todo 的 ID |
| **Request Body** | `TodoUpdate`（所有字段可选，仅传需要更新的字段） |

**Request Body 示例（只更新 title 和 completed）：**

```json
{
  "title": "学习 FastAPI 进阶",
  "completed": true
}
```

**Response `200 OK`：**

```json
{
  "id": 1,
  "title": "学习 FastAPI 进阶",
  "description": "阅读官方文档并完成练习",
  "completed": true,
  "created_at": "2025-01-15T10:00:00",
  "updated_at": "2025-01-15T15:00:00"
}
```

**前端调用示例：**

```js
const res = await fetch('http://localhost:8000/api/todos/1', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ completed: true })
});
const updated = await res.json();
```

---

### 4.5 删除 Todo

| 属性 | 值 |
|------|-----|
| **Method** | `DELETE` |
| **Path** | `/api/todos/{todo_id}` |
| **Path Parameters** | `todo_id` (int) — Todo 的 ID |
| **Request Body** | 无 |

**Response `204 No Content`：**

（无响应体）

**前端调用示例：**

```js
const res = await fetch('http://localhost:8000/api/todos/1', {
  method: 'DELETE'
});
if (res.status === 204) {
  console.log('删除成功');
}
```

---

## 5. 接口汇总表

| # | Method | Path | 描述 | 请求体 | 响应 |
|---|--------|------|------|--------|------|
| 1 | `GET` | `/api/todos` | 获取全部 Todo（支持过滤） | — | `TodoListResponse` |
| 2 | `GET` | `/api/todos/{todo_id}` | 获取单个 Todo | — | `TodoResponse` |
| 3 | `POST` | `/api/todos` | 创建 Todo | `TodoCreate` | `TodoResponse` (201) |
| 4 | `PUT` | `/api/todos/{todo_id}` | 更新 Todo | `TodoUpdate` | `TodoResponse` |
| 5 | `DELETE` | `/api/todos/{todo_id}` | 删除 Todo | — | 204 No Content |

---

## 6. 前端 API 封装建议

前端应将所有请求封装在 `src/api/todos.js` 模块中，统一管理 API 基础地址和错误处理：

```js
const BASE_URL = 'http://localhost:8000/api';

export async function fetchTodos(params = {}) { ... }
export async function fetchTodo(id) { ... }
export async function createTodo(data) { ... }
export async function updateTodo(id, data) { ... }
export async function deleteTodo(id) { ... }
```

各 Vue 组件通过导入该模块调用 API，不直接在组件中写 fetch。
