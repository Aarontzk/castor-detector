# Castor — Product Requirements Document (PRD)

**Versi:** 0.2 (komprehensif)
**Status:** Untuk direview sebelum eksekusi
**Owner:** Aka
**Tanggal:** Juli 2026
**Dokumen ini adalah:** Single source of truth untuk pengembangan Castor. Setiap keputusan implementasi harus bisa dirujuk balik ke dokumen ini.

---

# BAGIAN I — KONTEKS & MASALAH

## 1. Ringkasan Eksekutif

Castor adalah **observability & attribution layer open-source** untuk sistem multi-agent LLM. Fungsinya satu kalimat: memberi tahu developer **kapan** rantai agent mereka mulai berhalusinasi, **di step mana** dimulainya, **jenis** halusinasi apa, dan **bagaimana penyebarannya** — sesuatu yang tidak bisa dilakukan detector hallucination per-step standar.

Castor TIDAK mencoba menghilangkan hallucination (secara teoretis terbukti mustahil untuk model probabilistik — lihat Section 3.1). Castor mengubah hallucination dari kegagalan yang tak terlihat menjadi kegagalan yang **terlokalisasi, terklasifikasi, dan bisa di-debug**.

**Analogi posisi produk:** Sentry/Datadog memberi developer stack trace saat aplikasi crash. Castor memberi developer "stack trace" saat rantai reasoning agent mereka menyimpang dari kebenaran.

## 2. Problem Statement

### 2.1 Masalah inti: local coherence ≠ global truth

Sistem multi-agent memproses informasi sekuensial: output stage *i* menjadi konteks otoritatif stage *i+1*. Ketika error masuk di stage *i*:

1. Error diteruskan sebagai konteks "valid" ke stage berikutnya
2. Stage berikutnya menghasilkan output yang **koheren terhadap konteks tercemar** tapi salah terhadap kenyataan
3. Setiap step individual lolos pemeriksaan detector standar, karena secara lokal semuanya "masuk akal"
4. Error membesar monoton: |ε(i+1)| ≥ |ε(i)|

Ini sudah dibuktikan secara formal (CHARM, Lemma 1): untuk setiap tipe cascade, output per-step LOLOS threshold deteksi standar. Per-step detection secara inheren tidak cukup.

### 2.2 Kenapa self-correction tidak menyelesaikan ini

Agent yang diminta mereview logikanya sendiri mengalami **confirmation bias**: reasoning downstream tampak logis relatif terhadap memorinya yang sudah tercemar, sehingga agent justru MENGUATKAN cascade, bukan mengoreksinya. Fenomena "chain disloyalty": model mempertahankan klaim salah bahkan ketika koreksi diberikan sejak awal.

### 2.3 Skala masalah (data pendukung)

| Temuan | Sumber |
|---|---|
| 64% developer menyebut hallucination/inaccuracy risiko utama AI | State of AI 2026 Survey (n=6.084) |
| 66% frustrasi terbesar: output "almost right, but not quite"; 45%: debugging kode AI makan waktu lebih lama | Stack Overflow Developer Survey 2025 (n=49.000+) |
| ~40% proyek agentic AI dibatalkan/dihentikan | Gartner & MIT, awal 2026 |
| Contoh nyata: agent invoice stuck loop 50x cek email yang sama, bakar $400 token | Laporan produksi 2026 |
| 100 sitasi fabrikasi AI lolos review 3-5 pakar di NeurIPS 2025, muncul di 53 paper | Studi failure mode NeurIPS 2025 |
| Hanya 12% organisasi punya data cukup berkualitas untuk AI | Precisely 2025 |

### 2.4 Kenapa masalah ini belum terselesaikan tools yang ada

| Kategori tools existing | Contoh | Kenapa gagal untuk cascade |
|---|---|---|
| Output-level detector | SelfCheckGPT | Hanya evaluasi respons terminal; miss seluruh error intermediate yang membangunnya |
| Retrieval-level evaluator | RAGAS | Hanya cek relevansi dokumen di step 1; tidak melacak apakah konteks dipakai benar di step berikutnya |
| Consistency checker | Self-consistency sampling | Output cascade justru SANGAT konsisten secara internal — konsisten terhadap premis salah |
| Guardrail umum | Guardrails AI, NeMo Guardrails | Validasi per-output terhadap schema/policy; tidak punya konsep trajectory lintas step |
| Observability enterprise | Galileo, Arize, Langfuse | Tracing & logging kuat, tapi deteksi cascade + attribution titik asal belum jadi fitur first-class; berbayar/berat untuk tim kecil |
| Causal cascade research | CASPIAN | Sangat dekat secara teknik, tapi dirancang untuk cascade AKIBAT SERANGAN (adversarial), bukan hallucination organik; belum jadi tools praktis yang mudah dipasang |

**Celah pasar Castor:** deteksi + klasifikasi + attribution untuk cascade **organik**, ringan, gratis dijalankan, retrofit ke pipeline yang sudah ada.

## 3. Landasan Riset

### 3.1 Kenapa hallucination tidak bisa dihilangkan (dasar filosofi produk)

