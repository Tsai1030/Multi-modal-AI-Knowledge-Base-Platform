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

---

# STEP 4 — 多輪對話設計：Conversation 管理與 Compact 完成摘要

## 完成項目

### 1. `rag/conversation_compactor.py` — ConversationCompactor

- `COMPACT_PROMPT_TEMPLATE`：繁體中文摘要 prompt，以「對話摘要：」開頭
- `compact_threshold=15`：訊息數達此值觸發 Compact
- `compact_target=6`：Compact 後保留最近 N 條訊息
- `should_compact(message_count) -> bool`：`message_count >= compact_threshold`
- `compact(messages, keep_last_n) -> tuple[str, list[Message]]`：
  - 舊訊息格式化為純文字（用戶/助理/系統 role 標籤）
  - 呼叫 `llm_adapter.complete()` 生成摘要
  - 回傳 `(summary_text, messages[-keep_last_n:])`
  - 防守：`keep_last_n >= len(messages)` 時壓縮全部但保留全部
- `estimate_tokens(text) -> int`：`len(text) // 3`（中英文粗估）
- `_format_messages`：靜態方法，role 轉換為中文標籤

### 2. `services/conversation_service.py` — ConversationService

**Context 組裝流程（`get_conversation_context`）：**
```
[system] → [assistant(compact_summary)?] → [...history msgs] → [user(current_question)]
```

- `get_conversation_context(session_id, current_question) -> list[dict]`：
  1. 查詢 session（不存在拋 `NotFoundError`）
  2. 取最近 `compact_threshold` 條訊息
  3. 若 `should_compact(session.message_count)` → 執行 `_execute_compact`
  4. Compact 後改取 `compact_target + 1` 條（+1 為 summary marker 預留）
  5. 組裝 history，過濾 `is_compacted_summary=True` 的 DB marker
  6. 加入 `session.compact_summary` 作為 assistant message（若有）
- `save_user_message`：建立訊息 + `increment_message_count`
- `save_assistant_message`：建立訊息 + `update_last_message` + `increment_message_count`
- `_execute_compact`：
  1. 呼叫 `compactor.compact()` → LLM 摘要
  2. 刪除被壓縮的舊訊息（keep_ids 排除）
  3. 在 DB 插入 `role=system, is_compacted_summary=True` 的 marker
  4. 更新 `session.compact_summary` 與 `is_compacted=True`
- `auto_title_session`：若 `title.startswith("新對話")` → 取前 20 字更新標題

### 3. `services/chat_session_service.py` — ChatSessionService

| 方法 | 說明 |
|------|------|
| `create_session(user_id, query_mode="hybrid")` | 預設標題「新對話 {datetime}」 |
| `list_sessions(user_id, skip, limit)` | 委派 SessionRepository，按 last_message_at DESC |
| `get_session_with_messages(session_id, user_id, message_limit=50)` | 驗證 session.user_id == user_id，防跨用戶存取 |
| `rename_session(session_id, user_id, new_title)` | 驗證 ownership |
| `delete_session(session_id, user_id)` | CASCADE 自動刪除 messages |

所有方法：session 不存在拋 `NotFoundError`，非 owner 拋 `AuthorizationError`

### 4. `tests/test_conversation.py` — 23 個測試全數通過 ✅

| 類別 | 數量 | 測試重點 |
|------|------|---------|
| `TestConversationCompactor` | 6 | should_compact 閾值邊界、compact 分割與 LLM 呼叫、edge case、token 估算 |
| `TestConversationService` | 9 | context 組裝結構、compact summary 注入、DB marker 過濾、compact 觸發、長度上限、auto_title、訊息儲存 |
| `TestChatSessionService` | 8 | 建立 session 預設值、query_mode、分頁、ownership 驗證、NotFoundError |

## 關鍵設計決策

### 決策 1：`conversation_history=` 參數（STEP 4 確認）
- STEP 3 已標註：呼叫 `rag.aquery()` 時使用 `conversation_history=`（非 `history_messages=`）
- `get_conversation_context()` 回傳的 `list[dict]` 即為此參數的值
- **使用方式**：
  ```python
  context = await conversation_svc.get_conversation_context(session_id, question)
  result = await rag.aquery(question, param=QueryParam(conversation_history=context))
  ```

