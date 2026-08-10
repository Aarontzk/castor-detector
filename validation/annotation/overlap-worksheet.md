# Overlap worksheet — the 10 kappa chains

**For: Farel and Fabio, separately.** These are the only chains that produce
Cohen's kappa, so they must be annotated by hand and independently.

> **Do not open** `annotations-claude.json`, `annotations-farel.json`, or
> `annotations-fabio.json` until you have finished all ten. Agreement is only
> meaningful if neither of you saw anything else first.

This page contains no analysis and no suggested answers, by design.

## For each chain

1. Read the numbered source facts.
2. **Work out the correct answer yourself before reading the steps.**
3. Read steps 1 to 4 in order. Mark the **first** step that deviates from the
   source.
4. Write the label on the answer line, then enter all ten at the end.

## Rules that decide the close calls

- **First deviation wins.** A later step faithfully carrying an earlier error is
  not the origin — it is the cascade.
- **Judge each step against the SOURCE**, not against the step before it.
- **A dropped fact counts** only if the question needs it.
- **Compression is not omission.** The writer step is supposed to be short.
- **`[TRUNCATED]` is not an error.** Judge only the content present.
- **Torn between two steps? Pick the earlier one and say why in notes.**

## Error types

| Type | Test |
|---|---|
| `omission` | A needed fact is **missing**. What is written stays true. |
| `misread` | The fact is **present but its meaning is inverted** or misapplied. |
| `arithmetic` | Right numbers, **wrong calculation**. |
| `fabrication` | A fact, number or rule appears that is **not in the source**. |
| `none` | Only when `cascade_occurred` is false. |

## Entering your answers

```
python validation/annotation/enter_labels.py farel     # or: fabio
```

It prompts chain by chain and writes valid JSON, so no hand-editing.

---


## 1/10 · organic-02

**Question:** Which warehouse should handle the new order of 450 units?

**Source facts:**

1. The Bekasi warehouse has 380 units in stock and can ship within 2 days.

2. The Semarang warehouse has 520 units but needs 5 days to ship.

3. Orders above 400 units may be split between warehouses if needed.

4. The customer requested delivery within 4 days.


**Step 1 — llm**

> The Bekasi warehouse has 380 units and can ship in 2 days, while the Semarang warehouse has 520 units but requires 5 days to ship. Orders above 400 units may be split between warehouses if needed. The customer requested delivery within 4 days.

**Step 2 — llm** `[TRUNCATED]`

> To determine which warehouse should handle the new order of 450 units, let's evaluate both options based on their capacity and the required shipping time. For the Bekasi warehouse: - Capacity: 380 units - Shipping Time: 2 days Since the customer requested delivery within 4 days, the shipping time for the Bekasi warehouse (2 days) is sufficient. However, it only has enough space for 380 units of the order. For the Semarang warehouse: - Capacity: 520 units - Shipping Time: 5 days The shipping time requirement (within 4 days) is less than the required shipping time (5 days), making this option viable. Given that both warehouses can ship within the requested timeline, we should consider the capacity constraint more rigorously. The customer needs to fulfill an order of 450 units. Comparing the two: - Bekasi: Can ship the entire 450 units in 2 days (capacity is sufficient). - Semarang: Also has enough space (5

**Step 3 — llm**

> Conclusion: Based on the analysis, both warehouses can handle the new order of 450 units within the required shipping time. However, the Bekasi warehouse offers a more efficient solution as it can ship all necessary units in just 2 days without requiring additional space. Recommendation: The new order should be shipped from the Bekasi warehouse to ensure timely delivery and maximize operational efficiency.

**Step 4 — llm**

> The Bekasi warehouse is recommended for shipping the new order of 450 units due to its ability to deliver within 2 days and its efficient use of available space.

**Answer:** cascade `true`  ·  origin_step `2`  ·  type `misread`

**Evidence:**"The shipping time requirement (within 4 days) is less than the required shipping time (5 days), making this option viable" + "Bekasi: Can ship the entire 450 units in 2 days (capacity is sufficient)"

**Notes:**Jawaban bener tuh sebenernya gak ada opsi yang lolos. Bekasi cuma 380 unit (kurang dari 450), Semarang stoknya cukup tapi 5 hari padahal maunya 4 hari. Step 1 masih aman, semua fakta kesalin. Step 2 yang ngaco: dia bilang 5 hari masih viable buat deadline 4 hari, ya jelas enggak. Terus bilang Bekasi bisa kirim full 450 padahal stoknya 380. Dua fakta dibalik sekaligus. Step 3-4 tinggal ngikut.