Empat sumber yang saling terkait (riset "Fundamental Limits of LLMs at Scale"):
1. **Batas komputabilitas** — hallucination terbukti matematis tak terhindarkan untuk model probabilistik
2. **Data training** — tidak lengkap, berisik, long-tail, usang, saling bertentangan
3. **Misalignment evaluasi** — benchmark memberi reward ke fabrikasi percaya diri, bukan ketidakpastian terkalibrasi; model belajar "bluffing"
4. **Trade-off kreativitas-faktualitas** — mekanisme yang memungkinkan kreativitas adalah mekanisme yang meningkatkan risiko hallucination

**Implikasi produk:** karena eliminasi mustahil, nilai tertinggi yang bisa di-deliver adalah **deteksi dini + lokalisasi + attribution**. Ini keputusan desain fundamental Castor.

### 3.2 Fondasi yang diadopsi (tidak dibangun ulang)

| Sumber | Yang diadopsi | Bukti kualitas | Yang TIDAK diadopsi |
|---|---|---|---|
| **CHARM** (arXiv:2606.04435) | Taksonomi 4 tipe cascade; arsitektur passive observer; dual-reference drift tracking; nilai threshold awal (δ=0.18, τ=0.72, θ=0.55) sebagai starting point | 89.4% detection rate, 5.3% FPR, 215ms overhead/stage; ablation lengkap | Bobot manual 0.4/0.4/0.2 diadopsi sementara TAPI ditandai sebagai kelemahan yang diketahui; CPM (confidence monitor) diberi peran sekunder |
| **Hallucination Cascade** (arXiv:2606.07937) | Metodologi eksperimen injeksi error terkontrol; claim-level decomposition; temuan bahwa model heterogen punya profil hallucination berbeda | 500 eksperimen, 10 domain, 3 model, signifikansi statistik dilaporkan | Fokus mereka pada attenuation via refinement chain (trade-off dengan factual loss) tidak jadi strategi utama Castor |
| **Controlled Synthetic Data Generation** (arXiv:2410.12278) | Teknik synthetic error injection untuk membangun dataset validasi tanpa data hallucination asli (memotong circular dependency) | F1 0.938, mengungguli in-context learning detector 32.5% | - |
| **CASPIAN** (arXiv:2605.19240) | KONSEP attribution: origin / amplifier / bridge / propagation spine. Diadopsi versi threshold-based sederhana | Mengungguli semantic guardrails, LLM-judges, graph anomaly detectors; overhead <1% | Transfer entropy (LI-CTE) TIDAK diimplementasikan di v0.x — butuh banyak sampel interaksi & compute berat; masuk roadmap v2 |
| **AgentHallu** (arXiv:2601.06818) | Referensi benchmark step-level attribution (693 trajectory, 5 domain) untuk pembanding evaluasi | Benchmark khusus atribusi | - |

### 3.3 Kelemahan fondasi yang diakui secara eksplisit (dan bagaimana Castor menyikapinya)

| Kelemahan diakui penulis paper | Sikap Castor |
|---|---|
| Bobot agregasi CHARM (0.4/0.4/0.2) adalah tebakan wajar, bukan hasil learning — circular dependency: butuh data cascade berlabel untuk belajar bobot, butuh detector untuk melabeli data | Pakai bobot manual di v0.1; bangun dataset sintetis via error injection; kalibrasi ulang bobot dari dataset sintetis di v1 |
| Estimasi propagasi CHARM = ko-okurensi (korelasi), bukan bukti kausal | v0.1 jujur melabeli attribution sebagai "kandidat titik asal, threshold-based" dengan skor confidence — tidak pernah klaim causal proof; causal upgrade di v2 |
| Confidence self-reported LLM tidak terkalibrasi (CPM standalone hanya 38.3% CDR) | Sinyal confidence HANYA dipakai sebagai sinyal sekunder untuk mendeteksi tipe Confidence Inflation; tidak pernah jadi gerbang keputusan utama |
| Threshold tunggal tidak sebanding lintas jenis task (heteroskedastic signals, arXiv:2606.15841) | Threshold configurable per-kategori-task sejak v0.1; profil threshold per-domain masuk roadmap v1 |

---

# BAGIAN II — PETA HALLUCINATION SURFACE

## 4. Anatomi Workflow Multi-Agent & Semua Titik Masuk Hallucination

Ini bagian terpenting dokumen. Setiap titik diberi ID (H-x) dan status coverage Castor. Workflow referensi adalah generalisasi pipeline agentic modern:

```
[User Input] → [Query Formulation] → [Retrieval / Data Fetch] → [Intermediate Reasoning]
     → [Tool Use / Function Call] → [Inter-Agent Handoff] → [Memory Read/Write]
     → [Synthesis] → [Final Output] → (loop / multi-turn)
```

### 4.1 Katalog titik hallucination