### 決策 2：Compact 後取 `compact_target + 1` 條訊息
- `_execute_compact` 在 DB 插入 summary marker（`is_compacted_summary=True`），此 marker 有新的 `created_at`，會出現在 `get_recent_by_session` 的最新結果中
- 若只取 `compact_target`，marker 佔一個位置，實際 history 只剩 `compact_target - 1` 條
- 解決：取 `compact_target + 1`，context assembly 過濾 marker，確保保留 `compact_target` 條真實對話

### 決策 3：Summary marker in DB vs session.compact_summary
- DB marker（`is_compacted_summary=True`）：用於審計與災難恢復
- `session.compact_summary`：context assembly 的實際資料來源
- 兩者並存，context assembly 透過 session 欄位取值，不依賴 DB marker

## 注意事項（測試 mock 相關）
- 所有測試使用 mock（無真實 DB / LLM 呼叫）
- TODO（Docker 階段）：替換為真實服務整合測試後刪除 mock

## 驗證結果
- 23 個 Conversation 測試通過（`uv run pytest tests/test_conversation.py -v`）
- 51 個測試全數通過（23 conversation + 16 RAG adapter + 12 auth）

---

# STEP 5 — 文件上傳與 RAG 處理 API 完成摘要

## 完成項目

### 1. `schemas/document.py` — 三個 Pydantic 回應 Schema

| Schema | 欄位 | 用途 |
|--------|------|------|
| `DocumentUploadResponse` | id, title, status, created_at | POST /upload 202 回應 |
| `DocumentListResponse` | id, title, original_filename, file_size, mime_type, status, error_message, uploaded_by_id, created_at, updated_at | GET / 與 GET /{id} |
| `DocumentStatusResponse` | id, status, error_message | GET /{id}/status |

### 2. `services/document_service.py` — DocumentService

| 方法 | 說明 |
|------|------|
| `validate_file(file)` | 驗證副檔名（11 種允許）與大小（上限 50 MB） |
| `save_file(file)` | 儲存至 `upload_dir/{uuid}{ext}`，回傳 (stored_filename, file_path, file_size) |
| `create_document_record(...)` | 建立 Document 記錄，status=pending，title 取自原始檔名 stem |
| `process_document_background(doc_id)` | BackgroundTask：建立獨立 DB session，更新狀態 processing → completed/failed，儲存 rag_doc_id |
| `list_documents(user, skip, limit)` | Admin 看全部；一般用戶看自己上傳的 |
| `get_document(doc_id, user)` | NotFoundError / AuthorizationError 對應 404 / 403 |
| `delete_document(doc_id, user)` | 依序：刪向量（adelete_by_doc_id）→ 刪檔案 → 刪 DB 記錄 |

**關鍵實作細節**：
- `AsyncSessionFactory` 必須在模組頂層 import（非函式內），才能被 `patch()` 正確替換
- `process_document_complete(file_path, output_dir, doc_id=...)` 回傳 None；UUID 由 service 自行生成後存入 `rag_doc_id`
- 刪向量透過 `self._rag.lightrag.adelete_by_doc_id(rag_doc_id)`

### 3. `api/v1/documents.py` — 5 個 REST 端點

| 端點 | 方法 | Status | 說明 |
|------|------|--------|------|
| `/documents/upload` | POST | 202 | 上傳檔案，BackgroundTasks 觸發 RAG 處理 |
| `/documents/` | GET | 200 | 列出文件（分頁） |
| `/documents/{doc_id}` | GET | 200 | 取得單一文件詳情 |
| `/documents/{doc_id}/status` | GET | 200 | 查詢處理狀態 |
| `/documents/{doc_id}` | DELETE | 204 | 刪除文件（含向量與檔案） |

`_get_document_service` 為公開函式，供測試 override 使用。

### 4. `tests/test_documents.py` — 14 個測試全數通過 ✅

| 分類 | 測試數 | 測試重點 |
|------|--------|---------|
| Upload | 4 | 成功 202、副檔名不允許 422、超過大小 422、無 token 401 |
| Status query | 3 | 上傳後 pending、狀態轉換（直接更新 DB 驗證）、不存在 404 |
| List & detail | 2 | 只看自己的文件、他人文件 403 |
| Delete | 3 | owner 刪除 204、他人 403、admin 可刪任意文件 204 |
| Background task unit | 2 | 成功路徑（更新 completed + rag_doc_id）、失敗路徑（更新 failed + error） |

**測試策略**：
- `doc_client` fixture 使用 `patch.object(DocumentService, "process_document_background", new=AsyncMock)` 跳過真實 RAG
- 狀態轉換測試直接呼叫 `doc_repo.update_status()` 操作測試 DB，再透過 API 驗證
- Admin 測試透過 `db_session.execute(update(User).values(role=UserRole.admin))` 在測試 DB 提升權限
- Background task 單元測試以 module-level patch 替換 `AsyncSessionFactory` 與 `DocumentRepository`

## 驗證結果
- 14 個 Document 測試通過（`uv run pytest tests/test_documents.py -v`）
- 65 個測試全數通過（14 document + 23 conversation + 16 RAG adapter + 12 auth）

---

# STEP 6 — 對話視窗 API 與 SSE Streaming 查詢完成摘要

## 完成項目

### 1. Pydantic Schemas（3 個新檔案）

| 檔案 | Schema | 用途 |
|------|--------|------|
| `schemas/session.py` | `SessionCreateRequest`、`SessionResponse`、`SessionListResponse`、`SessionRenameRequest` | Session CRUD API 輸入/輸出 |
| `schemas/message.py` | `MessageResponse`（含 `from_orm_message` 解析 rag_sources JSON）、`SessionDetailResponse` | GET /{session_id} 詳情回應 |
| `schemas/query.py` | `QueryRequest`（min_length=1, max_length=2000）、`SSEEvent`（type/content/sources/session_id/message_id） | SSE 串流查詢 |

### 2. `api/v1/sessions.py` — Session CRUD Router

| 端點 | 方法 | Status | 說明 |
|------|------|--------|------|
| `/sessions/` | POST | 201 | 建立新對話視窗，支援自訂 query_mode |
| `/sessions/` | GET | 200 | 列出當前用戶所有 session（pagination），回傳 SessionListResponse |
| `/sessions/{session_id}` | GET | 200 | 取得 session 詳情含最近 50 條 messages |
| `/sessions/{session_id}/title` | PATCH | 200 | 重新命名 session |
| `/sessions/{session_id}` | DELETE | 204 | 刪除 session（CASCADE 自動刪除所有 messages） |

DI factory `_get_chat_session_service(db)` 定義於 router 檔案內，遵循 `documents.py` 的 local DI 模式。

### 3. `services/rag_query_service.py` — RAGQueryService

核心查詢流程（DECISION STEP6 方案 B）：
1. `save_user_message()` → 儲存使用者訊息至 DB
2. `get_conversation_context()` → 取得 conv_context（含 Compact）
3. `rag.aquery(question, mode=mode, param=QueryParam(conversation_history=conv_context))` → 取得知識庫 RAG context 字串
   - **使用 `conversation_history=` 參數**（DECISION STEP4，非 `history_messages=`）
4. `llm_adapter.complete_stream(question, system_prompt=rag_result)` → 真實串流 token
5. `save_assistant_message()` + `auto_title_session()` → 儲存回覆並自動命名
6. yield `sources` event（`sources=[]`，TODO：接 RAG source extraction）
7. yield `done` event（含 message_id）
8. 任何階段異常 → yield `error` event 後 return

SSE 輸出格式：
```
data: {"type": "token", "content": "逐字"}
data: {"type": "sources", "sources": []}
data: {"type": "done", "message_id": "uuid", "session_id": "uuid"}
data: {"type": "error", "content": "error message"}
data: [DONE]
```

### 4. `api/v1/query.py` — SSE Query Router

- `POST /query/stream` → StreamingResponse（media_type: text/event-stream）
- Headers：`Cache-Control: no-cache`、`X-Accel-Buffering: no`
- **串流前先驗證 session 存在及所有權**：確保 session 不存在回傳 404 HTTP（而非 SSE error event）
- DI factory `_get_rag_query_service(db)` 建構完整依賴鏈：
  ```
  RAGQueryService
    ├── RAGEngine.get_rag()
    ├── RAGEngine.get_llm_adapter()
    └── ConversationService
          ├── SessionRepository(db)
          ├── MessageRepository(db)
          └── ConversationCompactor(llm_adapter)
  ```

### 5. 計畫書決策標記（`RAG_Platform_ProjectPlan.md`）

| 標記 | 決策內容 |
|------|---------|
| DECISION STEP4 | `rag.aquery()` 必須使用 `QueryParam(conversation_history=)`，非 `history_messages=` |
| DECISION STEP6 方案B | 採真實串流：`rag.aquery()` 取 RAG context，`llm_adapter.complete_stream()` 做串流輸出 |
| DECISION STEP6 DI | DI factory 定義於各 router 檔案內（local），不修改 `deps.py` |

### 6. 測試（20 個新增，全數通過）

**`tests/test_sessions.py`（12 tests）**

| 分類 | 測試數 | 測試重點 |
|------|--------|---------|
| Create | 3 | 預設 mode 201、自訂 mode、無 token 401 |
| List | 2 | 只看自己的 sessions、無 token 401 |
| Get detail | 3 | 正確回傳 session+messages、他人 403、不存在 404 |
| Rename | 2 | 更新標題、他人 403 |
| Delete | 2 | owner 刪除 204 + 再訪 404、他人 403 |

**`tests/test_query.py`（8 tests）**

| 分類 | 測試數 | 測試重點 |
|------|--------|---------|
| Auth guards | 2 | 無 token 401、session 不存在 404（HTTP 層）|
| SSE format | 4 | Content-Type 驗證、token events 內容、[DONE] sentinel、done event 含 message_id |
| DB persistence | 2 | Q&A 後 DB 有 user+assistant messages、rag.aquery 收到正確 question+mode |

測試策略：
- `query_client` fixture 覆寫 `_get_rag_query_service`：注入真實 `ConversationService`（接 test DB）+ mocked RAG + mocked LLM async generator
- mocked LLM `complete_stream` 以 `async def ... yield token` 實作真正的 async generator

## 驗證結果
- 20 個新增測試通過（12 sessions + 8 query）
- 85 個測試全數通過（20 新增 + 65 既有）

---

# STEP 7 — 前端開發完成摘要

## 完成項目

### 技術選型與架構決策

**DECISION STEP7-A (Auth Option B)**: JWT 儲存策略採 httpOnly cookie + Next.js BFF API route，不使用 localStorage。
- Login 後通過 `POST /api/auth/token` 設定 httpOnly cookie
- Page load 通過 `GET /api/auth/me` 讀取 cookie 並回傳 user + token，token 存入 Zustand in-memory
- proxy.ts 檢查 cookie 存在性做路由守衛
- Axios interceptor 使用 Zustand in-memory token 做 Authorization header
- 安全性：cookie 不可被 JS 讀取（httpOnly）；token 在 memory 中，重載自動從 cookie 恢復

**DECISION STEP7-B (Next.js 16)**: middleware.ts → proxy.ts，函式名 middleware() → proxy()
**DECISION STEP7-C (base-ui)**: `asChild` → `render` prop（@base-ui/react 不支援 asChild）
**DECISION STEP7-D (MAC 設計)**: 深色側邊欄（near-black） + 淺色主內容區，全域 `dark` class

### 1. 型別定義

| 檔案 | 說明 |
|------|------|
| `frontend/src/types/auth.ts` | UserPublic, LoginRequest, SignupRequest, TokenResponse |
| `frontend/src/types/session.ts` | ChatSession, SessionListResponse, SessionCreateRequest |
| `frontend/src/types/message.ts` | Message, SessionDetailResponse, SSEEvent, SSEEventType |
| `frontend/src/types/document.ts` | Document, DocumentStatus, DocumentListResponse |