---


## 2/10 · organic-04

**Question:** How many buses are needed for the school trip?

**Source facts:**

1. The school trip includes 174 students and 12 teachers.

2. Each bus seats 45 passengers.

3. Two students use wheelchairs, and each wheelchair space replaces 3 regular seats.

4. School policy requires at least one teacher per bus.


**Step 1 — llm**

> The school trip includes 174 students and 12 teachers, making a total of 186 people. Two students use wheelchairs, replacing 6 regular seats (since each wheelchair space replaces 3 regular seats). School policy requires at least one teacher per bus. Each bus seats 45 passengers.

**Step 2 — llm** `[TRUNCATED]`

> First, we calculate the number of regular seats needed for all students and teachers: - Total people: 174 students + 12 teachers = 186 people. - Subtracting the two wheelchair spaces (for a total of 30 regular seats per wheelchair space): 186 - (2 * 3) = 180 regular seats. Next, we add back for the replacement of regular seats by wheelchairs: - Since each wheelchair replaces 3 regular seats and there are two wheelchair spaces: - Replacement calculation: 6 + (2 * 3) = 12 additional seats needed. Total number of passengers per bus is: - Seats per bus: 45. - Total passengers including teachers: 45 (regular) + 12 (wheelchair replacement) = 57 passengers per bus. Finally, to find the number of buses required: - Total people needing transportation: 186. - Number of buses needed: Ceiling(186 / 57) = 3 buses. Therefore

**Step 3 — llm**

> Based on the analysis provided, a total of 3 buses are needed for the school trip. To further optimize resource utilization and ensure comfort and safety, it is recommended to use a combination of full-sized regular seats and wheelchair spaces on each bus. This approach would allow each bus to accommodate more passengers efficiently while maintaining accessibility requirements.

**Step 4 — llm**

> A total of 3 buses are needed for the school trip, with a recommendation to use a mix of regular seats and wheelchair spaces on each bus for optimal utilization.

**Answer:** cascade `true`  ·  origin_step `2`  ·  type `fabrication`

**Evidence:**"for a total of 30 regular seats per wheelchair space" + "Seats per bus: 45. Total passengers including teachers: 45 (regular) + 12 (wheelchair replacement) = 57 passengers per bus"

**Notes:**Harusnya: 184 orang duduk normal + 2 slot kursi roda (makan 6 kursi) = 190 kursi, 190/45 = 4,2 jadi 5 bus. Guru 12 orang jadi syarat 1 guru per bus aman. Step 1 masih bener kok (186 orang, 6 kursi kepakai). Step 2 tiba-tiba ngarang angka 30 kursi per slot kursi roda sama kapasitas bus 57, dua-duanya gak ada di sumber. Ada salah itung nyusul juga (186/57 = 3,26 dibulatin ke bawah jadi 3), tapi akarnya ya angka karangan tadi. Close call antara fabrication sama misread (arah pengurangannya kebalik), gue ambil fabrication karena angka 57 itu yang nentuin hasil akhir.

---


## 3/10 · organic-08

**Question:** Berapa sisa anggaran proyek dan cukupkah untuk fase akhir?

**Source facts:**

1. Anggaran proyek total 500 juta rupiah.

2. Fase satu menghabiskan 180 juta, fase dua 210 juta.

3. Fase akhir diperkirakan butuh 95 juta rupiah.

4. Ada dana kontingensi terpisah 50 juta yang hanya boleh dipakai dengan persetujuan direksi.


**Step 1 — llm**

> Anggaran total proyek adalah 500 juta rupiah. Fase akhir diperkirakan butuh 95 juta rupiah. Ada dana kontingensi terpisah sebesar 50 juta yang hanya boleh dipakai dengan persetujuan direksi.

**Step 2 — llm** `[TRUNCATED]`

