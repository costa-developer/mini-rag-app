import { useState, useEffect } from "react";

const API = "http://localhost:8000";

function App() {
  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState([]);
  const [toolUsed, setToolUsed] = useState(null);

  useEffect(() => { fetchChats(); }, []);
  useEffect(() => {
    if (activeChatId) fetchChat(activeChatId);
  }, [activeChatId]);

  const fetchChats = async () => {
    const res = await fetch(`${API}/chats`);
    const data = await res.json();
    setChats(data);
  };

  const fetchChat = async (chatId) => {
    const res = await fetch(`${API}/chats/${chatId}`);
    const data = await res.json();
    setMessages(data.messages);
    setSources([]);
    setToolUsed(null);
  };

  const createNewChat = async () => {
    const res = await fetch(`${API}/chats`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: "New Match" }),
    });
    const newChat = await res.json();
    setChats((prev) => [...prev, newChat]);
    setActiveChatId(newChat.id);
    setMessages([]);
    setSources([]);
    setToolUsed(null);
  };

  const deleteChat = async (chatId, e) => {
    e.stopPropagation();
    await fetch(`${API}/chats/${chatId}`, { method: "DELETE" });
    setChats((prev) => prev.filter((c) => c.id !== chatId));
    if (activeChatId === chatId) {
      setActiveChatId(null);
      setMessages([]);
      setSources([]);
      setToolUsed(null);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !activeChatId) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setSources([]);
    setToolUsed(null);

    setChats((prev) =>
      prev.map((c) =>
        c.id === activeChatId && c.title === "New Match"
          ? { ...c, title: input.slice(0, 30) }
          : c
      )
    );

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      const response = await fetch(`${API}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: activeChatId, message: input }),
      });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));

        for (const line of lines) {
          const data = line.replace("data: ", "");
          if (data === "[DONE]") break;
          const parsed = JSON.parse(data);

          if (parsed.sources) {
            setSources(parsed.sources);
            continue;
          }

          if (parsed.tool_used) {
            setToolUsed(parsed.tool_used);
            continue;
          }

          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: updated[updated.length - 1].content + parsed.token,
            };
            return updated;
          });
        }
      }
    } catch (error) {
      console.error("Error:", error);
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div className="flex h-screen bg-[#0a0f0d] font-sans text-slate-200">

      {/* Sidebar - Dark Locker Room Style */}
      <div className="w-72 bg-[#0d1411] border-r border-emerald-900/30 flex flex-col shadow-2xl">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="bg-emerald-500 w-12 h-12 rounded-full flex items-center justify-center text-2xl shadow-[0_0_20px_rgba(16,185,129,0.4)]">
              ⚽
            </div>
            <div>
              <h1 className="text-xl font-black tracking-tighter text-white uppercase italic">VAR Bot</h1>
              <p className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest">Official Rules RAG</p>
            </div>
          </div>
          <button
            onClick={createNewChat}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white py-3 px-4 rounded-xl text-sm font-black uppercase tracking-wider transition-all hover:shadow-[0_0_15px_rgba(16,185,129,0.3)] active:scale-95"
          >
            Kickoff New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4 flex flex-col gap-2">
          <p className="text-[10px] font-bold text-slate-500 px-4 uppercase tracking-widest mb-2">Match History</p>
          {chats.map((chat) => (
            <div
              key={chat.id}
              onClick={() => setActiveChatId(chat.id)}
              className={`flex items-center justify-between px-4 py-3 rounded-xl cursor-pointer text-sm group transition-all border ${
                activeChatId === chat.id
                  ? "bg-emerald-950/40 border-emerald-500/50 text-emerald-400"
                  : "border-transparent text-slate-500 hover:bg-white/5 hover:text-slate-300"
              }`}
            >
              <span className="truncate flex-1 font-medium">{chat.title}</span>
              <button
                onClick={(e) => deleteChat(chat.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:text-red-400 transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main Pitch Area */}
      <div className="flex-1 flex flex-col overflow-hidden relative bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-[#141c18] to-[#0a0f0d]">
        {!activeChatId ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-32 h-32 border-4 border-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6 relative">
                <span className="text-6xl animate-bounce">⚽</span>
                <div className="absolute inset-0 border-t-4 border-emerald-500 rounded-full animate-spin-slow"></div>
              </div>
              <h2 className="text-4xl font-black text-white uppercase italic tracking-tighter mb-2">Enter the Arena</h2>
              <p className="text-slate-500 font-medium">Select a match or start a new inquiry to begin VAR review.</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex overflow-hidden">

            {/* Chat column */}
            <div className="flex-1 flex flex-col">
              <div className="flex-1 overflow-y-auto p-6 lg:px-12 flex flex-col gap-6">
                {messages.map((msg, index) => (
                  <div
                    key={index}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] px-6 py-4 rounded-3xl text-[15px] leading-relaxed shadow-xl ${
                        msg.role === "user"
                          ? "bg-emerald-600 text-white rounded-tr-none shadow-emerald-900/20"
                          : "bg-[#1a2420] text-slate-200 rounded-tl-none border border-emerald-900/30"
                      }`}
                    >
                      <p className="font-medium">{msg.content}</p>
                      {loading && index === messages.length - 1 && msg.role === "assistant" && (
                        <div className="flex gap-1 mt-2">
                          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce"></span>
                          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                          <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Tactical Tool Banner */}
              {toolUsed && (
                <div className="mx-6 mb-4 px-4 py-3 bg-blue-950/30 border border-blue-500/30 rounded-2xl text-[11px] text-blue-400 flex items-center gap-3 uppercase tracking-tighter">
                  <span className="bg-blue-500 text-white px-2 py-0.5 rounded font-black">AI REPLAY</span>
                  <span>Deploying <strong>{toolUsed.name}</strong>... Result: {toolUsed.result}</span>
                </div>
              )}

              {/* Input - The "Control Room" */}
              <div className="p-6 bg-[#0d1411]/80 backdrop-blur-md border-t border-emerald-900/30">
                <div className="max-w-4xl mx-auto flex gap-4 items-center bg-black/40 p-2 rounded-2xl border border-emerald-500/20 focus-within:border-emerald-500/50 transition-all">
                  <input
                    className="flex-1 bg-transparent px-4 py-2 text-sm outline-none placeholder:text-slate-600 text-white"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Inquire about Offsides, Fouls, or League Rules..."
                  />
                  <button
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-white px-6 py-2.5 rounded-xl font-black uppercase tracking-widest transition-all shadow-lg shadow-emerald-900/20"
                  >
                    SUBMIT
                  </button>
                </div>
              </div>
            </div>

            {/* Tactical Insights (Sources) - Right Side Panel */}
            {sources.length > 0 && (
              <div className="w-80 border-l border-emerald-900/30 bg-black/20 flex flex-col">
                <div className="p-6 border-b border-emerald-900/30">
                  <h2 className="text-xs font-black text-emerald-500 uppercase tracking-[0.2em] flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full shadow-[0_0_8px_#10b981]"></span>
                    Tactical Insights
                  </h2>
                </div>
                <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
                  {sources.map((source, index) => (
                    <div
                      key={index}
                      className="bg-[#141c18] rounded-xl p-4 border border-emerald-900/20 hover:border-emerald-500/40 transition-all group"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] font-black text-slate-500 uppercase italic">Ref Source {index + 1}</span>
                        <span className="text-[10px] font-bold text-emerald-500 bg-emerald-500/10 px-2 py-0.5 rounded">
                          {(source.similarity * 100).toFixed(0)}% MATCH
                        </span>
                      </div>
                      <p className="text-[12px] text-slate-400 leading-relaxed font-medium">
                        {source.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}
      </div>
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .animate-spin-slow {
          animation: spin-slow 8s linear infinite;
        }
      `}} />
    </div>
  );
}

export default App;