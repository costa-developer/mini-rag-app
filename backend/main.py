from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import uuid
import asyncio
import sys
import datetime

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from documents import DOCUMENTS
from rag import build_knowledge_base, retrieve

load_dotenv()

app = FastAPI()

# ─────────────────────────────────────────
# Set to True for demo without API key
# Set to False when real API key is available
# ─────────────────────────────────────────
MOCK_MODE = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

knowledge_base = []
chats = {}


class ChatRequest(BaseModel):
    chat_id: str
    message: str


class NewChatRequest(BaseModel):
    title: str = "New Chat"


async def get_mcp_tools():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            openai_tools = []
            for tool in tools_result.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
            return openai_tools


async def call_mcp_tool(tool_name: str, tool_args: dict):
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["mcp_server.py"],
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            return result.content[0].text


@app.on_event("startup")
async def startup_event():
    global knowledge_base
    knowledge_base = build_knowledge_base(DOCUMENTS)


@app.get("/")
def root():
    return {"status": "Backend is running!"}


@app.get("/chats")
def get_chats():
    return list(chats.values())


@app.post("/chats")
def create_chat(request: NewChatRequest):
    chat_id = str(uuid.uuid4())
    chat = {"id": chat_id, "title": request.title, "messages": []}
    chats[chat_id] = chat
    return chat


@app.get("/chats/{chat_id}")
def get_chat(chat_id: str):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chats[chat_id]


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: str):
    if chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")
    del chats[chat_id]
    return {"status": "deleted"}


