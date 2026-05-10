"use client";

import { useState } from "react";
import { Send, Mic, Stethoscope } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  confidence?: string;
  sources?: { title: string; page: number }[];
}

export default function VetDashboard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    // TODO (Faz 3): LangGraph SSE streaming entegrasyonu
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: input,
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
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Backend baglantisi kurulamadi. Sunucunun calistigini kontrol edin.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-background">
      {/* Left Panel — Animal Profile */}
      <aside className="w-72 border-r border-border bg-muted/30 p-4 flex flex-col gap-4">
        <div className="flex items-center gap-2 mb-2">
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
              <Badge variant="outline" className="text-xs">
                Faz 3
              </Badge>
            </div>
          </CardContent>
        </Card>
      </aside>

      {/* Center Panel — Chat Feed */}
      <main className="flex-1 flex flex-col">
        {/* Chat Messages */}
        <ScrollArea className="flex-1 p-6">
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
                    className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      msg.role === "user"
                        ? "bg-paytar-green text-white"
                        : "bg-muted border border-border"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    {msg.confidence && (
                      <div className="mt-2 flex gap-2">
                        <Badge
                          variant="outline"
                          className={`text-xs ${
                            msg.confidence === "high"
                              ? "bg-green-100 text-green-800 border-green-300"
                              : msg.confidence === "medium"
                              ? "bg-yellow-100 text-yellow-800 border-yellow-300"
                              : "bg-red-100 text-red-800 border-red-300"
                          }`}
                        >
                          Guven: {msg.confidence}
                        </Badge>
                      </div>
                    )}
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
          )}
        </ScrollArea>

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
