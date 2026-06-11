/**
 * PaytarAI marka isaretleri (Çayır vizyonu).
 * - PaytarMark: "p" monogram, sidebar/avatar icin.
 * - HolsteinHead: empty-state illustration.
 */

interface IconProps {
  size?: number;
  className?: string;
}

export function PaytarMark({ size = 28, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      stroke="currentColor"
      strokeWidth={10}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M30 22 Q22 16 28 8" strokeWidth={5.5} />
      <path d="M30 86 L30 30 L58 30 A16 16 0 1 1 58 62 L40 62" />
    </svg>
  );
}

export function HolsteinHead({ size = 88, className }: IconProps) {
  return (
    <svg
      width={size}
      height={size * 0.86}
      viewBox="0 0 140 120"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M52 28 Q44 14 36 16 Q32 18 36 22" />
      <path d="M88 28 Q96 14 104 16 Q108 18 104 22" />
      <path d="M40 32 Q18 38 22 58 Q26 64 38 56" />
      <path d="M100 32 Q122 38 118 58 Q114 64 102 56" />
      <path d="M44 36 Q44 24 70 24 Q96 24 96 36 L94 62 Q92 76 84 84 L80 96 Q70 102 60 96 L56 84 Q48 76 46 62 Z" />
      <path
        d="M62 36 Q70 32 78 36 Q74 44 70 44 Q66 44 62 36 Z"
        fill="currentColor"
        stroke="none"
        opacity="0.18"
      />
      <ellipse cx="58" cy="52" rx="1.6" ry="2.2" fill="currentColor" stroke="none" />
      <ellipse cx="82" cy="52" rx="1.6" ry="2.2" fill="currentColor" stroke="none" />
      <path d="M54 78 Q70 84 86 78" />
      <ellipse cx="64" cy="80" rx="1" ry="1.6" fill="currentColor" stroke="none" />
      <ellipse cx="76" cy="80" rx="1" ry="1.6" fill="currentColor" stroke="none" />
    </svg>
  );
}

/** paytarAI wordmark — Instrument Serif italic */
export function PaytarWordmark({ subtitle }: { subtitle?: string }) {
  return (
    <div className="flex flex-col">
      <div className="font-serif text-[19px] leading-none tracking-tight text-paytar-ink">
        paytar
        <span className="italic text-paytar-accent-ink">AI</span>
      </div>
      {subtitle && (
        <div className="font-mono text-[9px] mt-[3px] tracking-widest text-paytar-muted uppercase">
          {subtitle}
        </div>
      )}
    </div>
  );
}
