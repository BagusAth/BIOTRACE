// Kontrak data biotrace.report.v1 (dibangkitkan oleh biotrace/dto.py).
// Nama kolom mengikuti istilah PRD agar mudah ditelusuri ke tabel klaim.

export const DECISIONS = ["aman dilaporkan", "dengan catatan", "wajib verifikasi", "jangan dipakai"] as const;
export type Decision = (typeof DECISIONS)[number];
export type Grade = "A" | "B" | "C" | "D";
export type Level = "spesies" | "genus" | "famili" | "tidak dikenal";
export type CauseCode = "referensi" | "marker" | "sampel" | "lokasi";
export type Lang = "id" | "en";

export interface ReportMeta {
  proyek: string;
  judul: string;
  simulasi: boolean;
  mode: string;
  marker: string[];
  jumlah_stasiun: number;
  replikat_per_stasiun: string;
  jumlah_sampel: number;
  jumlah_kontrol: number;
  jumlah_klaim: number;
  jumlah_asv: number;
  diproses: string | null;
  durasi_detik: number;
  referensi: { label: string; nama: string; versi: string; jenis: string; wilayah: string };
  aturan: { versi: string; label: string };
  aplikasi: string;
  sidik_jari: string;
  kalibrasi_galat: string;
  batas_interpretasi: Record<Lang, string>;
}

export interface Summary {
  kalimat: string;
  jumlah: Record<Decision | "n" | "tidak dikenal", number>;
  tindak_lanjut: Record<Decision, string>;
  tidak_dikenal_ke_barcode: number;
}

export interface CauseCount {
  kode: string;
  label: string;
  petunjuk: string;
  jumlah: number;
}

export interface InputFile {
  nama: string;
  peran: string;
  deskripsi: string;
  sha256: string;
}

export interface MissingInfo {
  berkas: string;
  masalah: string;
  dampak: string;
  tingkat: string;
}

export interface Claim {
  id: string;
  asv: string;
  stasiun: string;
  danau: string;
  nama_lab: string;
  dilaporkan: string;
  tingkat: string;
  kemiripan: number | null;
  nilai: string;
  skor: number;
  batas_D: string;
  penyebab: string[];
  peluang_belum_di_kamus: number | null;
  label_L3: string[];
  keputusan: string;
}

export interface Reason {
  lapisan: string;
  judul: string;
  skor: number | null;
  maks: number | null;
  id: string;
  en: string;
}

export interface Origin {
  status: string;
  jalur: string;
  sumber_dna: string;
  fasilitas: string;
}

export interface EvidenceCardData {
  keluaran: {
    tingkat: string;
    nilai: string;
    skor: string;
    galat_nilai: string;
    peluang: string;
    catatan_peluang: string;
    penyebab: string[];
  };
  alasan: Reason[];
  tindak_lanjut: string;
  asal_usul: Origin | null;
  batas_D: string;
  "kecocokan_dalam_0,5%": string[];
}

export interface GapGroup {
  label: string;
  petunjuk: string;
  total: number;
  ada_sekuens: number;
  tervalidasi: number;
}

export interface GapGenus {
  wilayah: string;
  genus: string;
  n: number;
  r: number;
  p: number;
  tanpa_referensi: string[];
}

export interface PriorityItem {
  urutan: number;
  target: string;
  jenis: string;
  danau: string;
  status_L3: string;
  alasan: string;
  klaim: number;
}

export interface Report {
  schema: string;
  meta: ReportMeta;
  ringkasan: Summary;
  penyebab: CauseCount[];
  berkas: InputFile[];
  informasi_hilang: MissingInfo[];
  klaim: Claim[];
  kartu: Record<string, EvidenceCardData>;
  celah: { judul: string; kelompok: GapGroup[]; per_genus: GapGenus[]; sumber: string };
  prioritas_barcode: PriorityItem[];
  nama_ilmiah: string[];
  ekspor: { csv: string; pdf: string; barcode: string; manifest: string };
}
