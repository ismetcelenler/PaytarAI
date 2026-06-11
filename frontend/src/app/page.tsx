"use client";

import { useRouter } from "next/navigation";
import { Stethoscope, Wheat } from "lucide-react";
import { PaytarMark, HolsteinHead } from "@/components/paytar/brand";

export default function HomePage() {
  const router = useRouter();

  const pick = (role: "vet" | "producer") => {
    localStorage.setItem("paytar_role", role);
    router.push(`/${role}`);
  };

  return (
    <main className="flex-1 flex items-center justify-center bg-paytar-bg p-6 font-sans">
      <div className="w-full max-w-3xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-paytar-accent text-paytar-surface mb-5 shadow-[0_4px_0_rgba(61,90,44,0.18)]">
            <PaytarMark size={34} />
          </div>
          <h1 className="font-serif text-5xl text-paytar-ink tracking-tight">
            paytar<span className="italic text-paytar-accent-ink">AI</span>
          </h1>
          <p className="font-sans text-base text-paytar-ink2 mt-3 max-w-md mx-auto leading-relaxed">
            Büyükbaş hayvan sağlığı için kanıt tabanlı veteriner karar destek
            asistanı.
          </p>
          <p className="font-mono text-[10px] tracking-widest uppercase text-paytar-muted mt-2">
            ÇAYIR · 2026.Q1
          </p>
        </div>

        {/* Role cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <RoleCard
            id="role-select-vet"
            icon={<Stethoscope className="w-7 h-7" />}
            title="Veteriner Hekim"
            description="Teknik terminoloji, mg/kg dozaj hesabı, kontrendikasyon ve literatür referansları."
            tags={["Dozaj hesabı", "Kaynak referansları", "Klinik karar"]}
            onClick={() => pick("vet")}
          />
          <RoleCard
            id="role-select-producer"
            icon={<Wheat className="w-7 h-7" />}
            title="Hayvancılık Üreticisi"
            description="Sade Türkçe ile hayvanında ne olduğunu anla, ne zaman veteriner çağıracağını öğren."
            tags={["Semptom rehberi", "Sade Türkçe", "Acil yönlendirme"]}
            onClick={() => pick("producer")}
          />
        </div>

        {/* Footer + cow */}
        <div className="flex flex-col items-center mt-12">
          <HolsteinHead size={48} className="text-paytar-muted opacity-50 mb-3" />
          <p className="font-mono text-[10px] tracking-widest uppercase text-paytar-muted">
            Karar destek sağlar · kesin tanı koymaz
          </p>
        </div>
      </div>
    </main>
  );
}

interface RoleCardProps {
  id: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  tags: string[];
  onClick: () => void;
}

function RoleCard({ id, icon, title, description, tags, onClick }: RoleCardProps) {
  return (
    <button
      id={id}
      onClick={onClick}
      className="group relative overflow-hidden rounded-2xl border border-paytar-line bg-paytar-surface p-7 text-left transition-all duration-300 hover:border-paytar-accent hover:-translate-y-0.5 hover:shadow-[0_12px_24px_-16px_rgba(45,42,36,0.25)] focus:outline-none focus:ring-2 focus:ring-paytar-accent focus:ring-offset-2 focus:ring-offset-paytar-bg"
    >
      <div className="absolute top-0 right-0 w-32 h-32 bg-paytar-accent-soft rounded-bl-[80px] transition-all duration-300 group-hover:bg-paytar-accent-soft/80" />
      <div className="relative">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-paytar-accent-soft text-paytar-accent-ink mb-5 transition-colors group-hover:bg-paytar-accent group-hover:text-paytar-surface">
          {icon}
        </div>
        <h2 className="font-serif text-2xl text-paytar-ink tracking-tight mb-2">
          {title}
        </h2>
        <p className="font-sans text-sm text-paytar-ink2 leading-relaxed mb-4">
          {description}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {tags.map((t) => (
            <span
              key={t}
              className="font-mono text-[10px] tracking-wider uppercase rounded-full bg-paytar-surface2 px-2.5 py-1 text-paytar-accent-ink border border-paytar-line"
            >
              {t}
            </span>
          ))}
        </div>
      </div>
    </button>
  );
}
