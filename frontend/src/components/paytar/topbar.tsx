"use client";

import Link from "next/link";
import { ArrowLeft, Menu } from "lucide-react";

interface PaytarTopBarProps {
  title: string;
  meta: string;
  modelTag?: string;
  online?: boolean;
  /** Mobil: sidebar toggle butonu */
  onMenuClick?: () => void;
}

export function PaytarTopBar({
  title,
  meta,
  modelTag = "PAYTAR-RAG · ÇEVRİMİÇİ",
  online = true,
  onMenuClick,
}: PaytarTopBarProps) {
  return (
    <div className="flex items-center justify-between px-5 md:px-7 py-3.5 border-b border-paytar-line bg-paytar-bg flex-shrink-0">
      <div className="flex items-center gap-3">
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className="md:hidden w-8 h-8 rounded-md flex items-center justify-center text-paytar-ink hover:bg-paytar-surface2"
            aria-label="Menü"
          >
            <Menu className="w-4 h-4" />
          </button>
        )}
        <Link
          href="/"
          aria-label="Geri"
          className="md:hidden w-8 h-8 rounded-md flex items-center justify-center text-paytar-muted hover:bg-paytar-surface2"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div>
          <div className="font-serif text-[17px] leading-tight text-paytar-ink tracking-tight">
            {title}
          </div>
          <div className="font-mono text-[10px] text-paytar-muted mt-0.5 tracking-wider">
            {meta}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 font-mono text-[10px] text-paytar-muted tracking-wider">
        <span
          className={`inline-block w-1.5 h-1.5 rounded-full ${
            online ? "bg-paytar-accent" : "bg-paytar-muted"
          }`}
        />
        <span className="hidden sm:inline">{modelTag}</span>
      </div>
    </div>
  );
}