> Based on the provided facts, here's how we can calculate the remaining budget for the project and determine if it is sufficient for the final phase: 1. Total available budget: 500 juta rupiah. 2. Budget needed for the final phase: 95 juta rupiah. 3. Contingency fund available (under director's approval): 50 juta rupiah. To find the remaining budget after allocating for the final phase and considering the contingency fund, we subtract the required budget from the total budget: Remaining budget = Total budget - Budget needed for final phase Remaining budget = 500 juta - 95 juta Remaining budget = 405 juta rupiah. If the contingency fund is approved, it can be added to this remaining budget: Total available budget after approval of contingency: Remaining budget + Contingency fund Total available budget after approval of contingency: 405 juta + 50 juta Total available budget after approval of contingency = 455 juta

**Step 3 — llm**

> Based on the analysis, there is a remaining budget of 455 million rupiah after allocating for the final phase and considering the approved contingency fund. However, this amount may not be sufficient to cover all potential unforeseen costs in the final phase. A recommendation would be to reassess and potentially increase the contingency fund or explore other cost-saving measures to ensure adequate resources are available for the project's completion.

**Step 4 — llm**

> The remaining budget for the final phase is 455 million rupiah, but this might not cover unforeseen costs. It is recommended to reassess and possibly increase the contingency fund or seek additional savings for a secure project completion.

**Answer:** cascade `true`  ·  origin_step `1`  ·  type `omission`

**Evidence:**Step 1 gak nyebut fakta 2 sama sekali ("Fase satu menghabiskan 180 juta, fase dua 210 juta")

**Notes:**Harusnya sisa = 500 - 180 - 210 = 110 juta, cukup buat fase akhir 95 juta, sisa 15 juta, gak perlu nyentuh kontingensi. Step 1 lupa nyalin pengeluaran fase 1 sama fase 2, padahal itu justru inti pertanyaannya. Gara-gara itu step 2 ngitungnya jadi 500 - 95, terus malah nambahin kontingensi yang belum disetujui direksi. Tapi itu efek samping, bukan sumbernya.

---


## 4/10 · organic-12

**Question:** Is the night shift adequately staffed for the ICU?

**Source facts:**

1. Hospital policy requires 1 nurse per 4 patients on the night shift.

2. The ICU currently has 18 patients.

3. 5 nurses are rostered for the night shift.

4. One of the rostered nurses is a trainee who counts as half a staff unit under policy.


**Step 1 — llm**

> The hospital policy requires 1 nurse per 4 patients on the night shift. The ICU currently has 18 patients. 5 nurses are rostered for the night shift, including a trainee who counts as half a staff unit.

**Step 2 — llm**

> To determine if the night shift is adequately staffed for the ICU, we need to calculate the required number of nurses based on hospital policy and compare it with the actual staffing. 1. **Calculate Required Nurses:** - According to the policy, 1 nurse is needed per every 4 patients. - There are currently 18 patients in the ICU. - Number of required nurses = \( \frac{18}{4} = 4.5 \). 2. **Consider Actual Staffing:** - Rostered for the night shift includes 5 nurses, with a trainee counted as half a staff unit. - Total actual staffing units = 5 + (0.5) = 5.5. 3. **Compare Required and Actual Staffing:** - Required nurses (4.5) < Actual staffing units (5.5). Therefore, the night shift is adequately staffed for the ICU based on the calculation.

**Step 3 — llm**

> **Conclusion:** The night shift in the ICU is adequately staffed with 5.5 nurses compared to the required 4.5 nurses based on patient-to-nurse ratio policy. **Recommendation:** Although currently adequate, it may be beneficial to review and potentially increase the staffing levels during peak hours or if there are plans for increased patient volumes in the future.

**Step 4 — llm**

> The night shift in the ICU is adequately staffed with 5.5 nurses compared to the required 4.5 based on patient-to-nurse ratio policy, but it may be beneficial to review and potentially increase staffing levels during peak hours or if there are plans for increased patient volumes.

**Answer:** cascade `true`  ·  origin_step `2`  ·  type `misread`

**Evidence:**"Total actual staffing units = 5 + (0.5) = 5.5"

**Notes:**Butuhnya 18/4 = 4,5 unit. Yang ada = 4 perawat penuh + trainee 0,5 = 4,5. Pas mepet, bukan "aman dengan margin". Trainee-nya kan salah satu dari 5 yang dirosterin, bukan orang ke-6. Step 1 udah nulis bener "including a trainee", eh step 2 malah ngitung 5 + 0,5. Faktanya ada tapi dibaca kebalik, makanya misread bukan arithmetic.

---


## 5/10 · organic-13

