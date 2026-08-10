# Video demo script — Datathon 2026 semifinal

Target: **3–5 minutes**. Rules require **≥1 minute business side** and
**≥2 minutes of the product actually running**. Judged on "shows the actual
product in action… core user journey, implemented features, visible AI
capabilities" — so slides lose to a live terminal, and a live terminal loses to
a live terminal plus a UI.

Budget below totals **4:30**, leaving slack. Narration is Indonesian; everything
on screen stays English (matches the repo).

---

## Before you record (do this first, it is the difference between a clean take and six retries)

1. **Pre-download the models.** First use pulls ~1.2 GB and you do not want that
   on camera. Run any analysis once beforehand:
   ```
   python examples/analyze_trajectory.py
   ```
2. **Pre-warm every command you will run.** Second runs are much faster — the
   models stay in the OS file cache.
3. **Terminal setup:** font size 18–20 minimum, dark theme, window ~110 columns.
   Judges may watch on a laptop. Tiny text reads as "hiding something".
4. **Clear the scrollback** before each shot (`cls`).
5. **Have `ollama serve` running** with `qwen2.5:3b` pulled if you include the
   self-healing shot (section 4).
6. **Record audio separately if you can.** Terminal fan noise + built-in mic is
   the most common way a good demo sounds amateur.
7. **Do a silent dry run of the whole sequence once.** Every command, in order.
   Fix what breaks before the real take.

---

## 0:00 – 0:25 · Hook (the problem, shown not told)

**On screen:** a plain slide, or the README's cascade block.

```
step 1  extractor  ✓
step 2  analyst    ✗ ← "3 buses" is not entailed by the facts
step 3  reasoner   ✗   (propagating step 2's fabrication)
step 4  writer     ✓-looking, confidently wrong
```

**Narasi:**
> "Pipeline AI multi-agent kalian mengeluarkan jawaban yang salah — tapi
> terdengar sangat meyakinkan. Kalian cek setiap langkah satu per satu, semuanya
> lolos. Masalahnya bukan di satu langkah. Masalahnya di *rantainya*: satu error
> kecil di tengah, dan setiap agent sesudahnya memperlakukan error itu sebagai
> fakta. Namanya hallucination cascade."

---

## 0:25 – 1:30 · Business case (this is the ≥1 minute requirement)

**On screen:** `docs/landing.html` in a browser, or 2–3 clean slides.

**Narasi:**
> "Kenapa ini mahal. Debugging pipeline multi-agent hari ini artinya membaca log
> berjam-jam, dan tetap menebak prompt mana yang harus diperbaiki. Castor
> mengubah itu jadi satu baris: **langkah dua, agent analyst, entailment 0.003.**
>
> Empat cara pakai, semuanya sudah jalan hari ini: post-mortem debugging,
> regression gate di CI yang memblokir merge kalau reliabilitas turun,
> optimasi biaya per-role — Castor menunjukkan role mana yang jadi titik lemah,
> jadi kalian cukup upgrade model di satu role, bukan semuanya — dan pola
> self-healing.
>
> Castor jalan **100% lokal dan gratis**. Tidak ada API berbayar, data kalian
> tidak keluar dari mesin kalian. Dan Castor **pasif** — dia tidak pernah
> mengubah, memblokir, atau menghambat pipeline kalian. Kalau Castor sendiri
> error, pipeline kalian tetap jalan."

**Key numbers to say out loud** (they are the credibility, do not skip):
> "Angka kami apa adanya: deteksi 55%, false positive 27% setelah kalibrasi,
> dan atribusi asal error tepat dalam ±1 langkah di 96% kasus pada chain nyata."

---

## 1:30 – 3:45 · The product running (this is the ≥2 minute requirement)

> Do not narrate over silence while something loads. If a command takes >3s,
> either pre-warm it or cut the dead air in editing.

### Shot A — CLI on a real failing chain (~40s)

```
castor analyze validation/organic/organic-04.json --profile validation/calibrated-general.json
```

