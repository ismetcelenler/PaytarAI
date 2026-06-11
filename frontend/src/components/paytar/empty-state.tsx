"use client";

import { HolsteinHead } from "./brand";

interface SuggestedPrompt {
  tag: string;
  q: string;
}

interface EmptyStateProps {
  greetingName: string;
  description: string;
  suggested: SuggestedPrompt[];
  onPick: (q: string) => void;
}

export function PaytarEmptyState({
  greetingName,
  description,
  suggested,
  onPick,
}: EmptyStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 md:px-10 text-center">
      <div className="mb-7 text-paytar-accent opacity-90">
        <HolsteinHead size={96} />
      </div>
      <h2 className="font-serif text-3xl md:text-4xl leading-tight text-paytar-ink tracking-tight mb-1.5">
        İyi günler,{" "}
        <span className="italic text-paytar-accent-ink">{greetingName}</span>
      </h2>
      <p className="font-sans text-[15px] text-paytar-muted mb-8 max-w-md leading-relaxed">
        {description}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 w-full max-w-xl">
        {suggested.map((s, i) => (
          <button
            key={i}
            onClick={() => onPick(s.q)}
            className="flex flex-col items-start gap-1.5 px-4 py-3.5 bg-paytar-surface border border-paytar-line rounded-xl text-left hover:border-paytar-accent/40 hover:bg-paytar-surface/80 transition-colors"
          >
            <span className="font-mono text-[9.5px] text-paytar-accent-ink tracking-widest uppercase">
              {s.tag}
            </span>
            <span className="font-sans text-sm text-paytar-ink leading-snug">
              {s.q}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