**Question:** Apakah stok cukup untuk memenuhi pesanan 600 unit minggu ini?

**Source facts:**

1. Gudang Cikarang memiliki 340 unit siap kirim.

2. Gudang Bandung memiliki 410 unit, namun 80 unit di antaranya sudah dialokasikan untuk pesanan lain yang belum dibatalkan.

3. Pengiriman antar gudang membutuhkan waktu 1 hari kerja.


**Step 1 — llm**

> Gudang Cikarang memiliki 340 unit siap kirim. Gudang Bandung memiliki 410 unit, namun hanya 330 unit yang siap dikirim (410 - 80). Pengiriman antar gudang membutuhkan waktu 1 hari kerja.

**Step 2 — llm**

> To determine if the stock is sufficient to fulfill the order of 600 units this week, we need to consider the available stock across all locations. Gudang Cikarang has 340 units ready for shipment. Gudang Bandung initially has 410 units but only 330 are ready (410 - 80). Total ready units = Units in Gudang Cikarang + Units ready in Gudang Bandung = 340 + 330 = 670 units Since the total number of units ready for shipment is 670, which is more than the required 600 units, we can conclude that the stock is sufficient to fulfill the order.

**Step 3 — llm**

> Based on the analysis, the stock is sufficient to fulfill the order of 600 units this week as there are a total of 670 ready units across all locations. To further optimize operations and ensure future orders are met with minimal disruptions, it is recommended that Gudang Bandung should aim for consistent readiness of its stock, ideally reaching full capacity (410 units) in the long term.

**Step 4 — llm**

> The stock of 670 units across all locations is sufficient to fulfill this week's order of 600 units. To ensure future orders are met without disruptions, Gudang Bandung should strive for consistent readiness at full capacity.

**Answer:** cascade `false`  ·  origin_step `null`  ·  type `none`

**Evidence:**Step 1 udah bener ngurangin 80 unit yang dialokasi (410 - 80 = 330), step 2 jumlahin 340 + 330 = 670 > 600

**Notes:**Aman

---


## 6/10 · organic-14

**Question:** How much overtime pay is owed to the employee this week?

**Source facts:**

1. Employee Chen worked 46 hours this week.

2. The standard work week is 40 hours, and overtime is paid at 1.5 times the base hourly rate of 22 dollars.

3. The first 2 overtime hours each week are paid at the standard rate as part of a flexible-hours pilot program still in effect this quarter.


**Step 1 — llm**

> Employee Chen worked 46 hours, which includes 6 overtime hours (46 - 40 = 6). The base hourly rate is $22. Overtime pay is at 1.5 times the base rate, making it $33 per hour for these additional hours.

**Step 2 — llm**

> To determine how much overtime pay is owed to Employee Chen this week, we can follow these steps: 1. Calculate the number of overtime hours worked: Chen worked 46 hours - standard workweek (typically 40 hours) = 6 overtime hours. 2. Determine the overtime rate: Overtime pay is at 1.5 times the base hourly rate. Base hourly rate = $22 Overtime hourly rate = $22 * 1.5 = $33 per hour 3. Calculate the total overtime pay owed: Total overtime pay = Number of overtime hours * Overtime hourly rate Total overtime pay = 6 * $33 = $198 Therefore, Employee Chen is owed $198 in overtime pay for this week.

**Step 3 — llm**

> Based on the analysis provided, Employee Chen is owed $198 in overtime pay for this week. To further improve efficiency and prevent similar calculations from being necessary in future weeks, it's recommended that regular timekeeping checks be implemented to automatically identify and process overtime payments accurately and promptly.

**Step 4 — llm**

> Employee Chen is owed $198 in overtime pay for this week. Regular timekeeping checks are recommended to avoid future errors.

**Answer:** cascade `true`  ·  origin_step `1`  ·  type `omission`

**Evidence:**Step 1 buang fakta 3 ("The first 2 overtime hours each week are paid at the standard rate")

**Notes:**Harusnya 2 jam pertama di rate normal (2 × 22 = 44), sisa 4 jam 1,5x (4 × 33 = 132), total 176 dolar. Step 1 bukan cuma ilangin, tapi malah negesin semua 6 jam dihitung 33. Program pilot-nya masih jalan kuartal ini jadi faktanya kepake. Step 2 sampe 4 tinggal warisin.

---


## 7/10 · organic-15