@app.post("/chat")
async def chat(request: ChatRequest):
    if request.chat_id not in chats:
        raise HTTPException(status_code=404, detail="Chat not found")

    current_chat = chats[request.chat_id]

    # RAG always runs — even in mock mode
    rag_results = retrieve(request.message, knowledge_base, top_k=3)
    context = "\n\n".join([
        f"[{r['title']}]: {r['content']}"
        for r in rag_results
    ])

    current_chat["messages"].append({
        "role": "user",
        "content": request.message
    })

    if len(current_chat["messages"]) == 1:
        current_chat["title"] = request.message[:40]

    system_prompt = f"""You are a helpful football rules expert.
Use the retrieved rules below to answer accurately.
You also have access to tools for getting the current time and match duration.
Use them when the user asks about time or how long a match has been going.
If the answer is not in the context, say so honestly.

Retrieved rules:
{context}"""

    async def stream_response():

        # ─────────────────────────────────────────
        # MOCK MODE — streams a realistic reply
        # without calling OpenAI
        # ─────────────────────────────────────────
        if MOCK_MODE:
            msg_lower = request.message.lower()

            # Pick the best mock reply based on keywords
            if "offside" in msg_lower:
                reply = (
                    "A player is in an offside position if any part of their head, body or feet "
                    "is closer to the opponent's goal line than both the ball and the second-last opponent. "
                    "However, simply being in an offside position is not an offence — the player must be "
                    "actively involved in play by interfering with play, interfering with an opponent, "
                    "or gaining an advantage from being in that position."
                )
                tool_used = None

            elif "penalty" in msg_lower:
                reply = (
                    "A penalty kick is awarded when a player commits a direct free kick offence "
                    "inside their own penalty area. The ball is placed on the penalty mark, which is "
                    "11 metres from goal. The goalkeeper must remain on the goal line until the ball "
                    "is kicked. If the goalkeeper moves off the line before the kick and the penalty "
                    "is missed, the kick must be retaken."
                )
                tool_used = None

            elif "card" in msg_lower or "yellow" in msg_lower or "red" in msg_lower:
                reply = (
                    "A yellow card is shown to caution a player for offences such as unsporting behaviour, "
                    "dissent, persistent infringement, or time wasting. A player who receives two yellow "
                    "cards in the same match is shown a red card and sent off. A straight red card is given "
                    "for serious foul play, violent conduct, spitting, or denying an obvious goalscoring "
                    "opportunity. A sent-off player cannot be replaced by a substitute."
                )
                tool_used = None

            elif "var" in msg_lower or "video" in msg_lower:
                reply = (
                    "The Video Assistant Referee reviews four match-changing situations: goals, "
                    "penalty decisions, direct red card incidents, and cases of mistaken identity. "
                    "The VAR only intervenes for clear and obvious errors. The on-field referee always "
                    "makes the final decision — either by accepting the VAR recommendation or by "
                    "reviewing footage on the pitchside monitor themselves."
                )
                tool_used = None

            elif "time" in msg_lower or "clock" in msg_lower or "duration" in msg_lower:
                now = datetime.datetime.now().strftime("%H:%M:%S")
                reply = (
                    f"The current time is {now}. "
                    "A standard football match consists of two halves of 45 minutes each, "
                    "with stoppage time added at the end of each half for time lost. "
                    "If a winner must be determined, two periods of 15 minutes extra time are played, "
                    "followed by a penalty shootout if still level."
                )
                tool_used = {
                    "name": "get_current_time",
                    "result": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
                }

            elif "substitute" in msg_lower or "substitution" in msg_lower:
                reply = (
                    "Each team is allowed a maximum of 3 substitutions in most competitions, "
                    "though some allow 5. A substituted player cannot return to the match. "
                    "Substitutions can only be made when play is stopped, and the referee must "
                    "be informed before the substitution is made. In extra time, one additional "
                    "substitution is permitted."
                )
                tool_used = None

            elif "throw" in msg_lower:
                reply = (
                    "A throw-in is awarded when the whole of the ball passes over the touchline. "
                    "The throw-in is taken by a player from the team that did not last touch the ball. "
                    "The thrower must face the field of play, have both feet on or behind the touchline, "
                    "and deliver the ball from behind and over the head using both hands. "
                    "A goal cannot be scored directly from a throw-in."
                )
                tool_used = None

            else:
                # Default — use the top RAG result as the basis
                top = rag_results[0]
                reply = (
                    f"Based on the football rules I retrieved, the most relevant section is "
                    f"'{top['title']}': {top['content'][:300]}... "
                    f"This was matched with a similarity score of {round(top['similarity'] * 100)}%. "
                    f"Feel free to ask a more specific question about offside, penalties, cards, VAR, "
                    f"substitutions or match duration!"
                )
                tool_used = None

            # Stream the reply word by word with a small delay
            words = reply.split(" ")
            full_reply = ""
            for word in words:
                token = word + " "
                full_reply += token
                yield f"data: {json.dumps({'token': token})}\n\n"
                await asyncio.sleep(0.04)

            # Save to history
            current_chat["messages"].append({
                "role": "assistant",
                "content": full_reply.strip()
            })

            # Send RAG sources
            yield f"data: {json.dumps({'sources': rag_results})}\n\n"

            # Send tool info if time tool was used
            if tool_used:
                yield f"data: {json.dumps({'tool_used': tool_used})}\n\n"

            yield "data: [DONE]\n\n"

        # ─────────────────────────────────────────
        # REAL MODE — full OpenAI + MCP flow
        # ─────────────────────────────────────────
        else:
            tools = await get_mcp_tools()

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *current_chat["messages"]
                ],
                tools=tools,
                stream=False
            )

            message = response.choices[0].message
            tool_used = None

            if message.tool_calls:
                tool_call = message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_result = await call_mcp_tool(tool_name, tool_args)
                tool_used = {"name": tool_name, "result": tool_result}

                second_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *current_chat["messages"],
                        message,
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        }
                    ],
                    stream=True
                )

                full_reply = ""
                for chunk in second_response:
                    token = chunk.choices[0].delta.content
                    if token is not None:
                        full_reply += token
                        yield f"data: {json.dumps({'token': token})}\n\n"

            else:
                stream = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *current_chat["messages"]
                    ],
                    stream=True
                )

                full_reply = ""
                for chunk in stream:
                    token = chunk.choices[0].delta.content
                    if token is not None:
                        full_reply += token
                        yield f"data: {json.dumps({'token': token})}\n\n"

            current_chat["messages"].append({
                "role": "assistant",
                "content": full_reply
            })

            yield f"data: {json.dumps({'sources': rag_results})}\n\n"

            if tool_used:
                yield f"data: {json.dumps({'tool_used': tool_used})}\n\n"

            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )