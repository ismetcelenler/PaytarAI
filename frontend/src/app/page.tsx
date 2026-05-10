"use client";

import { useRouter } from "next/navigation";
import { Stethoscope, Wheat } from "lucide-react";

export default function HomePage() {
  const router = useRouter();

  const handleRoleSelect = (role: "vet" | "producer") => {
    localStorage.setItem("paytar_role", role);
    router.push(`/${role}`);
  };

  return (
    <main className="flex-1 flex items-center justify-center bg-gradient-to-br from-white via-paytar-sage-light to-paytar-cream-light p-4">
      <div className="w-full max-w-3xl">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-paytar-green mb-6 shadow-lg shadow-paytar-green/20">
            <span className="text-4xl text-white font-bold">P</span>
          </div>
          <h1 className="text-4xl font-bold text-paytar-green-dark tracking-tight">
            PaytarAI
          </h1>
          <p className="text-lg text-muted-foreground mt-3 max-w-md mx-auto">
            Veteriner Karar Destek Asistani
          </p>
          <p className="text-sm text-muted-foreground/70 mt-1">
            Kanit tabanli, guvenilir buyukbas hayvan sagligi destek sistemi
          </p>
        </div>

        {/* Role Selection Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Veteriner Hekim Card */}
          <button
            id="role-select-vet"
            onClick={() => handleRoleSelect("vet")}
            className="group relative overflow-hidden rounded-2xl border-2 border-transparent bg-white p-8 text-left shadow-md transition-all duration-300 hover:border-paytar-green hover:shadow-xl hover:shadow-paytar-green/10 hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-paytar-green focus:ring-offset-2"
          >
            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-paytar-sage/30 rounded-bl-[80px] transition-all duration-300 group-hover:bg-paytar-sage/50" />

            <div className="relative">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-paytar-green/10 text-paytar-green mb-5 transition-colors group-hover:bg-paytar-green group-hover:text-white">
                <Stethoscope className="w-7 h-7" />
              </div>

              <h2 className="text-xl font-semibold text-foreground mb-2">
                Veteriner Hekim
              </h2>

              <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                Teknik terminoloji, mg/kg dozaj hesabi, kontrendikasyon listeleri
                ve literatur referanslari ile profesyonel karar destegi.
              </p>

              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center rounded-full bg-paytar-sage/50 px-3 py-1 text-xs font-medium text-paytar-green-dark">
                  Dozaj Hesabi
                </span>
                <span className="inline-flex items-center rounded-full bg-paytar-sage/50 px-3 py-1 text-xs font-medium text-paytar-green-dark">
                  Kaynak Referanslari
                </span>
                <span className="inline-flex items-center rounded-full bg-paytar-sage/50 px-3 py-1 text-xs font-medium text-paytar-green-dark">
                  Sesli Komut
                </span>
              </div>
            </div>
          </button>

          {/* Uretici Card */}
          <button
            id="role-select-producer"
            onClick={() => handleRoleSelect("producer")}
            className="group relative overflow-hidden rounded-2xl border-2 border-transparent bg-white p-8 text-left shadow-md transition-all duration-300 hover:border-paytar-green hover:shadow-xl hover:shadow-paytar-green/10 hover:-translate-y-1 focus:outline-none focus:ring-2 focus:ring-paytar-green focus:ring-offset-2"
          >
            {/* Background decoration */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-paytar-cream/50 rounded-bl-[80px] transition-all duration-300 group-hover:bg-paytar-sage/50" />

            <div className="relative">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-paytar-green/10 text-paytar-green mb-5 transition-colors group-hover:bg-paytar-green group-hover:text-white">
                <Wheat className="w-7 h-7" />
              </div>

              <h2 className="text-xl font-semibold text-foreground mb-2">
                Hayvancilik Ureticisi
              </h2>

              <p className="text-sm text-muted-foreground leading-relaxed mb-4">
                Sade ve anlasilir Turkce ile hayvaninizda ne oldugunu anlayin,
                ne zaman veteriner cagiracaginizi ogrenin.
              </p>

              <div className="flex flex-wrap gap-2">
                <span className="inline-flex items-center rounded-full bg-paytar-cream/70 px-3 py-1 text-xs font-medium text-paytar-green-dark">
                  Semptom Rehberi
                </span>
                <span className="inline-flex items-center rounded-full bg-paytar-cream/70 px-3 py-1 text-xs font-medium text-paytar-green-dark">
                  Sade Turkce
                </span>
                <span className="inline-flex items-center rounded-full bg-paytar-cream/70 px-3 py-1 text-xs font-medium text-paytar-green-dark">
                  Sesli Komut
                </span>
              </div>
            </div>
          </button>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground/60 mt-8">
          Bu sistem karar destegi saglar, kesin tani koymaz.
        </p>
      </div>
    </main>
  );
}