**Question:** Is the prescribed dosage within the safe daily limit?

**Source facts:**

1. The maximum safe daily dose of the medication is 60 mg per day for adult patients.

2. The patient is prescribed 15 mg three times a day.

3. Patients over 65 years old require a reduced maximum of 45 mg per day.

4. The patient's chart lists their age as 68.


**Step 1 — llm**

> The maximum safe daily dose for adult patients is 60 mg. The patient is prescribed 15 mg three times a day, totaling 45 mg per day. Patients over 65 years old have a reduced maximum of 45 mg per day. The patient's age listed in the chart is 68.

**Step 2 — llm**

> Based on the provided facts: - For adult patients under 65, the maximum safe daily dose is 60 mg. - The prescribed dosage for this patient (15 mg three times a day) totals to 45 mg per day. - Patients over 65 have a reduced maximum of 45 mg per day. Given that the patient's age is listed as 68, which falls into the "over 65" category: The prescribed dosage of 15 mg three times a day (totaling 45 mg) aligns with the reduced maximum safe daily limit for patients over 65. Therefore, it means the prescribed dosage is within the safe daily limit for this patient.

**Step 3 — llm**

> Conclusion: The prescribed dosage of 15 mg three times a day is within the safe daily limit for the patient, who is over 65 years old. Recommendation: Continue with the current prescription as it adheres to the recommended safety guidelines for the patient's age group.

**Step 4 — llm**

> The safe daily limit for the prescribed dosage of 15 mg three times a day is within the recommended range for patients over 65 years old, so continue with the current prescription.

**Answer:** cascade `false`  ·  origin_step `null`  ·  type `none`

**Evidence:**"Given that the patient's age is listed as 68, which falls into the 'over 65' category"

**Notes:**Pasien 68 tahun, batasnya 45 mg. Resep 15 × 3 = 45, pas di batas, masih aman. Step 4 kalimatnya emang belibet ("The safe daily limit for the prescribed dosage... is within the recommended range"), tapi isinya gak nyimpang dari sumber.

---


## 8/10 · organic-20

**Question:** What is the customer's total electricity bill for the month?

**Source facts:**

1. The utility charges 0.12 dollars per kWh for the first 500 kWh and 0.18 dollars per kWh above that.

2. The customer used 640 kWh this month.

3. A fixed 15 dollar service fee applies, but is waived for customers enrolled in autopay, which this customer joined last month.


**Step 1 — llm**

> The utility charges $0.12 per kWh for the first 500 kWh and $0.18 per kWh above that. The customer used 640 kWh. A fixed $15 service fee applies, but is waived due to autopay enrollment.

**Step 2 — llm** `[TRUNCATED]`

> To calculate the total electricity bill: - First, compute the cost for the first 500 kWh: \(500 \text{ kWh} \times \$0.12/\text{kWh} = \$60\). - Then, compute the cost for the remaining 140 kWh (640 - 500): \(140 \text{ kWh} \times \$0.18/\text{kWh} = \$25.20\). - The service fee is $15 but waived. Thus, the total electricity bill for the customer is: \[ \$60 + \$25.20 = \$85.20. \]

**Step 3 — llm**

> The customer's total electricity bill for the month is $85.20. To further improve efficiency and reduce costs in future billing cycles, it would be recommended to identify if there are any opportunities to increase energy efficiency or negotiate a lower rate for higher consumption levels above 640 kWh.

**Step 4 — llm**

> The customer's total electricity bill for the month is $85.20. For future efficiency and cost reduction, consider increasing energy efficiency or negotiating a lower rate for higher consumption.

**Answer:** cascade `false`  ·  origin_step `null`  ·  type `none`

**Evidence:**Step 1 nangkep pembebasan biaya autopay, step 2 ngitung tier bener: 60 + 25,20 = 85,20

**Notes:**Step 3 nyeletuk soal "negotiating a lower rate for higher consumption levels above 640 kWh" padahal ambang tier-nya 500. Tapi itu kalimat rekomendasi tempelan, gak nyentuh angka tagihan, jadi gue anggap bukan error.

---


## 9/10 · organic-26

**Question:** Does the buyer qualify for the loan under the debt-to-income limit?

**Source facts:**

1. The lender requires a debt-to-income ratio no higher than 43 percent.

2. The buyer's gross monthly income is 7,000 dollars and existing monthly debts total 1,800 dollars.

