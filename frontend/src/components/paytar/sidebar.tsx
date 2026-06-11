"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ArrowLeft, Plus, Search } from "lucide-react";
import { PaytarMark, PaytarWordmark } from "./brand";
import { notYetImplemented } from "@/lib/paytar";

interface HistoryEntry {
  id: string;
  title: string;
  when: string;
}

interface PaytarSidebarProps {
  subtitle: string;
  userName: string;
  userInitial: string;
  userMeta: string;
  history: HistoryEntry[];
  activeId?: string;
  onNewChat: () => void;
}

export function PaytarSidebar({
  subtitle,
  userName,
  userInitial,
  userMeta,
  history,
  activeId,
  onNewChat,
}: PaytarSidebarProps) {
  const grouped = useMemo(() => {
    const out: Record<string, HistoryEntry[]> = {};
    for (const h of history) {
      (out[h.when] ||= []).push(h);
    }
    return out;
  }, [history]);

  return (
    <aside className="hidden md:flex w-[280px] flex-shrink-0 h-full flex-col bg-paytar-sidebar border-r border-paytar-line px-[18px] py-[22px]">
      {/* logo + back */}
      <div className="flex items-center gap-3 mb-6 pl-1">
        <Link
          href="/"
          aria-label="Geri"
          className="w-7 h-7 rounded-md flex items-center justify-center text-paytar-muted hover:bg-paytar-surface2 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="w-8 h-8 rounded-lg bg-paytar-accent flex items-center justify-center text-paytar-surface flex-shrink-0">
          <PaytarMark size={20} />
        </div>
        <PaytarWordmark subtitle={subtitle} />
      </div>

      {/* new chat */}
      <button
        onClick={onNewChat}
        className="flex items-center justify-between w-full px-3.5 py-2.5 rounded-full bg-paytar-accent text-paytar-surface text-sm font-medium mb-5 hover:opacity-95 transition-opacity shadow-[0_2px_0_rgba(61,90,44,0.25)]"
      >
        <span>Yeni sohbet</span>
        <Plus className="w-4 h-4" />
      </button>

      {/* search (TODO) */}
      <button
        onClick={() => notYetImplemented("Vakalarda arama")}
        className="flex items-center gap-2 w-full px-3 py-2 rounded-lg bg-paytar-surface2 border border-paytar-line mb-4 hover:bg-paytar-surface transition-colors text-left"
      >
        <Search className="w-3.5 h-3.5 text-paytar-muted flex-shrink-0" />
        <span className="font-sans text-xs text-paytar-muted">Vakalarda ara…</span>
      </button>

      {/* history */}
      <div className="flex-1 overflow-y-auto -mx-1.5">
        {Object.entries(grouped).map(([when, items]) => (
          <div key={when} className="mb-3.5">
            <div className="font-mono text-[9.5px] text-paytar-muted tracking-widest px-2.5 pb-1.5 uppercase">
              {when}
            </div>
            {items.map((h) => (
              <button
                key={h.id}
                onClick={() => notYetImplemented("Vaka geçmişi")}
                className={`block w-full text-left px-2.5 py-1.5 my-px rounded-md text-[13px] leading-snug truncate transition-colors ${
                  h.id === activeId
                    ? "bg-paytar-surface2 text-paytar-ink"
                    : "text-paytar-ink2 hover:bg-paytar-surface2/60"
                }`}
              >
                {h.title}
              </button>
            ))}
          </div>
        ))}
      </div>

      {/* user pill */}
      <div className="flex items-center gap-2.5 pt-2.5 pb-1 mt-2 border-t border-paytar-line">
        <div className="w-7 h-7 rounded-full bg-paytar-surface2 border border-paytar-line flex items-center justify-center font-serif text-sm text-paytar-ink">
          {userInitial}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] text-paytar-ink leading-tight">{userName}</div>
          <div className="font-mono text-[9.5px] text-paytar-muted mt-0.5 tracking-wider">
            {userMeta}
          </div>
        </div>
        <div className="w-1.5 h-1.5 rounded-full bg-paytar-accent" />
      </div>
    </aside>
  );
}
