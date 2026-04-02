# RAG 知識庫平台

一個生產級、多模態的 RAG（檢索增強生成）知識庫平台，具備即時串流對話、多輪對話歷史壓縮、以 Session 為範圍的文件檢索功能，以及管理員後台，全部容器化於 Docker 環境中運行。

---

## 目錄

1. [啟動步驟](#1-啟動步驟)
2. [硬體需求](#2-硬體需求)
3. [AI 工具使用說明](#3-ai-工具使用說明)
4. [系統架構](#4-系統架構)

---

## 1. 啟動步驟

### 事前準備

- 已安裝並啟動 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- 系統記憶體至少 **16 GB RAM**，顯示卡至少 **8 GB VRAM**（GPU 可選，但強烈建議）
- 首次啟動需穩定網路連線（需下載約 5 GB 的模型權重）

> **⚠️ 重要：啟動前請先設定環境變數**
>
> 複製範本並填入實際設定：
> ```bash
> cp backend/.env.docker.example backend/.env.docker
> ```
> 然後編輯 `backend/.env.docker`，**務必將 `SECRET_KEY` 改為隨機字串**（用於 JWT 簽名，預設值不安全）：
> ```
> SECRET_KEY=your-random-secret-key-at-least-32-characters
> ```
> 可用以下指令產生隨機 key：
> ```bash
> openssl rand -hex 32
> ```

---

### 第一次啟動（含建置映像檔 + 下載模型）

```bash
# 步驟 1：Clone 專案
git clone <your-repo-url>
cd RAG_TEST

# 步驟 2：建置映像檔並啟動所有服務
docker compose up -d --build

# 步驟 3：下載所需的 AI 模型到 Ollama
#   主語言模型
docker compose exec ollama ollama pull gpt-oss:latest

#   視覺模型（用於多模態文件解析）
docker compose exec ollama ollama pull llava:7b

#   嵌入模型（文件向量化，走 GPU）
docker compose exec ollama ollama pull bge-m3

# 步驟 4：確認所有容器狀態正常
docker compose ps
```

`docker compose ps` 正常輸出如下：

```
名稱                        狀態        連接埠
rag_test-chromadb-1         running     0.0.0.0:8001->8001/tcp
rag_test-ollama-1           healthy     0.0.0.0:11434->11434/tcp
rag_test-backend-1          healthy     0.0.0.0:8000->8000/tcp
rag_test-frontend-1         running     0.0.0.0:3000->3000/tcp
```

---

### 存取應用程式

| 服務        | 網址                        |
|------------|----------------------------|
| 前端介面    | http://localhost:3000      |
| 後端 API   | http://localhost:8000      |
| API 文件    | http://localhost:8000/docs |
| ChromaDB   | http://localhost:8001      |
| Ollama     | http://localhost:11434     |

---

### 首次上傳文件注意事項

> **請耐心等待** — 第一次上傳文件時，系統需要完成以下工作：
>
> 1. **MinerU 下載解析模型**（首次約 10–30 分鐘）：版面偵測、OCR 等 AI 模型需從網路下載，總計約 2 GB，下載期間後端日誌不會有進度輸出，這是正常現象。
> 2. **文字 Embedding 向量化**：文件解析完成後，透過 Ollama bge-m3 模型將文字轉換為向量並存入 ChromaDB。
>
> **第二次以後上傳**：MinerU 模型已快取，處理速度會明顯加快。
>
> 可透過以下指令觀察處理進度：
> ```bash
> docker compose logs -f backend
> ```
> 看到 `Document ... processing complete!` 即表示成功。

---

### 日常啟動（首次設定完成後）

```bash
# 啟動所有容器（無需重新建置）
docker compose up -d

# 停止所有容器
docker compose down
```

---

### 常見問題排查

```bash
# 查看特定服務的日誌
docker compose logs backend
docker compose logs frontend
docker compose logs chromadb

# 重新建置特定服務
docker compose up -d --build backend

# 重置所有資料（警告：將清除所有文件、對話紀錄與模型）
docker compose down -v
rm -rf backend/data backend/uploads backend/rag_storage data/
```

---

## 2. 硬體需求

本平台在本機同時運行三個高資源需求的 AI 工作負載：

| 元件 | 模型 | 記憶體（RAM） | 顯示記憶體（VRAM） | 說明 |
|------|------|:----------:|:---------------:|------|
| 大型語言模型 | `gpt-oss:latest` | ~8 GB | ~8 GB | 主要對話與推理模型 |
| 視覺模型 | `llava:7b` | ~6 GB | ~6 GB | 圖片與多模態文件解析 |
| 嵌入模型 | `bge-m3`（Ollama） | ~2 GB | ~2 GB | 1024 維度文字向量化，由 Ollama 統一管理 |
| ChromaDB | — | ~1 GB | — | 向量儲存（僅 CPU） |
| 後端 + 前端 | — | ~1 GB | — | 應用程式執行環境 |

---

### 最低建議規格

| 資源 | 最低要求 | 建議規格 |
|------|---------|---------|
| CPU | 8 核心 | 12 核心以上 |
| 系統記憶體 | 16 GB | 32 GB |
| 顯示記憶體 | 8 GB（LLM + 視覺模型共用） | 12 GB 以上（可同時運行兩個模型） |
| 儲存空間 | 30 GB 可用空間 | 50 GB 以上（模型權重 + 文件儲存） |
| 作業系統 | Windows 10 / macOS 12 / Ubuntu 20.04 | 最新版本 |

> **VRAM 不足時的行為**：若 GPU 顯示記憶體不足，Ollama 會自動將部分模型層卸載至 CPU RAM，系統仍可正常運作，但推理速度會顯著降低。

> **純 CPU 模式**：系統可在無 GPU 的環境下執行，但 LLM 推理速度約為每秒 1–3 個 token，即時串流體驗較差。

---

## 3. AI 工具使用說明

本平台的開發過程中使用了多個 AI 工具，各自負責不同的開發階段：

### 工具分工

**Claude（架構設計與主要開發）**
- 規劃整體系統架構、模組劃分與 API 介面設計
- 透過 `/init` 建立自訂 `CLAUDE.md` 程式碼規範，確立整個專案的開發標準
- 為前端 Agent 配置 Claude Code frontend skills 以及外部 shadcn/ui skills，讓 Agent 能自主建置 UI 元件
- 依照逐步開發計畫撰寫大部分後端與前端程式碼，每個 Step 完成後均進行模組化測試再繼續推進

**Codex（複雜功能完成 + Bug 修復）**
- Step 7 之後由 Codex 接手，因每個 Step 規模已相當龐大複雜，Claude 的 context 用量消耗過快
- 修復了一個關鍵的 Session 文件檢索 Bug：系統在多份文件存在時，無法正確將檢索範圍限定於當前 Session 所附加的文件。根本原因是文件 Context Manager 中的 Session ID 指向錯誤，由 Codex 定位並解決
- 逐步完成所有 Docker 相關設定：後端與前端的 `Dockerfile`、`.env.docker` 及 `docker-compose.yml`
- 多模態圖片讀取部分選用較小的 `llava:7b` 模型，考量因素為本機硬體的 VRAM 限制

**Gemini 與 GPT（程式碼審查 + 概念諮詢）**
- 對核心模組（RAG 適配器、對話壓縮、SSE 串流）進行程式碼審查
- 就 RAG 架構設計模式、LightRAG 內部機制與 ChromaDB 整合策略進行概念性諮詢
- 未直接用於產生程式碼

### 開發流程總覽

```
系統設計（Claude）
    ↓
CLAUDE.md 程式碼規範 → Claude Code Agent
    ↓
Step 1–6：後端 + 前端主體開發（Claude Code + frontend/shadcn skills）
    ↓
Step 7+：複雜功能（Codex）→ Session Bug 修復 → Docker 環境設定
    ↓
程式碼審查（Gemini + GPT）
```

---

## 4. 系統架構

### 4.1 高層架構圖

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Docker Compose 網路                           │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌───────────────────┐  │
│  │   前端介面   │────▶│   後端 API   │────▶│     ChromaDB      │  │
│  │  Next.js 16  │     │   FastAPI    │     │    向量資料庫      │  │
│  │  Port: 3000  │     │  Port: 8000  │     │   Port: 8001      │  │
│  └──────────────┘     └──────┬───────┘     └───────────────────┘  │
│                              │                                      │
│                              ▼                                      │
│                    ┌──────────────────┐                            │
│                    │      Ollama      │                            │
│                    │  LLM + 視覺模型  │                            │
│                    │  Port: 11434     │                            │
│                    │  gpt-oss:latest  │                            │
│                    │  llava:7b        │                            │
│                    │  bge-m3          │                            │
│                    └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 4.2 後端架構

```
backend/
├── app/
│   ├── main.py                  # FastAPI 入口：CORS、lifespan、路由器、例外處理器
│   ├── config.py                # Pydantic Settings（環境變數：DB、Ollama、ChromaDB、JWT、RAG）
│   │
│   ├── api/
│   │   ├── deps.py              # 依賴注入：get_db()、get_current_user()、get_current_admin()
│   │   └── v1/
│   │       ├── auth.py          # POST /signup、POST /login、POST /logout、GET /me
│   │       ├── documents.py     # POST /upload、GET /、GET /{id}、GET /{id}/status、DELETE /{id}
│   │       ├── sessions.py      # POST /、GET /、GET /{id}、PATCH /{id}/title、DELETE /{id}
│   │       ├── query.py         # POST /stream（SSE 串流 RAG 查詢）
│   │       └── admin.py         # GET /users、PATCH /users/{id}/role、PATCH /users/{id}/status
│   │
│   ├── core/
│   │   ├── security.py          # bcrypt 密碼雜湊、JWT HS256 編碼/解碼
│   │   └── exceptions.py        # 自訂例外 → HTTP 狀態碼（401/403/404/409/422/500）
│   │
│   ├── models/                  # SQLAlchemy ORM（AsyncSession / SQLite + Alembic）
│   │   ├── user.py              # users 資料表：id、email、hashed_password、role、is_active
│   │   ├── document.py          # documents 資料表：id、title、status、rag_doc_id、uploaded_by_id
│   │   ├── chat_session.py      # chat_sessions 資料表：id、user_id、query_mode、compact_summary
│   │   └── message.py           # messages 資料表：id、session_id、role、content、rag_sources
│   │
│   ├── schemas/                 # Pydantic 請求/回應模型
│   │   ├── auth.py              # UserCreateRequest、TokenResponse、UserPublicResponse
│   │   ├── document.py          # DocumentUploadResponse、DocumentListResponse
│   │   ├── session.py           # SessionCreateRequest、SessionResponse、SessionDetailResponse
│   │   ├── message.py           # MessageResponse
│   │   └── query.py             # QueryRequest、SSEEvent
│   │
│   ├── repositories/            # 資料存取層（基礎 CRUD + 特化查詢）
│   │   ├── base.py              # BaseRepository：get、get_all、create、update、delete
│   │   ├── user_repository.py   # get_by_email()
│   │   ├── document_repository.py # get_by_uploader()、update_status()
│   │   ├── session_repository.py  # get_by_user()、update_compact_data()、increment_message_count()
│   │   └── message_repository.py  # get_by_session()、get_recent_by_session()
│   │
│   ├── services/                # 業務邏輯層
│   │   ├── auth_service.py          # register()、authenticate()、產生 JWT Token
│   │   ├── document_service.py      # validate_file()、save_file()、process_document_background()
│   │   ├── chat_session_service.py  # 建立 / 列出 / 取得 / 重命名 / 刪除 Session
│   │   ├── conversation_service.py  # 建立對話歷史、儲存訊息、自動命名、自動壓縮
│   │   └── rag_query_service.py     # query_stream()：RAG 檢索 → LLM → SSE 輸出
│   │
│   ├── rag/                     # RAG 引擎層
│   │   ├── engine.py            # RAGEngine 單例：應用啟動時初始化 LightRAG + 所有適配器
│   │   ├── llm_adapter.py       # OllamaLLMAdapter：封裝 /api/chat（串流 + 非串流）
│   │   ├── embedding_adapter.py # OllamaEmbeddingAdapter：透過 Ollama /api/embed（bge-m3，GPU）
│   │   ├── chroma_adapter.py    # ChromaVectorDBStorage：實作 LightRAG BaseVectorStorage 介面
│   │   └── conversation_compactor.py  # 對話歷史超過閾值時，透過 LLM 壓縮舊訊息
│   │
│   ├── db/
│   │   ├── base.py              # 基礎 ORM 模型（UUID 主鍵 + 時間戳記）
│   │   ├── session.py           # AsyncSession 工廠
│   │   └── migrations/          # Alembic 版本化資料庫遷移
│   │
│   └── __init__.py
│
├── scripts/
│   ├── wait_for_dependencies.py # 啟動前健康檢查 ChromaDB + Ollama
│   └── start_backend.sh         # 進入點：執行遷移 → 等待依賴 → 啟動 uvicorn
│
└── tests/                       # Pytest 單元 + 整合測試
    ├── conftest.py
    ├── test_auth.py
    ├── test_documents.py
    ├── test_sessions.py
    ├── test_conversation.py
    ├── test_query.py
    └── test_rag_adapters.py
```

#### 後端請求流程

```
HTTP 請求
    │
    ▼
FastAPI Router（api/v1/）
    │
    ├── deps.py ──► JWT 驗證 → get_current_user()
    │
    ▼
服務層（Service Layer）
    ├── AuthService          → core/security.py（bcrypt、JWT）
    ├── DocumentService      → RAGEngine（背景任務：解析 + 索引）
    ├── ChatSessionService   → SessionRepository
    ├── ConversationService  → MessageRepository + ConversationCompactor
    └── RAGQueryService      → RAGEngine → OllamaLLMAdapter → SSE 串流
    │
    ▼
Repository 層
    └── Async SQLAlchemy → SQLite

RAG 查詢流程：
    ConversationService（建立對話歷史）
        ↓
    ChromaVectorDBStorage（Session 範圍向量搜尋）
        ↓
    OllamaLLMAdapter（透過 Ollama /api/chat 串流 token）
        ↓
    SSE AsyncGenerator → HTTP 回應
```

#### RAG 引擎內部架構

```
RAGEngine（單例）
    │
    ├── RAGAnything（基於 LightRAG）
    │       ├── OllamaLLMAdapter       → Ollama gpt-oss:latest  （對話 + 推理）
    │       ├── OllamaVisionAdapter    → Ollama llava:7b         （圖片說明生成）
    │       ├── OllamaEmbeddingAdapter → Ollama bge-m3            （1024 維向量嵌入，GPU）
    │       └── ChromaVectorDBStorage  → ChromaDB :8001          （向量搜尋）
    │
    └── 文件處理流水線
            PDF/DOCX/PPTX/XLSX → mineru 解析器 → 文字區塊
            圖片                → llava:7b      → 文字說明
            所有區塊            → bge-m3        → 向量嵌入 → ChromaDB
```

---

### 4.3 前端架構

```
frontend/src/
├── app/                         # Next.js 16 App Router
│   ├── layout.tsx               # 根佈局：主題提供者、應用載入時恢復登入狀態
│   ├── page.tsx                 # 落地頁
│   │
│   ├── (auth)/                  # 公開驗證路由（置中卡片佈局）
│   │   ├── login/page.tsx       # 登入表單（react-hook-form + zod 驗證）
│   │   └── signup/page.tsx      # 註冊表單
│   │
│   ├── (dashboard)/             # 受保護路由（側欄導航佈局）
│   │   ├── chat/
│   │   │   ├── page.tsx         # 查詢模式選擇（Hybrid / Local / Global）
│   │   │   └── [sessionId]/     # 活躍對話 Session 檢視
│   │   │       └── page.tsx
│   │   ├── documents/page.tsx   # 文件上傳 + 管理
│   │   └── admin/
│   │       ├── users/page.tsx        # 使用者角色與狀態管理
│   │       └── documents/page.tsx    # 所有文件（管理員視角）
│   │
│   └── api/                     # Next.js API 路由（BFF 模式）
│       └── auth/
│           ├── token/route.ts   # POST：將 JWT 儲存為 httpOnly Cookie
│           └── me/route.ts      # GET：使用 Cookie Token 代理 auth/me
│
├── components/
│   ├── ui/                      # shadcn/ui 基礎元件（16 個檔案）
│   │   └── button、input、card、dialog、avatar、badge、dropdown-menu、
│   │       label、textarea、progress、skeleton、spinner、scroll-area、
│   │       separator、sonner、tooltip
│   │
│   ├── chat/
│   │   ├── ChatWindow.tsx       # 主要對話容器，協調 SSE + Zustand store
│   │   ├── InputBar.tsx         # 訊息輸入框（Enter 送出，Shift+Enter 換行）
│   │   ├── MessageBubble.tsx    # 使用者（右）/ 助理（左，支援 Markdown 渲染）
│   │   ├── SessionSidebar.tsx   # Session 列表：建立、重命名、刪除、導航
│   │   └── StreamingText.tsx    # 即時 token 顯示，含游標動畫效果
│   │
│   ├── documents/
│   │   ├── UploadZone.tsx       # 拖放上傳（react-dropzone），可選擇附加到 Session
│   │   └── DocumentList.tsx     # 文件列表：狀態輪詢、刪除功能
│   │
│   ├── BlurText.tsx             # 文字模糊淡入動畫效果
│   ├── Galaxy.tsx               # 3D WebGL 星系背景（使用 OGL）
│   └── LightRays.tsx            # Canvas 光線特效動畫
│
├── hooks/
│   └── useSSEStream.ts          # EventSource 消費者 → onToken / onDone / onError 回調
│
├── lib/
│   ├── api.ts                   # Axios 實例：自動注入 Bearer Token、401 自動跳轉登入
│   └── utils.ts                 # cn() className 合併工具
│
├── store/
│   ├── authStore.ts             # Zustand：user、token、restoreFromServer()、logout()
│   └── chatStore.ts             # Zustand：sessions[]、messages{}、streamingContent、isStreaming
│
└── types/
    ├── auth.ts                  # UserPublic、LoginRequest、TokenResponse
    ├── session.ts               # ChatSession、SessionListResponse、SessionDetailResponse
    ├── message.ts               # Message（role: user | assistant | system）
    └── document.ts              # Document、DocumentStatus
```

#### 前端資料流

```
使用者操作
    │
    ▼
頁面元件（app/...）
    │
    ├── 從 Zustand store 讀取狀態（authStore / chatStore）
    ├── 呼叫 lib/api.ts 中的 API 函式
    └── 使用 components/ 中的 UI 元件

對話 SSE 串流流程：
    InputBar（使用者送出訊息）
        ↓
    chatStore.setIsStreaming(true)
        ↓
    useSSEStream.stream() → POST /api/v1/query/stream
        ↓
    onToken() → chatStore.appendStreamToken(token)
        ↓
    StreamingText 渲染 chatStore.streamingContent
        ↓
    onDone() → chatStore.finalizeStreamMessage() → MessageBubble
```

---

### 4.4 資料庫設計

#### 技術選型

| 項目 | 選擇 | 說明 |
|------|------|------|
| 資料庫引擎 | SQLite | 輕量、無需額外服務、資料存於 `/app/data/rag_platform.db` |
| ORM | SQLAlchemy 2.x（AsyncSession） | 全非同步操作，搭配 `aiosqlite` 驅動 |
| 遷移工具 | Alembic | 版本化 Schema 管理，啟動時自動執行 |
| 主鍵格式 | UUID | 所有資料表使用 UUID 作為主鍵，避免 ID 可猜測性 |

---

#### 資料表設計

**users — 使用者帳號**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID，PK | 使用者唯一識別碼 |
| email | String(255)，唯一索引 | 登入帳號，不可重複 |
| hashed_password | String(255) | bcrypt 雜湊，12 rounds |
| full_name | String(255) | 顯示名稱 |
| role | Enum(admin, user) | 權限角色，預設 user |
| is_active | Boolean | 帳號啟用狀態，預設 true |
| created_at / updated_at | DateTime | 建立與更新時間戳記 |

**documents — 上傳文件**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID，PK | 文件唯一識別碼 |
| title | String(512) | 文件標題（預設為原始檔名） |
| original_filename | String(512) | 原始上傳檔名 |
| stored_filename | String(512) | 儲存於磁碟的實際檔名（UUID 命名，避免衝突） |
| file_path | String(1024) | 完整檔案路徑 |
| file_size | Integer | 檔案大小（bytes） |
| mime_type | String(128) | MIME 類型（application/pdf 等） |
| status | Enum | pending → processing → completed / failed |
| error_message | Text，可空 | 處理失敗時的錯誤訊息 |
| uploaded_by_id | UUID，FK → users | 上傳者，cascade delete |
| rag_doc_id | String(512)，可空 | LightRAG 內部文件 ID，用於向量刪除 |
| created_at | DateTime | 上傳時間 |

**chat_sessions — 對話 Session**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID，PK | Session 唯一識別碼 |
| user_id | UUID，FK → users | 所屬使用者，cascade delete |
| title | String(512) | Session 名稱，預設「新對話」，首次提問後自動更新 |
| query_mode | String(32) | 查詢模式：hybrid / local / global |
| message_count | Integer | 訊息總數，用於觸發對話壓縮判斷 |
| last_message_at | DateTime，可空 | 最後一則訊息的時間，用於側欄排序 |
| is_compacted | Boolean | 是否已執行過對話歷史壓縮 |
| compact_summary | Text，可空 | 壓縮摘要內容，由 LLM 生成 |
| created_at | DateTime | 建立時間 |

**messages — 對話訊息**

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | UUID，PK | 訊息唯一識別碼 |
| session_id | UUID，FK → chat_sessions | 所屬 Session，cascade delete |
| role | Enum(user, assistant, system) | 訊息角色 |
| content | Text | 訊息內容 |
| token_count | Integer，可空 | 預估 token 數量 |
| is_compacted_summary | Boolean | 是否為對話壓縮摘要訊息 |
| rag_sources | Text，可空 | JSON 陣列，記錄 RAG 檢索來源 |
| query_mode | String(32)，可空 | 該次查詢使用的模式 |
| created_at | DateTime | 訊息時間戳記 |

> **複合索引**：`messages` 資料表在 `(session_id, created_at)` 上建立複合索引，加速按 Session 排序查詢。

---

#### 資料表關聯圖

```
┌────────────────────┐         ┌───────────────────────┐
│       users        │         │       documents        │
├────────────────────┤         ├───────────────────────┤
│ id（UUID，PK）     │──────┐  │ id（UUID，PK）        │
│ email（唯一）      │      │  │ title                 │
│ hashed_password    │      │  │ original_filename     │
│ full_name          │      │  │ stored_filename       │
│ role（admin|user） │      │  │ file_path             │
│ is_active          │      │  │ file_size             │
│ created_at         │      │  │ mime_type             │
│ updated_at         │      └─▶│ uploaded_by_id（FK）  │
└────────────────────┘         │ status（pending|       │
         │                     │   processing|          │
         │                     │   completed|failed）   │
         │                     │ rag_doc_id            │
         │                     │ error_message         │
         │                     │ created_at            │
         ▼                     └───────────────────────┘
┌────────────────────┐
│   chat_sessions    │
├────────────────────┤
│ id（UUID，PK）     │
│ user_id（FK）      │
│ title              │
│ query_mode         │
│  （hybrid|local|   │
│   global）         │
│ message_count      │
│ last_message_at    │
│ is_compacted       │
│ compact_summary    │
│ created_at         │
└────────────────────┘
         │
         │ 1:N
         ▼
┌────────────────────┐
│      messages      │
├────────────────────┤
│ id（UUID，PK）     │
│ session_id（FK）   │
│ role（user|        │
│  assistant|system）│
│ content（Text）    │
│ token_count        │
│ is_compacted_      │
│  summary           │
│ rag_sources（JSON）│
│ query_mode         │
│ created_at         │
└────────────────────┘
```

#### Repository 資料存取層

所有資料庫操作透過 Repository 模式封裝，Service 層不直接使用 SQLAlchemy Session：

```
BaseRepository（通用 CRUD）
    ├── get_by_id(id)           → 單筆查詢
    ├── get_all(skip, limit)    → 分頁列表
    ├── create(data_dict)       → 新增記錄
    ├── update(id, data_dict)   → 更新欄位
    └── delete(id)              → 刪除記錄

UserRepository
    └── get_by_email(email)     → 登入查詢

DocumentRepository
    ├── get_by_uploader(user_id)           → 使用者文件列表
    ├── update_status(id, status, error)   → 更新處理狀態
    └── get_docs_by_status(status)         → 依狀態篩選

SessionRepository
    ├── get_by_user(user_id)               → 使用者 Session 列表
    ├── increment_message_count(id)        → 訊息計數 +1
    ├── update_last_message(id, timestamp) → 更新最後訊息時間
    ├── update_title(id, title)            → 重命名
    └── update_compact_data(id, summary)   → 儲存壓縮摘要

MessageRepository
    ├── get_by_session(session_id)         → 取得所有訊息
    └── get_recent_by_session(id, limit)   → 取得最近 N 則（對話歷史組裝用）
```

---

### 4.5 API 端點總覽

#### 驗證
| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/v1/auth/signup` | 註冊新使用者 |
| POST | `/api/v1/auth/login` | 身份驗證，回傳 JWT |
| POST | `/api/v1/auth/logout` | 登出 |
| GET | `/api/v1/auth/me` | 取得當前使用者資訊 |

#### 文件
| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/v1/documents/upload` | 上傳文件（背景 RAG 處理） |
| GET | `/api/v1/documents/` | 列出文件 |
| GET | `/api/v1/documents/{id}` | 取得文件詳情 |
| GET | `/api/v1/documents/{id}/status` | 輪詢處理狀態 |
| DELETE | `/api/v1/documents/{id}` | 刪除文件 + 清除向量 |

#### 對話 Session
| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/v1/sessions/` | 建立新 Session |
| GET | `/api/v1/sessions/` | 列出使用者所有 Session |
| GET | `/api/v1/sessions/{id}` | 取得 Session + 訊息 |
| PATCH | `/api/v1/sessions/{id}/title` | 重命名 Session |
| DELETE | `/api/v1/sessions/{id}` | 刪除 Session |

#### 查詢
| 方法 | 端點 | 說明 |
|------|------|------|
| POST | `/api/v1/query/stream` | RAG 查詢（SSE 串流回應） |

#### 管理員
| 方法 | 端點 | 說明 |
|------|------|------|
| GET | `/api/v1/admin/users` | 列出所有使用者 |
| PATCH | `/api/v1/admin/users/{id}/role` | 變更使用者角色 |
| PATCH | `/api/v1/admin/users/{id}/status` | 啟用 / 停用帳號 |
| DELETE | `/api/v1/admin/vectors/orphaned` | 清除孤立向量 |

---

### 4.6 核心功能說明

#### 多模態文件支援

| 格式 | 處理方式 |
|------|---------|
| PDF | mineru 解析器 → 文字區塊 |
| DOCX / DOC | LibreOffice 轉換或快速 XML 解析 |
| PPTX / PPT | LibreOffice 轉換 |
| XLSX / XLS | LibreOffice 轉換 |
| JPG / PNG | llava:7b 視覺模型 → 文字說明 |
| MD / TXT | 直接文字解析 |

#### 查詢模式

| 模式 | 說明 | 最適合 |
|------|------|--------|
| Hybrid（混合） | 結合語意搜尋 + 知識圖譜 | 一般用途（預設） |
| Local（局部） | 聚焦文件片段 | 單份文件深度追問 |
| Global（全域） | 全域知識圖譜遍歷 | 跨文件摘要與綜合分析 |

#### 多輪對話壓縮機制（Conversation Compaction）

##### 設計動機

LLM 的 Context Window 有限，隨著對話輪數增加，若將所有歷史訊息全部送入 LLM，會導致：
- 超出 Context Window 上限，造成截斷或錯誤
- 輸入 token 暴增，推理速度下降、成本上升

本系統設計了一套**自動對話壓縮機制**，在不中斷使用者對話體驗的前提下，維持 Context 在可控範圍內。

##### 觸發條件與參數

| 參數 | 預設值 | 說明 |
|------|:------:|------|
| `conversation_compact_threshold` | 15 | 訊息數達到此值時觸發壓縮 |
| `conversation_compact_target` | 6 | 壓縮後保留最近幾則訊息不動 |
| `conversation_max_history_turns` | 20 | 組裝對話歷史時最多取幾則 |

##### 壓縮流程

```
每次使用者提問時，ConversationService 檢查 session.message_count

message_count < 15
    ↓
直接取最近 N 則訊息組成 history，送入 RAG 查詢

message_count >= 15（觸發壓縮）
    ↓
取出所有訊息，分為兩組：
    ├── 較舊的訊息（全部 - 最近 6 則）→ 送入 LLM 生成摘要
    └── 最近 6 則訊息 → 原文保留

    ↓
刪除「較舊的訊息」（從 messages 資料表）
    ↓
將摘要儲存為 system role 訊息（is_compacted_summary = True）
    ↓
將摘要同步寫入 chat_sessions.compact_summary 欄位
    ↓
組裝 history：[system prompt] + [摘要] + [最近 6 則] + [當前問題]
```

##### 壓縮 Prompt（中文摘要）

```
以下是一段對話的歷史紀錄，請將其整理成一段簡潔的摘要，
保留所有重要的問題、答案與關鍵資訊，以繁體中文回答：

{conversation_history}

請以「對話摘要：」開頭，輸出摘要內容。
```

##### 對話歷史組裝規則

送入 LLM 的 `history` 陣列按以下順序組裝，並過濾掉不應暴露給 LLM 的訊息：

```python
history = [
    {"role": "system", "content": "你是 RAG 知識庫助理..."},  # 固定系統提示
    {"role": "assistant", "content": compact_summary},          # 壓縮摘要（若存在）
    # 過濾掉：is_compacted_summary = True 的舊摘要訊息
    # 過濾掉：[[document-upload]] 開頭的文件上傳通知訊息
    {"role": "user",      "content": "..."},                    # 保留的對話訊息
    {"role": "assistant", "content": "..."},
    ...
    {"role": "user",      "content": current_question},         # 當前問題
]
```

##### Token 估算

```python
def estimate_tokens(text: str) -> int:
    # 中文約 0.5 token/字，英文約 0.25 token/字
    # 以 len // 3 作為保守粗估
    return len(text) // 3
```

#### Session 範圍文件檢索

當文件透過上傳附加到特定 Chat Session 時，RAG 檢索會自動限制在該 Session 所附加的文件範圍內，防止與全域知識庫產生交叉干擾。

---

### 4.7 基礎設施（Docker Compose）

```
docker-compose.yml
│
├── chromadb          （chromadb/chroma:latest）
│   ├── 連接埠：8001
│   └── 掛載：./data/chromadb → /chroma/data
│
├── ollama            （ollama/ollama:latest）
│   ├── 連接埠：11434
│   ├── 掛載：./data/ollama → /root/.ollama  （模型快取）
│   └── 健康檢查：ollama list（重試 20 次，間隔 10 秒）
│
├── backend           （./backend/Dockerfile）
│   ├── 連接埠：8000
│   ├── 依賴：chromadb（已啟動）+ ollama（健康）
│   ├── 掛載：
│   │   ├── ./backend/data     → /app/data      （SQLite 資料庫）
│   │   ├── ./backend/uploads  → /app/uploads   （上傳檔案）
│   │   └── ./backend/rag_storage → /app/rag_storage
│   └── 健康檢查：GET /health（重試 20 次，啟動等待 30 秒）
│
└── frontend          （./frontend/Dockerfile — 多階段建置）
    ├── 連接埠：3000
    ├── 依賴：backend（健康）
    ├── 建置階段：deps → builder → runner（node:20-alpine）
    └── 健康檢查：fetch localhost:3000（重試 10 次）
```