| ID | Titik | Deskripsi mekanisme | Tipe cascade terkait | Coverage Castor |
|---|---|---|---|---|
| H-01 | **Query formulation** | Agent salah menginterpretasi maksud user; seluruh pipeline mengerjakan pertanyaan yang salah dengan benar | Inference | ✅ v0.1 — drift step-1 vs input user |
| H-02 | **Retrieval: dokumen salah/tidak relevan** | Top-k mengembalikan dokumen yang salah; semua reasoning dibangun di atas premis palsu | Retrieval | ✅ v0.1 — source-output divergence |
| H-03 | **Retrieval: dokumen benar, ekstraksi salah** | Dokumen relevan, tapi agent mengutip/menyimpulkan bagian yang salah dari dokumen itu | Retrieval → Inference | ✅ v0.1 — entailment check evidence↔claim |
| H-04 | **Retrieval: informasi usang** | Dokumen valid tapi kedaluwarsa (definisi lama, kebijakan yang sudah diganti, metrik yang sudah direvisi) diperlakukan sebagai kebenaran terkini | Context Poisoning | ⚠️ v0.1 parsial (terdeteksi sebagai drift jika kontras dengan konteks lain); deteksi staleness eksplisit butuh metadata timestamp → v1 |
| H-05 | **Inferential leap** | Data benar, tapi lompatan logika tidak valid: "penjualan naik 10%" → "strategi marketing efektif" → "gandakan budget" | Inference | ✅ v0.1 — entailment drop antar step |
| H-06 | **Fabrikasi numerik/entitas** | Angka, nama, tanggal, sitasi, nama package yang dikarang tapi tampak plausibel | Inference | ⚠️ v0.1 parsial via drift; claim-level verification (dekomposisi klaim atomik) → v1 |
| H-07 | **Tool call: parameter fabrication** | Agent memanggil tool dengan argumen yang dikarang (ID yang tidak ada, filter yang salah) | Inference | ⚠️ v0.1 parsial (output tool yang aneh memicu drift); validasi parameter eksplisit → v1 |
| H-08 | **Tool output misinterpretation** | Tool mengembalikan data benar, agent salah membacanya (salah unit, salah kolom, salah baris) | Inference | ✅ v0.1 — entailment tool-output↔claim berikutnya |
| H-09 | **Tool error ditelan diam-diam** | Tool gagal/timeout, agent melanjutkan seolah dapat data, mengisi kekosongan dengan karangan | Retrieval/Inference | ⚠️ v0.1 parsial; hook eksplisit untuk error signal tool → v1 |
| H-10 | **Inter-agent handoff loss** | Informasi terdistorsi saat diserahkan antar agent (ringkasan yang menghilangkan kualifikasi penting: "mungkin naik" jadi "naik") | Inference/Confidence Inflation | ✅ v0.1 — drift antar handoff + confidence tracking |
| H-11 | **Confidence inflation antar step** | Dugaan lemah di step awal dinaikkan kepastiannya tiap step tanpa bukti baru: "kemungkinan" → "kemungkinan besar" → "sudah pasti" | Confidence Inflation | ✅ v0.1 — hedging-language tracking + drift; logit-based → v1 (butuh akses logit) |
| H-12 | **Memory write tercemar** | Kesimpulan salah ditulis ke memori persisten; mencemari SEMUA percakapan/task berikutnya, bukan cuma rantai saat ini | Context Poisoning (lintas sesi) | ❌ v0.1; memory-boundary monitoring → v1 (kebutuhan tinggi, kompleksitas sedang) |
| H-13 | **Memory read usang** | Agent membaca memori dari konteks lama yang sudah tidak berlaku | Context Poisoning | ❌ v0.1; → v1 bersama H-12 |
| H-14 | **Cross-turn drift (multi-turn)** | Percakapan panjang: klaim episode awal bermutasi pelan-pelan di episode berikutnya | Inference (temporal) | ⚠️ v0.1 mendukung trajectory panjang secara mekanis; anchor management lintas-turn (kapan reset referensi) → v1 |
| H-15 | **Loop amplification** | Agent loop (retry, polling) memperkuat klaim yang sama berulang sampai tampak seperti konsensus | Confidence Inflation | ⚠️ v0.1 parsial (repetisi tinggi = similarity tinggi ke diri sendiri, sinyal berbeda); deteksi loop eksplisit → v1 |
| H-16 | **Multi-agent debate false consensus** | Beberapa agent "berdebat" lalu konvergen ke jawaban salah; konsensus dikira validasi | Confidence Inflation | ❌ v0.1 (topologi v0.1 = rantai linier); topologi graf/DAG → v2 |
| H-17 | **Orchestrator misrouting** | Agent router mengirim task ke agent yang salah; agent tersebut menjawab dengan percaya diri di luar kompetensinya | Inference | ❌ v0.1; butuh model kompetensi per-agent → v2 |
| H-18 | **Multimodal: vision extraction error** | Model salah membaca gambar (angka di chart, teks di dokumen scan) lalu error masuk pipeline teks | Retrieval (modal lain) | ❌ v0.1 (text-only); lihat Section 4.2 → v2 |
| H-19 | **Multimodal: cross-modal grounding failure** | Klaim teks tidak sesuai dengan konten gambar/audio yang dirujuknya | Inference (cross-modal) | ❌ v0.1; → v2 |
| H-20 | **Prompt injection / adversarial** | Instruksi berbahaya di data eksternal membajak reasoning | Context Poisoning (disengaja) | ❌ SELAMANYA di luar scope — ini domain security (CASPIAN, LLM Guard). Castor fokus hallucination organik. Didokumentasikan agar user tidak salah ekspektasi |

### 4.2 Posisi multimodal (keputusan eksplisit)

Target user Castor termasuk tim dengan workflow multimodal. Keputusan desain:

- **v0.1 adalah text-only pada layer pengukuran.** Alasan teknis: embedding model teks (all-mpnet-base-v2) tidak bisa mengukur drift terhadap gambar/audio secara langsung, dan menambah CLIP-style multimodal embedding menggandakan kompleksitas sebelum fondasi terbukti.
- **TAPI arsitektur v0.1 WAJIB multimodal-ready:** struktur data trajectory punya field `modality` dan `raw_ref` sejak hari pertama, sehingga step multimodal bisa direkam (dengan representasi teksnya, mis. caption/hasil ekstraksi) walau pengukuran drift-nya belum cross-modal.
- **Praktisnya untuk user multimodal hari ini:** titik H-18 tetap tertangkap SECARA TIDAK LANGSUNG — begitu hasil ekstraksi vision masuk sebagai teks ke step berikutnya, drift teks-ke-teks Castor mulai bekerja dari situ. Yang belum bisa: memverifikasi ekstraksi terhadap gambar aslinya.
- **v2:** cross-modal grounding via multimodal embedding (CLIP-family / SigLIP) sebagai modul opsional.

## 5. Value Map — Apa Persisnya yang Di-deliver ke User

| # | Nilai | Tanpa Castor | Dengan Castor | Fase |
|---|---|---|---|---|
| V1 | **Deteksi dini cascade** | Tahu output akhir salah (kalau ketahuan sama sekali) | Alert saat drift mulai, sebelum sampai output akhir | v0.1 |
| V2 | **Lokalisasi titik asal** | Debug manual step-by-step, berjam-jam | "Cascade dimulai step 3, agent `reasoner`" | v0.1 |
| V3 | **Klasifikasi jenis** | "Ada yang salah entah di mana" | "Ini Inference Cascade" → langsung tahu perbaikannya di logika prompt, bukan di retrieval | v0.1 |
| V4 | **Jejak penyebaran** | Tidak ada | Laporan drift per-step: step mana stabil, step mana melompat | v0.1 |
| V5 | **Regression testing reliability** | Ganti prompt/model, berdoa tidak ada yang rusak | Jalankan test suite trajectory + error injection; bandingkan skor cascade antar versi pipeline | v0.1 (CLI) / v1 (CI integration) |
| V6 | **Perbandingan konfigurasi** | Pilih model/urutan agent berdasar feeling | Data: konfigurasi A menyebarkan error 2x lebih jauh daripada konfigurasi B | v1 |
| V7 | **Memory hygiene** | Memori tercemar diam-diam merusak semua sesi berikutnya | Gate/alert sebelum klaim ber-drift-tinggi ditulis ke memori | v1 |
| V8 | **Audit trail reliability** | Tidak ada bukti untuk review/compliance | Laporan terstruktur per-run yang bisa disimpan dan diaudit | v1 |
| V9 | **Amplifier/bridge attribution** | - | "Agent X paling sering jadi penguat error di sistem lu" | v2 |
| V10 | **Cross-modal grounding** | - | Verifikasi klaim teks terhadap sumber gambar | v2 |

**Positioning satu kalimat untuk README:** *"Castor tells you WHERE your agent chain started hallucinating — not just that it did."*

---

# BAGIAN III — PRODUK

## 6. Target User & Persona

### Persona utama: "Backend/AI engineer di tim kecil"
- Membangun pipeline LangChain/CrewAI/custom 3-10 step, kadang multimodal (vision extraction → reasoning teks)
- Pain: output kadang salah, debugging = baca log manual berjam-jam; tidak ada budget Galileo/Arize; tidak tahu step mana yang jadi sumber masalah
- Kebutuhan: pasang cepat (<15 menit), tidak mengubah pipeline yang ada, tidak menambah biaya API, output yang langsung actionable

### Persona sekunder: "Solo builder / indie hacker"
- Agent workflow untuk produk sendiri; sangat sensitif biaya; butuh confidence sebelum ship

### Persona tersier (roadmap): "Tim regulated industry"
- Butuh audit trail; tertarik V8; baru relevan setelah v1 stabil

### Anti-persona (bukan target)
- Tim yang butuh perlindungan adversarial/security (arahkan ke CASPIAN/LLM Guard)
- Tim yang butuh real-time blocking latency-critical di v0.1 (Castor v0.1 = passive observer)

## 7. Use Cases (Detail, dengan Alur)

### UC-1: Post-mortem debugging (use case inti v0.1)
**Aktor:** Engineer dengan trajectory yang menghasilkan output salah.
**Alur:** (1) Export trajectory (list step) → (2) `castor analyze trajectory.json` → (3) Terima laporan: flag per step, drift ke step sebelumnya & ke anchor awal, kandidat titik asal, tipe cascade, confidence → (4) Perbaiki step yang ditunjuk.
**Sukses jika:** waktu menemukan step bermasalah turun dari jam ke menit.

### UC-2: Live observation (passive, non-blocking)
**Aktor:** Pipeline berjalan di dev/staging.
**Alur:** (1) Bungkus pipeline dengan `CastorObserver` (callback LangChain / decorator Python) → (2) Setiap step selesai, Castor menghitung drift secara async → (3) Jika threshold terlampaui, emit warning ke log/callback (TIDAK memutus eksekusi di v0.1).
**Catatan desain:** blocking/halt adalah opsi opt-in di v1, bukan default — false positive yang menghentikan produksi lebih merusak kepercayaan daripada cascade yang terlewat di fase awal produk.

