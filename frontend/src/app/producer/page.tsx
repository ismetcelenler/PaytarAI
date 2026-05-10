"use client";

import { useState } from "react";
import { Send, Mic, Wheat, ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

/* AI-PROMPT.md Section 5.1 — Semptom Kategorileri */
const SYMPTOM_CATEGORIES = [
  { id: "digestive", label: "Sindirim Sorunu", icon: "\ud83e\udec1", examples: ["Siskinlik", "Ishal", "Yemek yememe"] },
  { id: "respiratory", label: "Solunum Sorunu", icon: "\ud83d\udca8", examples: ["Oksuruk", "Burun akintisi", "Nefes darligi"] },
  { id: "limb", label: "Ayak / Hareket", icon: "\ud83e\uddb5", examples: ["Topallama", "Sislik", "Yurumeme"] },
  { id: "skin", label: "Deri / Yara", icon: "\ud83e\ude79", examples: ["Yara", "Sislik", "Dokuntu"] },
  { id: "milk", label: "Sut Sorunu", icon: "\ud83e\udd5b", examples: ["Sut azaldi", "Sut rengi degisti", "Meme sisligi"] },
  { id: "birth", label: "Dogum / Yavru", icon: "\ud83d\udc04", examples: ["Dogum zorlugu", "Plasenta atmama", "Yavru emmeme"] },
  { id: "general", label: "Genel Durum", icon: "\ud83c\udf21\ufe0f", examples: ["Ates", "Halsizlik", "Suruden ayrilma"] },
  { id: "eye", label: "Goz Sorunu", icon: "\ud83d\udc41\ufe0f", examples: ["Goz akintisi", "Goz kizarikligi", "Gormeme"] },
];

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export default function ProducerDashboard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showSymptomGuide, setShowSymptomGuide] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const handleSymptomSelect = (categoryId: string, example: string) => {
    const cat = SYMPTOM_CATEGORIES.find((c) => c.id === categoryId);
    const query = `Hayvanimin ${cat?.label.toLowerCase()} var: ${example}`;
    setShowSymptomGuide(false);
    setInput("");

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
      timestamp: new Date(),
    };
    setMessages([userMsg]);
    sendMessage(query);
  };

  const sendMessage = async (text: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            user_role: "producer",
            input_source: "text",
          }),
        }
      );
      const data = await res.json();

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Baglanti hatasi. Sunucunun calistigini kontrol edin.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    const text = input;
    setInput("");
    sendMessage(text);
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border px-4 py-3 flex items-center gap-3 bg-paytar-green">
        <Wheat className="w-6 h-6 text-white" />
        <h1 className="text-lg font-semibold text-white">PaytarAI</h1>
        <Badge className="bg-white/20 text-white border-white/30 text-xs">
          Uretici Modu
        </Badge>
        {!showSymptomGuide && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto text-white hover:bg-white/10"
            onClick={() => {
              setShowSymptomGuide(true);
              setSelectedCategory(null);
            }}
          >
            <ArrowLeft className="w-4 h-4 mr-1" />
            Semptom Rehberi
          </Button>
        )}
      </header>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {showSymptomGuide ? (
          /* Symptom Guide — AI-PROMPT.md Section 5.1 */
          <ScrollArea className="flex-1 p-6">
            <div className="max-w-lg mx-auto">
              <h2 className="text-lg font-medium text-paytar-green-dark mb-2">
                Hayvaninda ne goruyorsun?
              </h2>
              <p className="text-sm text-muted-foreground mb-6">
                Bir kategori sec, sonra detay ekleyebilirsin.
              </p>

              <div className="grid grid-cols-2 gap-3">
                {SYMPTOM_CATEGORIES.map((cat) => (
                  <button
                    key={cat.id}
                    id={`symptom-${cat.id}`}
                    onClick={() =>
                      setSelectedCategory(
                        selectedCategory === cat.id ? null : cat.id
                      )
                    }
                    className={`min-h-[48px] p-3 rounded-xl border text-left transition-all duration-200 ${
                      selectedCategory === cat.id
                        ? "border-paytar-green bg-paytar-sage shadow-sm"
                        : "border-gray-200 bg-white hover:border-paytar-green hover:shadow-sm"
                    }`}
                  >
                    <span className="text-2xl">{cat.icon}</span>
                    <span className="block text-sm font-medium mt-1">
                      {cat.label}
                    </span>
                    <span className="block text-xs text-muted-foreground mt-0.5">
                      {cat.examples.join(" \u00b7 ")}
                    </span>
                  </button>
                ))}
              </div>

              {/* Detail Step */}
              {selectedCategory && (
                <div className="mt-6 p-4 bg-paytar-sage/30 rounded-xl border border-paytar-green/20">
                  <p className="text-sm font-medium text-paytar-green-dark mb-3">
                    Hangi belirtiyi goruyorsun?
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {SYMPTOM_CATEGORIES.find(
                      (c) => c.id === selectedCategory
                    )?.examples.map((ex) => (
                      <button
                        key={ex}
                        onClick={() =>
                          handleSymptomSelect(selectedCategory, ex)
                        }
                        className="px-4 py-2 rounded-full bg-white border border-paytar-green/30 text-sm text-paytar-green-dark hover:bg-paytar-green hover:text-white transition-colors min-h-[44px]"
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        ) : (
          /* Chat Feed */
          <ScrollArea className="flex-1 p-6">
            <div className="space-y-4 max-w-lg mx-auto">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-paytar-green text-white"
                        : "bg-muted border border-border"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted border border-border rounded-2xl px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-paytar-green/40 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-paytar-green/40 rounded-full animate-bounce [animation-delay:0.15s]" />
                      <span className="w-2 h-2 bg-paytar-green/40 rounded-full animate-bounce [animation-delay:0.3s]" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          </ScrollArea>
        )}

        {/* Input Area (always visible) */}
        <div className="border-t border-border p-4 bg-background">
          <div className="max-w-lg mx-auto flex gap-3 items-end">
            <Button
              id="producer-voice-btn"
              variant="outline"
              size="icon"
              className="min-w-[56px] min-h-[56px] rounded-full border-paytar-green/30 text-paytar-green hover:bg-paytar-green hover:text-white transition-colors"
              title="Sesli komut"
            >
              <Mic className="w-6 h-6" />
            </Button>
            <Textarea
              id="producer-chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Sorunuzu yazin..."
              className="min-h-[48px] max-h-[100px] resize-none"
              rows={1}
            />
            <Button
              id="producer-send-btn"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="min-w-[48px] min-h-[48px] rounded-full bg-paytar-green hover:bg-paytar-green-dark transition-colors"
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
