/**
 * PaytarAI — Evidence Highlight Matcher
 *
 * Chunk metni icinde judge'in birebir alintisini (evidence) bulup highlight
 * edilecek karakter araligini doner. Hem ana chat (message.tsx) hem test
 * paneli (test/page.tsx) AYNI fonksiyonu kullanir — davranis senkron kalsin.
 *
 * Tasarim: "yanlis yesil"den kacin. Eski findBestMatch 2 kelime eslesince
 * +80 karakter boyuyordu; bu alakasiz bolgeleri yesile cektigi icin kaldirildi.
 * Burada her eslesme TAM olarak eslesen araligi boyar:
 *   1) Tam substring (birebir).
 *   2) Normalize substring (kucuk harf + noktalama/bosluk farklarini yok say),
 *      orijinal metindeki karsiligini geri haritala.
 *   3) Kelime-dizisi: evidence'in sonundan kelime atarak en uzun ardisik
 *      eslesmeyi bul (judge alintiyi hafifce parafraz etmis olabilir).
 *      Esik: en az 4 kelime ya da kelimelerin %60'i. Altinda eslesme = null.
 *   4) Hicbiri yoksa null → highlight YOK (yanlis yesilden iyidir).
 */

const WORD_CHAR = /[A-Za-z0-9ğüşıöçĞÜŞİÖÇ]/;

/**
 * Metni normalize ederken her normalize karakterinin ORIJINAL index'ini tutan
 * bir harita uretir. Boylece normalize uzayda bulunan eslesme, orijinal metne
 * birebir geri yansitilabilir.
 */
function normalizeWithMap(text: string): { norm: string; map: number[] } {
  let norm = "";
  const map: number[] = [];
  let prevSpace = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (WORD_CHAR.test(ch)) {
      norm += ch.toLowerCase();
      map.push(i);
      prevSpace = false;
    } else if (!prevSpace && norm.length > 0) {
      norm += " ";
      map.push(i);
      prevSpace = true;
    }
  }
  // Sondaki bosluk varsa kirp (eslesme sonunu sasirtmasin)
  if (norm.endsWith(" ")) {
    norm = norm.slice(0, -1);
    map.pop();
  }
  return { norm, map };
}

function normalizeText(text: string): string {
  return normalizeWithMap(text).norm;
}

/**
 * `evidence`'in `text` icindeki en iyi eslesme araligini doner, yoksa null.
 * Donen [start, end] orijinal `text` karakter offset'leridir.
 */
export function findEvidenceRange(
  text: string,
  evidence: string,
): [number, number] | null {
  const needle = evidence.trim();
  if (!needle || !text) return null;

  // 1) Tam substring
  const exact = text.indexOf(needle);
  if (exact >= 0) return [exact, exact + needle.length];

  // 2) Normalize substring → orijinale geri haritala
  const { norm: hNorm, map } = normalizeWithMap(text);
  const nNorm = normalizeText(needle);
  if (nNorm.length < 8) return null; // cok kisa evidence — guvenilmez

  const idx = hNorm.indexOf(nNorm);
  if (idx >= 0) {
    const start = map[idx];
    const end = map[idx + nNorm.length - 1] + 1;
    return [start, end];
  }

  // 3) Kelime-dizisi: sondan kelime atarak en uzun ardisik onek eslesmesi
  const words = nNorm.split(" ").filter(Boolean);
  const minWords = Math.max(4, Math.ceil(words.length * 0.6));
  for (let w = words.length - 1; w >= minWords; w--) {
    const sub = words.slice(0, w).join(" ");
    const i2 = hNorm.indexOf(sub);
    if (i2 >= 0) {
      const start = map[i2];
      const end = map[i2 + sub.length - 1] + 1;
      return [start, end];
    }
  }

  // 4) Eslesme yok
  return null;
}