### UC-3: Regression testing sebelum deploy
**Aktor:** Engineer mengganti model/prompt/urutan agent.
**Alur:** (1) Punya suite trajectory uji + suite dengan error injection → (2) Jalankan sebelum & sesudah perubahan → (3) Bandingkan: detection rate, drift profile, titik asal → (4) Merge hanya jika profil reliability tidak memburuk.

### UC-4: Kalibrasi threshold per domain
**Aktor:** User yang domainnya beda karakter (legal vs. kode vs. data numerik).
**Alur:** (1) `castor calibrate` dengan sample trajectory bersih milik user → (2) Castor menghitung distribusi drift normal domain tersebut → (3) Merekomendasikan threshold → (4) Simpan sebagai profil.
**Kenapa penting:** temuan heteroskedastic signals — threshold global tunggal tidak adil lintas jenis task. Ini differentiator vs. CHARM yang pakai threshold global.

### UC-5: Multi-turn conversation monitoring
**Aktor:** Builder chatbot/copilot dengan sesi panjang.
**Alur:** trajectory lintas turn; anchor = klaim faktual awal; Castor melacak mutasi klaim antar turn (H-14). v0.1 mendukung secara mekanis (trajectory panjang), manajemen anchor pintar di v1.

### UC-6 (v1): Memory write gate
**Alur:** sebelum agent menulis ke memori persisten, klaim dicek drift & entailment-nya; klaim berisiko ditandai/ditahan (H-12).

## 8. Goals & Non-Goals

### Goals v0.x
1. Deteksi semantic drift dua-referensi (previous + anchor) tanpa API berbayar
2. Klasifikasi ke 4 taksonomi cascade dengan sinyal murah (embedding + NLI lokal)
3. Attribution threshold-based dengan skor confidence yang jujur
4. Retrofit non-invasif: callback LangChain + API Python generik + CLI
5. Seluruh dev & validasi 100% gratis (model lokal, data sintetis)
6. Arsitektur modular + multimodal-ready pada struktur data

### Non-Goals v0.1 (eksplisit, dengan alasan)
| Non-goal | Alasan | Nasib |
|---|---|---|
| Mencegah/memblokir hallucination secara aktif | Passive observer dulu; blocking butuh FPR sangat rendah yang belum terbukti | v1 opt-in |
| Adversarial/prompt injection defense | Domain security berbeda (H-20); sudah ada pemain (CASPIAN, LLM Guard) | Selamanya di luar scope |
| Transfer entropy / causal proof formal | Butuh banyak sampel interaksi + compute berat; attribution sederhana sudah deliver nilai | v2 |
| Pengukuran drift cross-modal | Kompleksitas ganda sebelum fondasi terbukti | v2 (struktur data sudah siap sejak v0.1) |
| Dashboard UI | Core library dulu; laporan JSON/teks cukup untuk persona utama | v1/v2 |
| Topologi non-linier (debate, graf agent) | v0.1 = rantai linier; mayoritas pipeline produksi masih linier | v2 |
| Fine-tuning model embedding/NLI khusus | Pakai model off-the-shelf yang terbukti dulu | Backlog |

## 9. Functional Requirements

### FR-1: Trajectory Data Model
- Struktur step: `{step_id, text, agent_name?, role?, timestamp?, modality: "text" (default), raw_ref?, confidence_raw?, metadata?}`
- HARUS menyimpan SELURUH step (bukan hanya terakhir); embedding di-cache per step (hitung sekali)
- HARUS menerima trajectory dari: (a) list Python, (b) file JSON/JSONL, (c) stream callback (step masuk satu-satu)
- Field `modality` & `raw_ref` wajib ada sejak v0.1 walau pengukuran multimodal belum aktif (multimodal-ready)

### FR-2: Embedding & Similarity Engine
- Default: `sentence-transformers` model `all-mpnet-base-v2` (lokal, gratis; konsisten dengan CHARM agar hasil bisa dibandingkan)
- Model embedding HARUS pluggable (interface `Embedder`) — user bisa ganti model multibahasa (mis. untuk Bahasa Indonesia) tanpa menyentuh core
- Cosine similarity via numpy; tidak ada dependency API berbayar

### FR-3: Dual-Reference Drift Tracker
- Untuk tiap step i≥2 hitung: `drift_prev = 1 - sim(e_i, e_{i-1})` dan `drift_anchor = 1 - sim(e_i, e_anchor)`
- Anchor default = step 1; HARUS bisa dioverride user (mis. anchor = dokumen sumber, bukan step 1 — penting untuk kasus H-02 di mana step 1 sendiri yang tercemar)
- Dukungan **consensus anchor** (mengikuti CHARM): anchor bisa berupa agregat top-k dokumen retrieval, bukan hanya top-1, untuk mengurangi risiko anchor tunggal yang korup

### FR-4: Transition Validity (Entailment) Checker
- NLI cross-encoder lokal (`cross-encoder/nli-deberta-v3-base`, konsisten CHARM) menilai: apakah step i+1 ter-entail oleh step i + evidence
- Output: skor entail/neutral/contradiction per transisi
- Fungsi kunci untuk membedakan "topik baru yang sah" vs. "lompatan logika yang diklaim sebagai kesimpulan" (H-05): penurunan entailment + klaim konklusif = flag; pergantian topik eksplisit tanpa klaim kesimpulan = bukan flag

