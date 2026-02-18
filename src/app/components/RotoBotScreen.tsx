import { useState } from "react";
import { Brain, Send, TrendingUp, Trophy, Target, Zap } from "lucide-react";
import { RotoBotLogo } from "./RotoBotLogo";
// Chat uses hardcoded responses for now — Gemini integration planned for Phase 2

interface Message {
  role: "user" | "bot";
  text: string;
}

const QUICK_PROMPTS = [
  "Who are RotoBot's Final Four picks?",
  "Best upset to make in my bracket?",
  "Who is the best player in the tournament?",
  "Should I pick Auburn or Duke for the title?",
  "What's the safest 5-12 upset to pick?",
  "Explain efficiency ratings in simple terms",
];

const BOT_RESPONSES: Record<string, string> = {
  "Who are RotoBot's Final Four picks?":
    "Based on current season data, RotoBot projects: **Auburn** (West), **Duke** (East), **Florida** (Midwest), and **Houston** (South). Auburn leads all teams with a 96 RotoBot Score and Johni Broome is the clear Naismith frontrunner. The Championship is projected to be Auburn vs Duke — a 58-42 edge to Auburn based on rebounding and schedule strength.",

  "Best upset to make in my bracket?":
    "🔥 RotoBot's #1 upset recommendation: **#12 UAB over #5 Purdue** (East Region). Eric Gaines' pressure defense disrupts Purdue's post-entry game, and UAB has 3 wins over Top-50 KenPom opponents this year. 5-12 upsets happen 35% of the time historically — this is one of the strongest 5-12 setups RotoBot has seen.",

  "Who is the best player in the tournament?":
    "RotoBot ranks the top 3 players by tournament impact score:\n\n1. **Johni Broome (Auburn)** — 19.1 PPG / 10.8 RPG, two-way dominance\n2. **Cooper Flagg (Duke)** — Projected #1 pick, 21.4 PPG / 8.2 RPG\n3. **Walter Clayton Jr. (Florida)** — Best PG in the country, 18.8 PPG / 5.8 APG\n\nBroome and Flagg are the most likely MVPs if their teams meet in the Final.",

  "Should I pick Auburn or Duke for the title?":
    "This is the matchup RotoBot has been modeling all season. **Auburn (58%)** is the slight edge because: (1) Superior rebounding (+4.1 margin) neutralizes Duke's transition game, (2) Johni Broome has a clear size advantage vs Duke's frontcourt, (3) Auburn is 15-0 on neutral courts this season.\n\nHowever, **Duke at 42%** is very live. Cooper Flagg can take over any game, and Duke's defensive rating is historically elite. This is genuinely a coin flip — pick your heart.",

  "What's the safest 5-12 upset to pick?":
    "**#12 UAB** vs **#5 Purdue** is the safest 5-12 upset in the bracket. Three reasons: (1) UAB has 3 wins over KenPom Top-50 teams, (2) their steals-and-press defense disrupts post-dominant teams, (3) 5-seeds from Big Ten who rely on interior scoring are historically vulnerable to athletic mid-majors.\n\nSecond option: **#12 Colorado** vs **#5 Oregon** in the South. KJ Simpson is healthy and Colorado has sneaky Big 12 wins.",

  "Explain efficiency ratings in simple terms":
    "Great question! Here's the breakdown:\n\n📊 **Adjusted Offensive Efficiency (AdjO)** = Points scored per 100 possessions, adjusted for competition. Think of it as 'how good is this offense against average opponents?' Higher = better.\n\n🛡️ **Adjusted Defensive Efficiency (AdjD)** = Points allowed per 100 possessions. Lower = better.\n\n⚡ **Pace** = Number of possessions per 40 minutes. High-pace teams take more shots but allow more for opponents too. In March, slow-pace teams often upset fast-pace ones.\n\n🎯 **eFG% (Effective Field Goal%)** = Shooting efficiency accounting for the fact that 3s are worth more than 2s. The most predictive single stat.",
};

function getResponse(message: string): string {
  const key = Object.keys(BOT_RESPONSES).find(k =>
    k.toLowerCase() === message.toLowerCase()
  );
  if (key) return BOT_RESPONSES[key];
  if (message.toLowerCase().includes("auburn")) return BOT_RESPONSES["Should I pick Auburn or Duke for the title?"];
  if (message.toLowerCase().includes("upset")) return BOT_RESPONSES["Best upset to make in my bracket?"];
  if (message.toLowerCase().includes("final four")) return BOT_RESPONSES["Who are RotoBot's Final Four picks?"];
  return `Great question about "${message}"! Based on RotoBot's analysis of 32 first-round games and full-season data across 361 teams, I can tell you that the 2025-26 tournament looks exceptionally competitive. Consider asking me about specific teams, upsets, or efficiency stats for more targeted analysis!`;
}

function renderBotText(text: string) {
  return text.split('\n').map((line, i) => (
    <p key={i} style={{ marginBottom: 6, lineHeight: 1.6 }}>
      {line.split(/\*\*(.*?)\*\*/).map((part, j) =>
        j % 2 === 1
          ? <strong key={j} style={{ color: "#00b8db" }}>{part}</strong>
          : part
      )}
    </p>
  ));
}