Let the per-step table land on screen. **Point at the origin row.**

**Narasi:**
> "Ini chain asli dari model lokal qwen. Castor membaca keempat langkahnya dan
> menunjuk langkah dua — di situ '3 bus' muncul, angka yang tidak ada di
> dokumen sumber. Jawaban benarnya 5 bus. Perhatikan kolom entailment: ambruk
> ke nol koma nol nol tiga."

### Shot B — the dashboard (~50s) · **owner: Aka**

Upload a trajectory JSON → per-step signals render → origin step highlighted.

**Narasi:**
> "Permukaan yang sama lewat web. Upload trajectory, dan tiap langkah muncul
> dengan sinyalnya: drift terhadap dokumen sumber, entailment, dan completeness.
> Langkah asal di-highlight otomatis."

> **Fallback kalau dashboard belum siap saat rekaman:** ganti shot ini dengan
> `castor analyze ... --json-out report.json`, tunjukkan JSON-nya, lalu bilang
> "output machine-readable ini yang dikonsumsi dashboard dan CI". Jangan pernah
> merekam UI yang setengah jalan — lebih baik terminal yang rapi.

### Shot C — CI regression gate (~20s)

```
castor analyze trajectory.json ; echo "exit code: $?"
```

**Narasi:**
> "Exit code 1 kalau cascade terdeteksi. Jadi ini bisa langsung jadi gate di CI —
> merge yang menurunkan reliabilitas otomatis gagal."

### Shot D — self-healing, the closer (~35s)

```
python examples/self_healing_chain.py
```

**Narasi:**
> "Dan karena Castor tahu langkah mana yang beracun, orchestrator bisa
> mengulang **hanya langkah itu** dengan grounding yang bersih — satu panggilan
> LLM tambahan, bukan mengulang seluruh rantai."

Expected on screen:
```
[analyst] attempt 1 FLAGGED: entailment 0.010 < threshold 0.72
[analyst] healed (attempt 2): ... operating profit Q1 $230,000, Q2 $210,000 ...
```

**Say the honest part — it lands better than hiding it:**
> "Ini pola di luar Castor, bukan fitur bawaan. Selama false positive kami masih
> 27%, kami tidak akan otomatis mengulang langkah di pipeline orang tanpa
> sepengetahuan mereka."

---

## 3:45 – 4:20 · Honest numbers (do not skip — this is your differentiator)

**On screen:** `docs/VALIDATION.md` scrolling, or a table slide.

**Narasi:**
> "Kami buka angkanya. Deteksi 55%, di bawah target kami 70%. Kesalahan
> token-level seperti angka yang salah cuma terdeteksi 29% — embedding memang
> hampir tidak bergeser untuk itu, dan claim-level verification adalah item
> nomor satu kami di v1. Kalibrasi wajib: threshold default dari paper CHARM
> menandai 93% trajectory bersih.
>
> Semua angka ini ada di repo dan bisa direproduksi. Kalau juri clone dan
> menjalankannya, angkanya keluar sama."

> Kalau verdict rule rework sudah selesai sebelum rekaman, tambahkan satu
> kalimat: verdict trajectory-level naik dari 0/24 ke <angka>/24 — dan sebutkan
> ongkos false positive-nya juga.

---

## 4:20 – 4:30 · Close

**On screen:** GitHub repo + Hugging Face dataset link.

**Narasi:**
> "Castor. Bukan memberi tahu bahwa AI kalian berhalusinasi — tapi **di mana**
> mulainya. Open source, MIT, jalan sepenuhnya lokal."

---

## Checklist sebelum submit

- [ ] Durasi 3–5 menit
- [ ] ≥1 menit sisi bisnis
- [ ] ≥2 menit produk benar-benar jalan (bukan slide)
- [ ] Terminal terbaca di layar laptop
- [ ] Audio jelas, tidak ada dead air panjang
- [ ] Link unlisted YouTube / Google Drive, **akses sudah dites dari incognito**
- [ ] Angka yang disebut di video sama persis dengan angka di paper