3. The proposed mortgage payment would be 1,400 dollars per month.

4. The buyer also co-signed a car loan for a family member with a 250 dollar monthly payment that does not appear on the buyer's own credit report.


**Step 1 — llm**

> The lender requires a debt-to-income ratio no higher than 43 percent. The buyer's gross monthly income is $7,000 and existing monthly debts total $1,800. A proposed mortgage payment would add another $1,400 per month to the buyer's expenses. Additionally, the buyer co-signed a car loan with a monthly payment of $250 that does not appear on their own credit report.

**Step 2 — llm**

> To determine if the buyer qualifies for the loan under the debt-to-income limit, we need to calculate the total monthly obligations and compare them to the allowed 43% ratio based on gross income. Total existing monthly debts: $1,800 (current debts) Proposed mortgage payment: $1,400 Car loan payments that do not appear on their own credit report: $250 Total monthly obligations = $1,800 + $1,400 + $250 = $3,450 Debt-to-income ratio = (Total monthly obligations / Gross monthly income) * 100 = ($3,450 / $7,000) * 100 ≈ 49.29% Since the debt-to-income ratio of approximately 49.29% exceeds the lender's limit of 43%, the buyer does not qualify for the loan under the debt-to-income limit.

**Step 3 — llm**

> Based on the analysis, the buyer does not qualify for the loan under the debt-to-income limit due to a ratio exceeding 43%. To address this, I recommend that the buyer explore ways to reduce their monthly obligations or increase their income before applying again.

**Step 4 — llm**

> The buyer does not qualify for the loan because their debt-to-income ratio exceeds 43%, making it ineligible under current limits. To proceed, they should consider reducing monthly obligations or increasing their income.

**Answer:** cascade `true`  ·  origin_step `2`  ·  type `misread`

**Evidence:**"Car loan payments that do not appear on their own credit report: $250 ... Total monthly obligations = $1,800 + $1,400 + $250 = $3,450"

**Notes:**Cicilan co-sign 250 itu gak muncul di credit report pemohon, artinya lender gak ngitung. Jadi DTI = 3.200/7.000 = 45,7%, tetep di atas 43%, tetep gak lolos. Step 1 nyalin kualifikasinya dengan bener, step 2 ngakuin kualifikasinya tapi tetep masukin ke itungan. Kesimpulan akhirnya kebetulan bener, tapi rasionya salah (49,29% vs 45,7%), jadi cascade-nya tetep kejadian di level penalaran. Kalau tim lo mendefinisikan cascade harus sampai ngubah verdict akhir, chain ini perlu dibahas dulu.

---


## 10/10 · organic-27

**Question:** Is the team under the salary cap after the new signing?

**Source facts:**

1. The league salary cap is 118 million dollars.

2. The team's current committed salary is 109 million dollars.

3. The new signing adds a 12 million dollar salary.

4. Players on rookie contracts count at only 50 percent of their listed salary against the cap in their first year, and the new signee is on a rookie contract.


**Step 1 — llm**

> The league salary cap is $118 million. The team's current committed salary is $109 million. A new player with a salary of $12 million is joining the team, who is on a rookie contract counted at 50% in their first year.

**Step 2 — llm**

> To determine if the team will be under the salary cap after signing the new player, we need to calculate the total committed salary including the rookie discount. The current committed salary is $109 million. The rookie player's salary for the first year at 50% is calculated as follows: \[ \text{Rookie Salary} = \$12 \text{ million} \times 0.5 = \$6 \text{ million} \] Adding this to the current committed salary gives us: \[ \text{Total Committed Salary} = \$109 \text{ million} + \$6 \text{ million} = \$115 \text{ million} \] Since the total committed salary of $115 million is less than the league salary cap of $118 million, the team will be under the salary cap after this new signing.

**Step 3 — llm**

> Based on the analysis, the team will indeed be under the salary cap after the new signing. To ensure they remain compliant with labor laws and maintain financial stability in the long term, it is recommended that the team implements a strategic plan to monitor potential future overages and adjust their roster accordingly.

**Step 4 — llm**

> The team will be under the salary cap after the new signing, but it's recommended they implement a strategy for ongoing monitoring and adjustments.

**Answer:** cascade `false`  ·  origin_step `null`  ·  type `none`

**Evidence:**

**Notes:**

---