### FR-5: Anomaly Flagging & Threshold Management
- Default awal: `δ_drift = 0.18`, `τ_entail = 0.72` (dari CHARM) — HARUS configurable, per-instance dan per-profil
- HARUS mendukung **threshold profile per kategori task** (respons ke masalah heteroskedastic): user mendefinisikan profil (mis. "numerik", "naratif", "kode") dengan threshold masing-masing
- `castor calibrate`: hitung distribusi drift dari sample trajectory bersih milik user, rekomendasikan threshold (UC-4)

### FR-6: Taxonomy Classifier
Rule-based v0.1, sinyal per tipe:
| Tipe | Sinyal utama |
|---|---|
| Retrieval Cascade | Divergensi tinggi antara output step-1/evidence dan sumber; drift_anchor tinggi sejak awal |
| Inference Cascade | Entailment drop pada transisi + klaim konklusif; drift_prev rendah tapi drift_anchor menanjak bertahap |
| Context Poisoning | Lonjakan drift mendadak di tengah rantai pada konten yang masuk dari luar (tool/memori) |
| Confidence Inflation | Bahasa kepastian menguat (hedging-word tracking: "mungkin"→"pasti"; daftar termino bilingual EN+ID) sementara tidak ada evidence baru + drift_anchor naik |
- Output klasifikasi HARUS menyertakan confidence dan boleh multi-label (satu cascade bisa dua tipe sekaligus)

### FR-7: Origin Attribution
- Kandidat titik asal = step pertama yang melewati threshold pada sinyal manapun
- Output WAJIB: `{origin_step, origin_agent, cascade_type[], drift_scores, confidence, method: "threshold-based"}` — field `method` wajib, agar user tahu ini bukan causal proof
- Jika beberapa step melewati threshold hampir bersamaan, laporkan semua kandidat terurut, jangan paksa satu jawaban

### FR-8: Reporting
- Format: JSON terstruktur (machine-readable, untuk CI) + ringkasan teks human-readable (untuk terminal)
- Isi minimal: verdict (cascade/tidak), per-step drift table, flagged steps, klasifikasi, attribution, threshold yang dipakai, versi Castor + versi model embedding (reproducibility)

### FR-9: Integration Surface
- **API Python generik**: `CastorObserver.observe(step)` + `CastorObserver.report()` — framework-agnostic, prioritas #1
- **LangChain callback handler**: menempel via mekanisme callback resmi, tanpa mengubah chain user — prioritas #2
- **CLI**: `castor analyze <file>`, `castor calibrate <dir>` — prioritas #3
- CrewAI/AutoGen/lainnya: lewat API generik dulu; adapter khusus menyusul berdasarkan permintaan user nyata

### FR-10: Synthetic Error Injection Toolkit (untuk validasi & untuk user)
- Modul `castor.inject`: menyuntik error terkontrol ke trajectory bersih — jenis suntikan: fabrikasi numerik, distorsi entitas, lompatan kausal, inflasi kepastian, penukaran konteks
- Dipakai internal untuk validasi (Section 12) DAN diekspos ke user untuk membangun regression suite mereka sendiri (UC-3). Ini fitur, bukan cuma alat internal.

### FR-11: Performance & Footprint
- Overhead per step (embedding + similarity) di consumer GPU/CPU: target <500ms per step, mode async tersedia agar tidak memblokir pipeline
- Memori: cache embedding per trajectory; untuk trajectory >100 step, sliding window + anchor tetap dipertahankan
- Instalasi: `pip install castor-*` menarik dependency <2GB (model di-download saat first-run, bukan dibundel)

### FR-12: Error Handling & Degradasi
- Jika model NLI gagal dimuat → degradasi ke drift-only mode dengan warning eksplisit (jangan diam-diam)
- Jika step kosong/non-teks → skip dengan catatan di laporan, jangan crash
- Castor tidak boleh pernah menjadi penyebab pipeline user gagal (semua exception internal tertangkap, dilaporkan sebagai monitoring failure)

## 10. Arsitektur

```
                        ┌──────────────────────────────────────┐
 [Pipeline user]        │            CASTOR (passive)          │
  step output ──────────▶  Ingestion (API / callback / CLI)    │
  (tidak diubah,        │        │                             │
   tidak diblokir)      │        ▼                             │
                        │  Trajectory Store (semua step +      │
                        │  embedding cache, multimodal-ready)  │
                        │        │                             │
                        │        ├──▶ Drift Tracker (dual-ref) │
                        │        ├──▶ Entailment Checker (NLI) │
                        │        └──▶ Confidence-Language      │
                        │             Tracker (hedging words)  │
                        │        │                             │
                        │        ▼                             │
                        │  Aggregator (weighted, configurable, │
                        │  default bobot CHARM — ditandai      │
                        │  sebagai known limitation)           │
                        │        │                             │
                        │        ├──▶ Taxonomy Classifier      │
                        │        └──▶ Origin Attribution       │
                        │        │                             │
                        │        ▼                             │
                        │  Report (JSON + human-readable)      │
                        └──────────────────────────────────────┘
```

Prinsip: setiap kotak = modul dengan interface, bisa diganti tanpa merombak yang lain (mitigasi risiko "fondasi paper masih baru").

## 11. Tech Stack

