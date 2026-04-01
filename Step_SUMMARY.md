# RAG Knowledge Platform — 開發進度總覽

---

# STEP 1 — 資料庫 ORM 設計與 Migration 完成摘要

## 完成項目

### 1. `db/base.py` — SQLAlchemy 基礎層
- `Base`：使用 SQLAlchemy 2.0 `DeclarativeBase` 新式寫法
- `TimestampMixin`：提供 `created_at` / `updated_at`，自動填入 UTC 時間
- `UUIDMixin`：提供 `id: Mapped[UUID]` 作為所有 table 的 Primary Key

### 2. `db/session.py` — Async Session Factory
- 使用 `create_async_engine` + `async_sessionmaker`
- 提供 `get_async_session` async generator 供 FastAPI 依賴注入使用

### 3. ORM Models（4 個 table）

| 檔案 | Table | 重點欄位 |
|------|-------|---------|
| `models/user.py` | `users` | email (unique), hashed_password, role (admin/user), is_active |
| `models/document.py` | `documents` | status (pending/processing/completed/failed), uploaded_by_id FK, rag_doc_id |
| `models/chat_session.py` | `chat_sessions` | user_id FK (CASCADE), query_mode, message_count, compact_summary |
| `models/message.py` | `messages` | session_id FK (CASCADE), role (user/assistant/system), token_count, is_compacted_summary |

- 所有 Model 繼承 `UUIDMixin` + `TimestampMixin` + `Base`
- Relationships 使用 TYPE_CHECKING 避免循環 import
- `messages` table 建立複合 Index `(session_id, created_at)` 加速排序查詢

### 4. Repositories（5 個類別）

| 檔案 | 類別 | 額外方法 |
|------|------|---------|
| `repositories/base.py` | `BaseRepository[T]` | `get_by_id`, `get_all`, `create`, `update`, `delete`, `count` |
| `repositories/user_repository.py` | `UserRepository` | `get_by_email`, `get_active_users`, `deactivate` |
| `repositories/document_repository.py` | `DocumentRepository` | `get_by_uploader`, `get_by_status`, `update_status`, `get_by_rag_doc_id` |
| `repositories/session_repository.py` | `SessionRepository` | `get_by_user`, `update_title`, `update_last_message`, `increment_message_count`, `update_compact_data` |
| `repositories/message_repository.py` | `MessageRepository` | `get_by_session`, `get_recent_by_session`, `get_session_token_total`, `delete_by_session`, `bulk_create` |

### 5. Alembic Migration 設定
- `alembic.ini`：設定 async SQLite driver (`aiosqlite`)
- `app/db/migrations/env.py`：async migration runner，import 所有 models 供 autogenerate 偵測
- `app/db/migrations/script.py.mako`：migration 檔案模板
- 執行 `alembic revision --autogenerate -m "init_all_tables"` 產生 migration 檔案
- 執行 `alembic upgrade head` 成功建立資料庫

## 驗證結果
- SQLite DB (`data/rag_platform.db`) 成功建立 5 個 table：`alembic_version`, `chat_sessions`, `documents`, `messages`, `users`
- 所有 Foreign Key 與 Index 正確建立

---

# STEP 2 — 會員認證系統 (Auth) 完成摘要

## 完成項目

### 1. `core/exceptions.py` — 自訂例外體系
- `AppBaseException`：所有應用例外的基底類別
- 子例外：`AuthenticationError` (401)、`AuthorizationError` (403)、`NotFoundError` (404)、`ConflictError` (409)、`AppValidationError` (422)、`RAGProcessingError` (500)

### 2. `core/security.py` — SecurityService
- `hash_password`：bcrypt 雜湊，rounds=12
- `verify_password`：bcrypt 驗證
- `create_access_token`：JWT 建立，payload 含 `sub`（user_id）、`role`、`exp`
- `decode_token`：JWT 解碼，失敗拋出 `AuthenticationError`

### 3. `schemas/auth.py` — Pydantic 請求/回應 Schema
- `UserCreateRequest`：email + 密碼強度驗證（min 8 chars、含字母、含數字）
- `UserLoginRequest`：email + password
- `TokenResponse`：access_token + token_type
- `UserPublicResponse`：不含 hashed_password 的安全回應
- `RoleUpdateRequest` / `StatusUpdateRequest`：Admin 管理用

### 4. `services/auth_service.py` — AuthService
- `register`：檢查 email 重複 → hash password → 建立 user
- `authenticate`：查詢 user → 驗證密碼 → 驗證 is_active → 發 JWT
- `get_user_by_id`：查詢用戶，不存在拋 `NotFoundError`

### 5. `api/deps.py` — FastAPI 依賴注入
- `get_db`：yield async session（覆寫 `get_async_session` 供測試使用）
- `get_current_user`：解析 Bearer token → 查詢 user → 驗證 is_active
- `get_current_admin`：驗證 role == admin，否則拋 `AuthorizationError`

### 6. `api/v1/auth.py` — Auth Router
| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/v1/auth/signup` | POST | 註冊新用戶 → 201 |
| `/api/v1/auth/login` | POST | 登入取得 JWT → 200 |
| `/api/v1/auth/logout` | POST | 登出（client 丟棄 token）→ 200 |
| `/api/v1/auth/me` | GET | 取得當前用戶資料（需 JWT）|

### 7. `api/v1/admin.py` — Admin Router（Admin only）
| 端點 | 方法 | 說明 |
|------|------|------|
| `/api/v1/admin/users` | GET | 列出所有用戶 |
| `/api/v1/admin/users/{id}/role` | PATCH | 修改用戶角色 |
| `/api/v1/admin/users/{id}/status` | PATCH | 啟用/停用帳號 |

### 8. `app/main.py` — FastAPI 應用主程式
- CORS middleware（允許 `http://localhost:3000`）
- 全域 exception handler：所有 `AppBaseException` 統一回傳 `{"detail": "..."}` JSON
- lifespan hook（預留 RAGEngine 初始化位置）
- `/` 根路徑與 `/health` 健康檢查端點

### 9. `tests/test_auth.py` — 測試（12 個全數通過 ✅）
- signup 成功 / email 重複 409 / 密碼太短 422 / 密碼無數字 422
- login 成功 / 密碼錯誤 401 / 帳號不存在 401
- `/me` 正常取得 / 無 token 401 / 無效 token 401
- admin route 對一般用戶回 403
- logout 回 200

## 修正與問題紀錄

### 問題 1：`email-validator` 套件缺失
- **症狀**：`ImportError: email-validator is not installed`
- **原因**：`pydantic` 的 `EmailStr` 需要額外套件，原始 `pyproject.toml` 未包含
- **修正**：`uv add "pydantic[email]"`

### 問題 2：bcrypt 5.x 與 passlib 不相容
- **症狀**：`ValueError: password cannot be longer than 72 bytes` + bcrypt `__about__` AttributeError
- **原因**：passlib 1.7.x 尚未支援 bcrypt 5.x API 變更
- **修正**：`uv add "bcrypt<5"` 降版至 4.3.0

### 問題 3：測試時跨請求資料不可見（signup 後 login 回 401）
- **症狀**：signup 成功（201）但 login 失敗（401），duplicate email 測試也失敗（第二次 signup 竟然回 201）
- **原因**：`get_async_session` 只有 `flush()` 而沒有 `commit()`，每次請求結束資料被 rollback；測試 override 的是 `get_async_session` 但 `deps.py` 直接 import，FastAPI DI 無法攔截
- **修正**：
  1. `db/session.py` 的 `get_async_session` 加入 `commit()` / `rollback()` 機制
  2. `tests/conftest.py` 改成 override `get_db`（deps.py 中的函數）而非底層 `get_async_session`

### 問題 4：`ValidationError` 命名衝突
- **症狀**：FastAPI 的 `status.HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning
- **原因**：自訂的 `ValidationError` 與 Python 內建 / Pydantic 的同名類別衝突；status code 常數也已更名
- **修正**：重新命名為 `AppValidationError`，status code 改用 `HTTP_422_UNPROCESSABLE_CONTENT`

## 驗證結果
- 所有 12 個測試通過（`uv run pytest tests/test_auth.py -v`）
- FastAPI app 可正確 import，13 個 route 全部註冊成功

---

# STEP 3 — RAG-Anything 整合核心 完成摘要

## 完成項目

### 1. `rag/llm_adapter.py` — OllamaLLMAdapter + OllamaVisionAdapter

**OllamaLLMAdapter**
- `complete(prompt, system_prompt, history_messages, stream, **kwargs) -> str`：POST Ollama `/api/chat`
- `complete_stream(...) -> AsyncGenerator[str, None]`：串流模式逐 token yield
- `as_llm_func() -> Callable`：回傳符合 LightRAG `llm_model_func` 簽名的 callable（model 預先 bind）
- LightRAG 呼叫規範：`await llm_func(prompt, system_prompt=None, history_messages=[], stream=False, **kwargs)`

**OllamaVisionAdapter**（llava:7b，文件圖片 caption 專用，不用於即時對話）
- `vision_complete(...)` 三段式邏輯：
  1. `messages` 提供 → VLM Enhanced Query，直接送 llava
  2. `image_data` 提供 → 單張圖片 base64 分析
  3. fallback → 委派給 llm_adapter（gpt-oss:latest）純文字
- `as_vision_func() -> Callable`：回傳符合 RAGAnything `vision_model_func` 簽名的 callable

### 2. `rag/embedding_adapter.py` — BGEEmbeddingAdapter
- Lazy load BAAI/bge-m3（`threading.Lock` 保證 thread-safe）
- `embed(texts) -> list[list[float]]`：asyncio executor 執行 `model.encode()`，batch_size=32
- `to_embedding_func() -> EmbeddingFunc`：回傳 LightRAG `EmbeddingFunc(embedding_dim=1024, max_token_size=8192)`

### 3. `rag/chroma_adapter.py` — ChromaVectorDBStorage
- 繼承 `lightrag.base.BaseVectorStorage`，完整實作所有抽象方法
- 實作方法：`initialize`, `upsert`, `query`, `get_by_id`, `get_by_ids`, `get_vectors_by_ids`, `delete`, `delete_entity`, `delete_entity_relation`, `drop`, `index_done_callback`
- ChromaDB collection 命名：`{workspace}_{namespace}_{model}_{dim}d`
- 透過 `RAGEngine._register_chroma_storage()` monkey-patch 注入 `lightrag.kg.STORAGES["ChromaVectorDBStorage"]`

### 4. `rag/engine.py` — RAGEngine singleton
- 啟動順序：注冊 ChromaStorage → OllamaLLMAdapter → OllamaVisionAdapter → BGEEmbeddingAdapter → RAGAnythingConfig → RAGAnything
- `RAGAnythingConfig(parser="mineru", enable_image_processing=True, enable_table_processing=True, enable_equation_processing=True)`
- `lightrag_kwargs` 傳入 `vector_storage="ChromaVectorDBStorage"` + chroma connection params
- `get_rag()`, `get_llm_adapter()`, `shutdown()` class methods

### 5. `app/main.py` — lifespan 整合
- `lifespan` 加入 `await RAGEngine.initialize(settings)` / `await RAGEngine.shutdown()`

### 6. `tests/test_rag_adapters.py` — 16 個測試全部通過
- OllamaLLMAdapter (4)：complete 回傳、system_prompt 注入、history 注入、as_llm_func
- OllamaVisionAdapter (4)：messages 模式、image_data 模式、fallback 模式、as_vision_func
- BGEEmbeddingAdapter (2)：embed 向量維度、batch 處理 70 筆
- ChromaVectorDBStorage (5)：initialize、upsert、query 結果轉換、delete、drop
- `test_bge_embedding_func_metadata` (1)：EmbeddingFunc metadata 驗證

## 技術決策紀錄

### 決策 1：ChromaVectorDBStorage 實作方式
- **問題**：當前版本 lightrag `kg/` 目錄缺少 `chroma_impl.py`（只有 STORAGES dict 登錄但 impl 不存在）
- **方案**：自實作 `ChromaVectorDBStorage(BaseVectorStorage)` + monkey-patch `STORAGES["ChromaVectorDBStorage"]`
- **原因**：Option B（standalone）會讓整個 ChromaDB 整合變成空殼，影響後續所有 STEP 設計

### 決策 2：conversation_history（非 history_messages）
- **發現**：計畫書寫 `history_messages=...` 但 LightRAG `QueryParam` 實際欄位是 `conversation_history`
- **影響**：STEP 4 ConversationService 呼叫 `rag.aquery()` 時需用 `conversation_history=` 參數
- **action**：STEP 4 實作時按正確欄位名稱傳入

### 決策 3：MinerU 暫未安裝
- `RAGAnythingConfig(parser="mineru")` 已寫入設定
- STEP 3 只建介面層，不觸發 parser；MinerU 在 STEP 5 文件上傳時才需要

## 注意事項（測試 mock 相關）
- `tests/test_rag_adapters.py` 所有測試使用 mock（Ollama、ChromaDB、SentenceTransformer 均未真實呼叫）
- TODO（Docker 階段）：替換為真實服務整合測試後刪除 mock

## 驗證結果
- 16 個 RAG adapter 測試通過（`uv run pytest tests/test_rag_adapters.py -v`）
- 12 個 auth 測試繼續通過（共 28 個測試全數通過）