export function RotoBotScreen() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "bot",
      text: "Hey! I'm RotoBot — your AI March Madness assistant. I've analyzed all 64 projected tournament teams, calculated win probabilities for every possible matchup, and I'm ready to help you build the smartest bracket possible.\n\nWhat would you like to know?"
    }
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = (text: string) => {
    if (!text.trim()) return;
    const userMsg: Message = { role: "user", text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);
    setTimeout(() => {
      const botMsg: Message = { role: "bot", text: getResponse(text) };
      setMessages(prev => [...prev, botMsg]);
      setIsTyping(false);
    }, 800 + Math.random() * 600);
  };

  return (
    <div
      className="min-h-screen pt-16 pb-20 md:pb-8 flex flex-col"
      style={{ background: "linear-gradient(160deg, #010c2a 0%, #030712 40%, #00081e 100%)" }}
    >
      <div className="fixed pointer-events-none" style={{ top: "20%", left: "30%", width: 500, height: 400, background: "radial-gradient(ellipse, rgba(0,184,219,0.06) 0%, transparent 70%)" }} />

      <div className="max-w-3xl mx-auto w-full px-4 sm:px-6 py-6 flex flex-col flex-1 relative">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6 p-4 rounded-2xl" style={{ background: "rgba(0,184,219,0.05)", border: "1px solid rgba(0,184,219,0.15)" }}>
          <RotoBotLogo size={48} />
          <div>
            <h1 style={{ fontFamily: "Rubik, sans-serif", fontSize: 20, fontWeight: 800, color: "white" }}>
              RotoBot AI
            </h1>
            <div className="flex items-center gap-2 mt-0.5">
              <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "#22c55e" }} />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 12, color: "#22c55e" }}>
                Online • Processing 2,847 data points per game
              </span>
            </div>
          </div>
          <div className="ml-auto flex flex-col gap-1.5 text-right hidden sm:flex">
            <div className="flex items-center gap-2 justify-end">
              <Trophy size={11} color="#f59e0b" />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>64 Teams Tracked</span>
            </div>
            <div className="flex items-center gap-2 justify-end">
              <Target size={11} color="#00b8db" />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>74.2% 2024 Accuracy</span>
            </div>
            <div className="flex items-center gap-2 justify-end">
              <TrendingUp size={11} color="#22c55e" />
              <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.4)" }}>32 Upsets Flagged</span>
            </div>
          </div>
        </div>

        {/* Quick prompts */}
        <div className="mb-4">
          <span style={{ fontFamily: "Rubik, sans-serif", fontSize: 11, color: "rgba(255,255,255,0.3)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Quick questions
          </span>
          <div className="flex flex-wrap gap-2 mt-2">
            {QUICK_PROMPTS.map(p => (
              <button
                key={p}
                onClick={() => sendMessage(p)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full transition-all hover:opacity-80"
                style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  fontFamily: "Rubik, sans-serif",
                  fontSize: 12,
                  color: "rgba(255,255,255,0.65)",
                  cursor: "pointer",
                }}
              >
                <Zap size={10} color="#00b8db" />
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Messages */}
        <div
          className="flex-1 flex flex-col gap-4 overflow-y-auto mb-4 pr-1"
          style={{ minHeight: 0, maxHeight: "50vh" }}
        >
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              {msg.role === "bot" && <RotoBotLogo size={32} className="shrink-0 mt-1" />}
              <div
                className="max-w-[85%] rounded-2xl px-4 py-3"
                style={{
                  background: msg.role === "bot"
                    ? "rgba(0,184,219,0.07)"
                    : "rgba(60,132,255,0.15)",
                  border: msg.role === "bot"
                    ? "1px solid rgba(0,184,219,0.15)"
                    : "1px solid rgba(60,132,255,0.25)",
                }}
              >
                <div style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: "rgba(255,255,255,0.85)", lineHeight: 1.6 }}>
                  {msg.role === "bot" ? renderBotText(msg.text) : msg.text}
                </div>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex gap-3">
              <RotoBotLogo size={32} className="shrink-0 mt-1" />
              <div
                className="px-4 py-3 rounded-2xl flex items-center gap-1.5"
                style={{ background: "rgba(0,184,219,0.07)", border: "1px solid rgba(0,184,219,0.15)" }}
              >
                {[0, 1, 2].map(i => (
                  <div
                    key={i}
                    className="w-1.5 h-1.5 rounded-full animate-bounce"
                    style={{ background: "#00b8db", animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div
          className="flex items-center gap-3 p-3 rounded-2xl"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)" }}
        >
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendMessage(input)}
            placeholder="Ask RotoBot anything about the bracket..."
            className="flex-1 bg-transparent outline-none"
            style={{ fontFamily: "Rubik, sans-serif", fontSize: 14, color: "white" }}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim()}
            className="w-9 h-9 rounded-xl flex items-center justify-center transition-all hover:opacity-80 disabled:opacity-40"
            style={{
              background: input.trim() ? "linear-gradient(135deg, #00b8db, #3c84ff)" : "rgba(255,255,255,0.1)",
              border: "none",
              cursor: input.trim() ? "pointer" : "not-allowed",
            }}
          >
            <Send size={14} color="white" />
          </button>
        </div>
        <p className="text-center mt-2" style={{ fontFamily: "Rubik, sans-serif", fontSize: 10, color: "rgba(255,255,255,0.2)" }}>
          RotoBot uses projected 2025–26 season data. Bracket seeds are unofficial until Selection Sunday.
        </p>
      </div>
    </div>
  );
}