| Komponen | Pilihan | Alasan |
|---|---|---|
| Bahasa | Python 3.10+ | Ekosistem ML + target user |
| Embedding | sentence-transformers / all-mpnet-base-v2 (pluggable) | Konsisten CHARM; gratis; lokal |
| NLI | cross-encoder/nli-deberta-v3-base (pluggable) | Konsisten CHARM; lokal |
| Numerik | numpy | Cukup; hindari dependency berat |
| Simulasi agent untuk testing | Ollama + qwen2.5-coder / phi4-mini | Gratis; RTX 4060 memadai |
| Packaging | pyproject.toml, pip-installable | Standar |
| Lisensi | MIT | Adopsi maksimal, mengikuti pola OSS sukses di ruang ini |

## 12. Validation Plan (100% tanpa API berbayar)

1. **Dataset sintetis:** 30 trajectory bersih manual (fakta terverifikasi, domain campur: numerik, naratif, prosedural, multi-turn) → duplikasi dengan suntikan error via FR-10 pada step & tipe yang tercatat → total ±90-120 trajectory berlabel
2. **Dataset semi-natural:** jalankan agent chain lokal (Ollama) pada task nyata, anotasi manual sebagian output — menangkap hallucination organik asli, bukan hanya sintetis
3. **Metrik:** detection rate; FPR; attribution accuracy (exact-step & ±1 step); classification accuracy per tipe; latency per step
4. **Ablation wajib:** drift-prev saja vs. drift-anchor saja vs. dual vs. dual+NLI vs. full — setiap komponen harus membuktikan kontribusinya atau dibuang (hindari overengineering)
5. **Pembanding:** baseline naive (threshold similarity tunggal output-akhir-vs-input) — Castor harus mengalahkan ini dengan margin jelas, kalau tidak, produk tidak punya alasan ada

## 13. Success Metrics

| Metrik | Target v0.1 | Catatan |
|---|---|---|
| Detection rate (dataset sintetis) | ≥70% | CHARM mencapai 89.4% dengan resource riset penuh; 70% jujur untuk v0.1 |
| False positive rate | ≤20%, arah turun tiap iterasi | FPR adalah metrik kepercayaan #1 — user meninggalkan tools yang banyak alarm palsu |
| Attribution accuracy (±1 step) | ≥50% | Baseline kasar |
| Setup time user baru | <15 menit clone→laporan pertama | Diukur dengan tester eksternal (bukan diri sendiri) |
| Overhead per step | <500ms di CPU consumer | |
| Adopsi (setelah publish) | Sinyal kualitatif dulu: 3-5 user nyata memberi feedback | Bintang GitHub bukan metrik fase awal |

## 14. Risks & Mitigations

| Risiko | Kemungkinan | Dampak | Mitigasi |
|---|---|---|---|
| FPR tinggi di dunia nyata (drift sah terdeteksi sebagai cascade — topik pindah secara legitimate) | Tinggi | Tinggi (kepercayaan) | Entailment layer untuk bedakan "topik baru sah" vs "lompatan diklaim kesimpulan"; default non-blocking; threshold per-profil; kalibrasi per-domain |
| Threshold CHARM tidak transfer ke domain/bahasa user (termasuk Bahasa Indonesia) | Tinggi | Sedang | `castor calibrate`; embedding pluggable ke model multibahasa; dokumentasi jujur bahwa default = starting point |
| Paper fondasi masih baru, klaim bisa terpatahkan | Sedang | Tinggi | Arsitektur modular; validasi independen sendiri (Section 12), jangan hanya percaya angka paper |
| Kompetitor besar menambahkan fitur serupa | Sedang | Sedang | Kecepatan rilis scope kecil; positioning "ringan & gratis" yang enterprise tools tidak incar |
| Scope creep (v0.1 membengkak) | Tinggi | Tinggi | Non-goals eksplisit (Section 8); fase dikunci; fitur baru masuk backlog, bukan sprint berjalan |
| Confidence-language tracking (hedging words) rapuh lintas gaya bahasa | Sedang | Rendah | Sinyal ini bobot terkecil; multi-label + confidence di output |
| Solo developer, waktu terbatas | Tinggi | Tinggi | Prioritas keras: Fase 1 & 4 dulu; Claude Code untuk akselerasi implementasi |

## 15. Rollout Fase

| Fase | Deliverable | Definition of Done |
|---|---|---|
| 0 — Fondasi | Env setup; ringkasan taksonomi; 10 trajectory uji pertama | Environment jalan; dokumen ringkas ada |
| 1 — Drift Core | FR-1,2,3,5 (subset), FR-12 | 5 trajectory manual: step ber-drift tertinggi sesuai ekspektasi anotasi manual |
| 2 — Klasifikasi | FR-4, FR-6 | ≥60-70% classification accuracy di dataset suntik |
| 3 — Attribution | FR-7, FR-8 | Output terstruktur lengkap dengan field method & confidence |
| 4 — Validasi | Section 12 penuh + FR-10 | Laporan metrik & ablation tertulis; keputusan buang/pertahankan tiap komponen |
| 5 — Packaging | FR-9, FR-11; README; contoh; publish GitHub + PyPI | Tester eksternal: clone→laporan <15 menit |
| v1 (pasca-feedback) | H-04, H-07, H-09 eksplisit; memory gate (H-12/13); anchor management multi-turn (H-14); loop detection (H-15); CI integration; blocking opt-in; kalibrasi bobot dari data sintetis | Ditentukan dari feedback user nyata |
| v2 (riset) | Transfer entropy attribution; topologi graf (H-16/17); multimodal grounding (H-18/19); dashboard | Ditentukan kemudian |

**Aturan main (sesuai kesepakatan):** jangan menumpuk strategi di depan. v1 dan v2 adalah arah, bukan janji. Iterasi dari feedback dan error nyata.

## 16. Open Questions

1. Format anchor untuk multi-turn: reset per turn, atau anchor kumulatif? (tunda ke v1, butuh data nyata)
2. Bahasa dokumentasi: EN-first (jangkauan OSS) dengan contoh ID, atau bilingual penuh?
3. Nama package PyPI: `castor` kemungkinan bentrok — cek ketersediaan, siapkan alternatif (`castor-ai`, `castor-monitor`)
4. Threshold profile bawaan: berapa profil default yang dikapalkan? (usul awal: `general`, `numeric`, `code`)

## 17. Referensi

1. CHARM — arXiv:2606.04435
2. Hallucination Cascade — arXiv:2606.07937
3. Controlled Synthetic Data Generation for Hallucination Detection — arXiv:2410.12278
4. CASPIAN — arXiv:2605.19240
5. Heteroskedastic Signals in Budgeted LLM Verification — arXiv:2606.15841
6. AgentHallu — arXiv:2601.06818
7. On the Fundamental Limits of LLMs at Scale — arXiv:2511.12869
8. State of AI 2026 Survey; Stack Overflow Developer Survey 2025; Gartner/MIT agentic AI reports 2026

---

# LAMPIRAN — PROMPT SIAP PAKAI

## A. Prompt untuk Claude Code

```
Saya membangun Castor: Python library open-source untuk mendeteksi "hallucination
cascade" pada sistem multi-agent LLM — error kecil di satu step yang menyebar dan
membesar di step berikutnya, yang lolos dari detector per-step standar.

Dokumen acuan: castor-prd.md (terlampir di repo). Baca penuh sebelum menulis kode.
PRD adalah single source of truth; jika ada ambiguitas, tanya dulu, jangan asumsi.

TUGAS SEKARANG — implementasi Fase 1 (Drift Core) SAJA:
- FR-1: Trajectory data model (dict/dataclass: step_id, text, agent_name opsional,
  modality default "text", raw_ref opsional — field multimodal WAJIB ada walau
  belum dipakai)
- FR-2: Embedding engine — sentence-transformers all-mpnet-base-v2, dibungkus
  interface Embedder yang pluggable; cosine similarity pakai numpy
- FR-3: Dual-reference drift tracker — tiap step i≥2 hitung drift ke step i-1 DAN
  ke anchor (default step 1, bisa dioverride); embedding di-cache per step
- FR-5 (subset): threshold configurable per instance, default 0.18; flagging
  sederhana
- FR-12: error handling — Castor tidak boleh crash-kan pipeline user; step
  kosong/aneh di-skip dengan catatan

BATASAN KERAS:
- JANGAN implementasi Fase 2 (klasifikasi taksonomi), Fase 3 (attribution), NLI,
  atau integrasi LangChain — itu fase berikutnya
- Nol dependency ke API LLM berbayar
- Sertakan unit test + satu test end-to-end pakai trajectory 5 kalimat manual di
  mana step ke-3 sengaja melompat logikanya; test lulus jika step 3 mendapat
  drift tertinggi
- Struktur proyek rapi: pyproject.toml, src layout, pytest

Setelah selesai: jalankan test, laporkan hasilnya, dan berhenti. Jangan lanjut
ke fase berikutnya tanpa konfirmasi.
```

## B. Prompt untuk Claude Design (dipakai nanti di Fase 5)

```
Saya membangun Castor, tools open-source yang memberi developer "stack trace"
untuk hallucination di sistem multi-agent AI: bukan cuma mendeteksi bahwa rantai
agent berhalusinasi, tapi menunjukkan DI STEP MANA dimulainya, JENIS apa, dan
bagaimana menyebarnya.

Buatkan landing page untuk developer dengan elemen:
1. Hero: headline satu kalimat — masalah "error kecil di step 2 jadi kesimpulan
   salah yang percaya diri di step 5, dan semua detector standar melewatkannya";
   tagline produk: "Castor tells you WHERE your agent chain started hallucinating
   — not just that it did."
2. Diagram cascade: rantai 5 node agent; node 2 mulai bergeser warna, penyimpangan
   menguat ke node 5; tanpa Castor semua node tampak "hijau/lolos", dengan Castor
   node 2 ditandai sebagai origin
3. Section "How it works" 3 langkah: (a) Track — drift semantik dual-reference
   tiap step, (b) Classify — 4 tipe cascade (Retrieval, Inference, Context
   Poisoning, Confidence Inflation), (c) Attribute — tunjuk step titik asal +
   confidence
4. Section "Built for real pipelines": pasang <15 menit, passive (tidak memblokir
   pipeline), 100% lokal & gratis (tanpa API berbayar), retrofit ke LangChain
5. CTA: GitHub repo + `pip install`
Gaya: teknis, clean, terpercaya, developer-first; hindari gaya marketing
konsumen; dark-mode friendly. Ini draft awal, bukan final production.
```
