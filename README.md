# Mini RAG App — Football Rules Chatbot

A full-stack AI chatbot with RAG (Retrieval-Augmented Generation), LLM streaming, multiple chat sessions, and MCP tool integration.

---

## Architecture Overview

```
Browser (React)          FastAPI Backend          External
port 3000          ←——→  port 8000          ←——→  OpenAI API
                                            ←——→  MCP Server
```

### Files

```
mini-rag-app/
├── backend/
│   ├── main.py          # FastAPI server — routes, streaming, RAG + MCP wiring
│   ├── rag.py           # Embedding + cosine similarity retrieval engine
│   ├── documents.py     # Football rules knowledge base (10 chunks)
│   ├── mcp_server.py    # Local MCP server — get_current_time, get_match_duration
│   └── .env             # API key (never commit this)
└── frontend/
    └── src/
        └── App.js       # React UI — chat, sidebar, streaming, RAG sources panel
```

---

## How to Start

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install fastapi uvicorn openai python-dotenv numpy scikit-learn mcp pytz
uvicorn main:app --reload
```

Backend runs at: http://127.0.0.1:8000
API docs at: http://127.0.0.1:8000/docs

### 2. Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at: http://localhost:3000

### 3. Environment Variables

Create `backend/.env`:
```
OPENAI_API_KEY=your-key-here
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/chats` | List all chats |
| POST | `/chats` | Create a new chat |
| GET | `/chats/{id}` | Get a chat with messages |
| DELETE | `/chats/{id}` | Delete a chat |
| POST | `/chat` | Send a message (streaming SSE) |

---

## How Each Feature Works

### Streaming (Step 2)
- Backend uses `stream=True` with OpenAI and `StreamingResponse` (SSE)
- Frontend reads the stream with `response.body.getReader()`
- Each token arrives as `data: {"token": "Hello"}\n\n`
- React appends each token to the last message in real time

### Multiple Chats (Step 3)
- Each chat has a UUID, title, and message history
- Full conversation history is sent to OpenAI on every request (context memory)
- Chats stored in-memory (resets on server restart)

### RAG — Retrieval-Augmented Generation (Step 4)
- At startup: all 10 football rule chunks are embedded using `text-embedding-3-small`
- On each query: the user's message is embedded and compared to all document vectors
- Top 3 most similar chunks (by cosine similarity) are injected into the system prompt
- AI answers using our rules, not just its training data
- Frontend shows sources panel with similarity scores

### MCP Server (Step 5)
- Local MCP server provides two tools: `get_current_time` and `get_match_duration`
- FastAPI connects via `stdio_client` and lists available tools
- Tools are passed to OpenAI — it decides whether to call one
- If a tool is called, FastAPI runs it via MCP and sends the result back to OpenAI
- Frontend shows a purple banner when a tool was used

---

## Design Decisions

- **In-memory storage** — kept simple intentionally; a real app would use PostgreSQL or Redis
- **scikit-learn cosine similarity** — lightweight, no heavy vector DB needed for 10 documents
- **SSE over WebSockets** — simpler for one-directional streaming (server → client)
- **MCP stdio transport** — standard local MCP pattern, spawns a subprocess per request
- **RAG before tool check** — retrieval always happens; tools only if OpenAI requests them
- **gpt-4o-mini** — fast and cost-efficient for a demo app

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Tailwind CSS |
| Backend | FastAPI, Python 3.12 |
| AI | OpenAI gpt-4o-mini + text-embedding-3-small |
| RAG | NumPy + scikit-learn cosine similarity |
| Tools | MCP (Model Context Protocol) |
| Streaming | Server-Sent Events (SSE) |
