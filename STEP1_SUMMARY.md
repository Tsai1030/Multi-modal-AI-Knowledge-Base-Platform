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
