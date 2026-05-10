"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic, Stethoscope, BookOpen, Shield, ArrowLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import ReactMarkdown from "react-markdown";
import Link from "next/link";

interface Source {
  title: string;
  score: number;
  snippet: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  confidence?: string;
  sources?: Source[];
  criticAttempts?: number;
  auditCount?: number;
}

const CONFIDENCE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  high: { bg: "bg-emerald-100 border-emerald-300", text: "text-emerald-800", label: "Yuksek Guven" },
  medium: { bg: "bg-amber-100 border-amber-300", text: "text-amber-800", label: "Orta Guven" },
  low: { bg: "bg-orange-100 border-orange-300", text: "text-orange-800", label: "Dusuk Guven" },
  insufficient: { bg: "bg-red-100 border-red-300", text: "text-red-800", label: "Yetersiz Kanit" },
};

export default function VetDashboard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    const text = input;
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            user_role: "veterinarian",
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
        confidence: data.evidence_confidence,
        sources: data.sources,
        criticAttempts: data.critic_attempts,
        auditCount: data.audit_entry_count,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Backend baglantisi kurulamadi. Sunucunun calistigini kontrol edin.",
        timestamp: new Date(),
        confidence: "insufficient",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Left Panel — Sidebar */}
      <aside className="w-72 border-r border-border bg-muted/30 p-4 flex flex-col gap-4">
        <div className="flex items-center gap-2 mb-2">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <ArrowLeft className="w-4 h-4 text-muted-foreground" />
          </Link>
          <Stethoscope className="w-5 h-5 text-paytar-green" />
          <h2 className="font-semibold text-paytar-green-dark">Veteriner Modu</h2>
        </div>
        <Separator />

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Hayvan Profili</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Kulak No:</span>
              <span className="font-medium">—</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Irk:</span>
              <span className="font-medium">—</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Yas:</span>
              <span className="font-medium">—</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Agirlik (kg):</span>
              <span className="font-medium">—</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Sistem Durumu</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">Backend:</span>
              <Badge variant="outline" className="text-xs bg-paytar-sage/30 text-paytar-green-dark border-paytar-green/30">
                Aktif
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">LangGraph:</span>
              <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                Calisiyor
              </Badge>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-muted-foreground">RAG:</span>
              <Badge variant="outline" className="text-xs bg-emerald-50 text-emerald-700 border-emerald-200">
                20 chunk
              </Badge>
            </div>
          </CardContent>
        </Card>
      </aside>

      {/* Center Panel — Chat Feed */}
      <main className="flex-1 flex flex-col">
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-6">
          {messages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-paytar-green/10 mb-4">
                  <Stethoscope className="w-8 h-8 text-paytar-green" />
                </div>
                <h3 className="text-lg font-medium text-foreground mb-2">
                  Veteriner Karar Destek
                </h3>
                <p className="text-sm text-muted-foreground max-w-md">
                  Klinik bulgulari veya ilac adini yazin. Sistem kanit tabanli
                  literatur verileriyle destek saglayacaktir.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4 max-w-3xl mx-auto">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-5 py-4 ${
                      msg.role === "user"
                        ? "bg-paytar-green text-white"
                        : "bg-muted border border-border"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      <div className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-paytar-green-dark prose-strong:text-foreground prose-li:text-foreground">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    )}

                    {/* Confidence + Metadata Badges */}
                    {msg.confidence && (
                      <div className="mt-3 pt-3 border-t border-border/50 flex flex-wrap gap-2">
                        <Badge
                          variant="outline"
                          className={`text-xs ${CONFIDENCE_STYLES[msg.confidence]?.bg || ""} ${CONFIDENCE_STYLES[msg.confidence]?.text || ""}`}
                        >
                          <Shield className="w-3 h-3 mr-1" />
                          {CONFIDENCE_STYLES[msg.confidence]?.label || msg.confidence}
                        </Badge>
                        {msg.criticAttempts !== undefined && msg.criticAttempts > 0 && (
                          <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 border-blue-200">
                            {msg.criticAttempts} Critic retry
                          </Badge>
                        )}
                      </div>
                    )}

                    {/* Source Cards */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {msg.sources.map((src, i) => (
                          <div
                            key={i}
                            className="flex items-start gap-2 p-2 rounded-lg bg-background/60 border border-border/50"
                          >
                            <BookOpen className="w-4 h-4 text-paytar-green mt-0.5 flex-shrink-0" />
                            <div className="min-w-0">
                              <p className="text-xs font-medium text-foreground truncate">
                                {src.title}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                Skor: {src.score.toFixed(2)}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted border border-border rounded-2xl px-5 py-4">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 bg-paytar-green/40 rounded-full animate-bounce" />
                        <span className="w-2 h-2 bg-paytar-green/40 rounded-full animate-bounce [animation-delay:0.15s]" />
                        <span className="w-2 h-2 bg-paytar-green/40 rounded-full animate-bounce [animation-delay:0.3s]" />
                      </div>
                      <span className="text-xs text-muted-foreground ml-2">Analiz ediliyor...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-border p-4 bg-background">
          <div className="max-w-3xl mx-auto flex gap-3 items-end">
            <Textarea
              id="vet-chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Klinik bulgulari veya ilac adini yazin..."
              className="min-h-[48px] max-h-[120px] resize-none"
              rows={1}
            />
            <Button
              id="vet-voice-btn"
              variant="outline"
              size="icon"
              className="min-w-[48px] min-h-[48px] rounded-full border-paytar-green/30 text-paytar-green hover:bg-paytar-green hover:text-white transition-colors"
              title="Sesli komut"
            >
              <Mic className="w-5 h-5" />
            </Button>
            <Button
              id="vet-send-btn"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="min-w-[48px] min-h-[48px] rounded-full bg-paytar-green hover:bg-paytar-green-dark transition-colors"
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