### 2. API 客戶端 (`lib/api.ts`)
- Axios instance，baseURL = `NEXT_PUBLIC_API_URL`
- Request interceptor：自動附加 Authorization header（從 Zustand memory 取 token）
- Response interceptor：401 → logout + redirect `/login`
- 封裝 `authApi`, `sessionApi`, `documentApi`, `adminApi`

### 3. Next.js BFF API Routes
| 路由 | 說明 |
|------|------|
| `POST /api/auth/token` | 設定 httpOnly cookie (maxAge 7天) |
| `DELETE /api/auth/token` | 清除 cookie (logout) |
| `GET /api/auth/me` | 讀取 cookie → 呼叫 FastAPI → 回傳 user + token |

### 4. Zustand Stores
- **authStore**: user, token, isLoading, setAuth, logout, restoreFromServer
- **chatStore**: sessions, messages, streamingContent, 完整 CRUD + streaming state

### 5. 主題設計（Mac 黑白）
- `globals.css`：深色側邊欄 `--sidebar: oklch(0.13 0 0)` (light) / `oklch(0.09 0 0)` (dark)
- `layout.tsx`：`dark` class 預設套用深色模式
- `--radius: 0.5rem`（略小於預設，符合 macOS 精緻感）

### 6. 路由守衛 (`src/proxy.ts`)
- 檢查 `auth_token` cookie 存在性
- 未登入 → redirect `/login?next=<path>`
- 已登入訪問 `/login`、`/signup` → redirect `/chat`
- 根路徑 `/` → 依 cookie 狀態決定 redirect

### 7. 認證頁面 (`(auth)/`)
- **login/page.tsx**: react-hook-form 表單、`useSearchParams` 以 Suspense 包裝、登入成功設 cookie
- **signup/page.tsx**: 密碼強度即時提示、成功後 auto-login
- 使用 shadcn `Card`, `Field`, `FieldLabel`, `FieldError`, `Input`, `Button`

### 8. Dashboard 佈局
- **(dashboard)/layout.tsx**: Client Component，頁面載入時呼叫 `restoreFromServer` 恢復 auth 狀態，未登入 redirect `/login`
- **SessionSidebar.tsx**: 深色側邊欄、新對話（模式選擇）、session 列表（hover 操作選單）、文件庫 / Admin 連結、用戶資訊 + 登出

### 9. 聊天功能
| 元件 | 功能 |
|------|------|
| `ChatWindow.tsx` | 訊息列表 + 自動捲動 + streaming 狀態管理 |
| `MessageBubble.tsx` | user（右對齊黑色）/ assistant（左對齊灰色）+ Markdown + RAG sources |
| `StreamingText.tsx` | 逐字顯示 + blinking cursor 動畫 |
| `InputBar.tsx` | Textarea、Enter 送出 / Shift+Enter 換行、streaming 期間禁用 |
| `useSSEStream.ts` | fetch + ReadableStream 逐行解析 SSE，分派 token/done/error |

### 10. 文件管理
- **UploadZone.tsx**: react-dropzone 拖拉上傳 + 進度條模擬 + 多格式支援
- **DocumentList.tsx**: 狀態顏色標籤 + processing 每 3 秒 polling + 刪除確認

### 11. Admin 頁面
- **admin/users/page.tsx**: 用戶表格 + 角色切換 + 啟用/停用
- **admin/documents/page.tsx**: 所有文件列表 + 刪除

## 錯誤修正記錄
- `FieldMessage` → `FieldError`（shadcn base-nova 實際 export 名稱）
- `TooltipTrigger asChild` → `render` prop（@base-ui 不支援 asChild）
- `DropdownMenuTrigger asChild` → `render` prop
- `delayDuration` → `delay`（TooltipProvider base-ui 參數名）
- `useSearchParams()` 包裝在 Suspense 內（Next.js 16 靜態預渲染要求）

## 驗證結果
- `next build` 成功，12 個 route 全部編譯通過
- TypeScript type check 通過
- 無 linting 錯誤
