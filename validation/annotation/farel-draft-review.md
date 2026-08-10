# Verification sheet — Farel's 9 single chains

Machine draft, **pending your verification**. Every record in
`annotations-farel.json` carries `verified_by_human: false` until you change it.

The 10 overlap chains are NOT here and must not be: they are the Cohen's kappa
source and have to be annotated by hand, without reading any other labels.

For each chain below: read the source, check the quoted origin step, then either
flip `verified_by_human` to `true` in the form, or correct the label first.

**Independent cross-check.** This draft was produced without reading
`annotations-claude.json`. Comparing afterwards: **origin step agrees 9/9**,
error type agrees 8/9. The one disagreement is flagged below and is yours to
settle.

---

## organic-03 — Is the reactor within safe operating limits?

**Source:**

> The cooling system operates safely between 40 and 75 degrees Celsius. Sensor A reads 71 degrees, sensor B reads 68 degrees. Sensor A was flagged last month for reading 3 degrees too high and is scheduled for recalibration. Readings above 74 degrees require immediate shutdown.

**Proposed origin — step 1 (llm):**

> The cooling system operates safely between 40 and 75 degrees Celsius. Sensor A reads 71 degrees, and Sensor B reads 68 degrees. The readings are below the upper limit of 75 degrees.

**Label:** `cascade=true` · `origin_step=1` · `error_type=omission`

**Why:** Drops both the sensor-A '3 degrees too high' calibration flag and the 'above 74 degrees require immediate shutdown' rule, keeping only the 40-75 safe range. The 74 shutdown threshold is the operative rule for this question and it is replaced by the wrong number (75).

**Notes:** Final answer (reactor is safe) stays correct by coincidence: 71 read minus the 3-degree offset is 68, and 68 < 74 either way. Step 4 additionally fabricates 'both sensors at 74 degrees Celsius', which matches neither sensor.

- [ ] verified

---

## organic-05 — Did the marketing campaign meet its target?

**Source:**

> The campaign targeted 3,000 new sign-ups with a budget of 20,000 dollars. It achieved 3,420 sign-ups but spent 24,500 dollars. The cost-per-signup target was 7 dollars. Sign-ups from the partner channel, 400 of the total, are excluded from the campaign's own performance count.

**Proposed origin — step 1 (llm):**

> The campaign targeted 3,000 new sign-ups with a budget of $20,000. It achieved 3,420 sign-ups but spent $24,500. The cost-per-signup target was $7. Sign-ups from the partner channel were excluded from the performance count.

**Label:** `cascade=true` · `origin_step=1` · `error_type=omission`

**Why:** Keeps the partner-channel exclusion rule but drops the quantity it applies to (400 of the 3,420 sign-ups), which makes the exclusion impossible to apply downstream.

**Notes:** Correct figures: own sign-ups 3,420 - 400 = 3,020, which still beats the 3,000 target; cost per sign-up 24,500 / 3,020 = $8.11 against a $7 target. Step 2 instead divides by the full 3,420 and reports $7.13, and never checks the sign-up target at all. Borderline step 1 vs step 2 - chose step 1 per GUIDE rule 6, because the number was already gone.

- [ ] verified

---

## organic-06 — Kapan sebaiknya panen dilakukan?

**Source:**

> Padi varietas Ciherang biasanya dipanen 115 sampai 125 hari setelah tanam. Sawah ini ditanami tanggal 10 Maret. Curah hujan tinggi diperkirakan mulai minggu kedua Juli. Panen saat hujan menurunkan kualitas gabah dan menaikkan biaya pengeringan sekitar 20 persen.

**Proposed origin — step 1 (llm):**

> Panenan varietas Ciherang biasanya dilakukan antara 115 sampai 125 hari setelah tanam. Curah hujan tinggi mulai pada minggu kedua Juli, yang dapat berdampak negatif pada kualitas gabah dan meningkatkan biaya pengeringan sekitar 20%.

**Label:** `cascade=true` · `origin_step=1` · `error_type=omission`

**Why:** Drops the planting date (10 Maret). Without it, '115 sampai 125 hari setelah tanam' cannot be converted into a date, and the question asks for a date.

**Notes:** Correct window is 3-13 July (10 March + 115 to 125 days), which straddles the onset of heavy rain in the second week of July, so the answer should be to harvest at the early end, before roughly 7 July. Steps 2-4 never compute any date and answer only in relative terms.

- [ ] verified

---

## organic-09 — What is the company's net profit after tax for Q3?

**Source:**

> Bright Foods Ltd reported Q3 revenue of 1,250,000 dollars and operating costs of 890,000 dollars. Corporate tax is charged at 22 percent on operating profit. A one-time equipment write-off of 40,000 dollars is deducted before tax but excluded from operating profit reporting.

**Proposed origin — step 1 (llm):**

> Bright Foods Ltd reported a revenue of $1,250,000 and operating costs of $890,000 in Q3. Corporate tax at 22% is applied to the operating profit, which excludes a one-time equipment write-off of $40,000 from tax calculations but does not affect operating profit reporting.

**Label:** `cascade=true` · `origin_step=1` · `error_type=misread`

**Why:** Source: the write-off is 'deducted before tax but excluded from operating profit reporting'. Step 1 renders it as excluding the write-off 'from tax calculations', inverting the treatment - deducted before tax reduces the taxable base, excluded from tax ignores it.

**Notes:** Step 2 compounds this by ADDING the write-off into operating profit (Revenue - Costs + Write-off) and then miscomputing even that formula as $300,000 when it gives $400,000. Correct chain: operating profit $360,000, taxable $320,000, tax $70,400, net $249,600. Borderline step 1 vs step 2; chose step 1 because the inversion is already there.

- [ ] verified

---

## organic-10 — Can the driver complete both deliveries within the same shift?

**Source:**

> Driver Morales starts his shift at 08:00 and works a maximum of 9 hours including a mandatory 30-minute break. Delivery A takes 3 hours 15 minutes round trip. Delivery B takes 4 hours 45 minutes round trip. Delivery B requires a signed customs form only if the shipment crosses the state line, which adds 20 minutes.

**Proposed origin — step 1 (llm):**

> Morales starts his shift at 08:00 and works a maximum of 9 hours including a mandatory 30-minute break. Delivery A takes 3 hours and 15 minutes, and Delivery B takes 4 hours and 45 minutes round trip. Adding the necessary customs form processing time for Delivery B adds an additional 20 minutes.

**Label:** `cascade=true` · `origin_step=1` · `error_type=misread`

**Why:** The 20-minute customs form is conditional in the source ('only if the shipment crosses the state line'). Step 1 states it as unconditional: 'Adding the necessary customs form processing time ... adds an additional 20 minutes.'

**Notes:** Two further independent errors downstream: step 2 reads 'maximum of 9 hours including a mandatory 30-minute break' as '9-hour shift (excluding breaks)', and step 3 concludes 'cannot' from its own total of 8.333 h against a 9 h limit. Correct answer is YES and it fits either way: 8:00 driving + 0:20 customs + 0:30 break = 8:50 <= 9:00.

- [ ] verified

---

## organic-18 — How much of the claim will the insurer reimburse?

> ⚠️ **DISAGREEMENT — decide this one yourself.**
>
> draft: step 2 `misread` · other machine pass: step 2 `fabrication`

**Source:**

> The policy covers water damage up to 10,000 dollars per incident with a 500 dollar deductible. The claim submitted totals 8,200 dollars in damage. Damage caused by gradual leaks rather than sudden incidents is excluded from coverage, and the inspector's report flags 1,500 dollars of the claim as gradual-leak damage.

**Proposed origin — step 2 (llm):**

> To determine how much the insurer will reimburse, we first need to identify which part of the claim is covered by the policy: water damage up to $10,000 per incident with a $500 deductible. The total submitted claim is $8,200. Out of this, $1,500 is for gradual leaks and not covered under the policy. Therefore, we need to calculate the amount after applying the deductible to the remaining water damage portion: Remaining claim amount (after excluding leaks): $8,200 - $1,500 = $6,700 Since the policy covers up to $10,000 per incident with a $500 deductible, the insurer will reimburse $9,700 for this incident ($10,000 total coverage - $300 remaining deductible). Thus, the reimbursement amount i…

**Label:** `cascade=true` · `origin_step=2` · `error_type=misread`

**Why:** Computes the covered amount correctly ($8,200 - $1,500 = $6,700) then discards it and treats the $10,000 policy CAP as the payout base: '$10,000 total coverage - $300 remaining deductible' = $9,700, which exceeds the entire $8,200 claim.

**Notes:** Step 1 carried every fact faithfully. The '$300 remaining deductible' is also fabricated - $300 appears nowhere in the source - but the misread of a ceiling as an entitlement is what produced the wrong answer, so per GUIDE that is the type. Correct: $6,700 - $500 = $6,200.

- [ ] verified

---

## organic-21 — Apakah anggaran BBM bulan ini cukup untuk seluruh rute pengiriman?

**Source:**

> Anggaran BBM bulan ini sebesar 8 juta rupiah. Rute reguler membutuhkan 5.2 juta rupiah. Ada 2 rute tambahan musiman yang masing-masing membutuhkan 1.4 juta rupiah, tapi salah satu rute tambahan dibiayai terpisah oleh klien dan tidak masuk anggaran internal.

**Proposed origin — step 2 (llm):**

> Based on the provided facts, let's break down the information step by step to answer the question: 1. The budget for gasoline is set at 8 million rupiah. 2. This budget will cover all routes, which include: - Regular routes: 5.2 million rupiah (total for these routes) - Additional seasonal routes: 2.8 million rupiah (1.4 million each) 3. There's an additional route that was not included in the internal budget but is paid by the client. Let's calculate: - Total required for all routes = 5.2 million + 2.8 million = 8 million rupiah. - Since there are no leftover amounts, and the total budget exactly matches the total requirement (8 million), it means the budget of 8 million rupiah is indeed su…

**Label:** `cascade=true` · `origin_step=2` · `error_type=misread`

**Why:** Lists the client-funded route as excluded from the internal budget in its own point 3, then computes internal cost as 5.2 + 2.8 = 8 juta anyway and concludes the budget 'exactly matches' with no surplus.

**Notes:** Correct internal cost is 5.2 + 1.4 = 6.6 juta, leaving a 1.4 juta surplus. The final answer ('cukup') is coincidentally right but the margin is wrong. Step 1 kept every source fact including the exclusion, though it editorialises 'diprediksi sudah mencukupi'; borderline step 1 vs 2, chose step 2 because step 1 dropped and inverted nothing.

- [ ] verified

---

## organic-23 — Has the appeal been filed within the legal deadline?

**Source:**

> The appeal must be filed within 30 calendar days of the ruling, issued on March 3rd. The filing was submitted on April 1st. Court holidays do not extend the deadline, but the filing window pauses for court closures, and the court was closed for 3 days in late March for a facility issue.

**Proposed origin — step 1 (llm):**

> The appeal must be filed within 30 calendar days of the ruling on March 3rd. The filing was submitted on April 1st. Court closures and holidays do not extend the deadline, but there were 3 court closures in late March.

**Label:** `cascade=true` · `origin_step=1` · `error_type=misread`

**Why:** Source states two different rules: 'Court holidays do not extend the deadline, but the filing window pauses for court closures'. Step 1 collapses them into 'Court closures and holidays do not extend the deadline', inverting the closure rule.

**Notes:** Final answer (filed in time) is coincidentally correct: April 1 beats the April 2 base deadline even without the 3-day pause that would move it to April 5. Step 2 also invents a garbled range, '30 days from March 3rd would fall between March 24th and April 3rd'.

- [ ] verified

---

## organic-28 — Will the customer be charged before their trial ends?

**Source:**

> The free trial lasts 14 days from signup on June 1st. Billing occurs automatically at the start of day 15 unless canceled. The customer canceled on June 10th, but cancellations submitted after 6 PM are processed the next calendar day per the terms of service, and the cancellation was submitted at 9 PM on June 10th.

**Proposed origin — step 1 (llm):**

> The free trial lasts for 14 days from signup on June 1st. The customer canceled on June 10th, but cancellations after 6 PM are processed the next calendar day. Cancellations submitted at 9 PM on June 10th would not result in charging before the end of the trial.

**Label:** `cascade=true` · `origin_step=1` · `error_type=omission`

**Why:** Drops 'Billing occurs automatically at the start of day 15 unless canceled' - the rule the question turns on - and substitutes its own conclusion instead.

**Notes:** Step 2 then fabricates a rule found nowhere in the source ('within the first 6 days (until June 5th) where cancellations are processed immediately') and places June 10 inside it. Correct: cancellation at 9 PM on June 10 is processed June 11, billing would fall on June 15, so no charge. Borderline - step 2's fabrication is the more severe error, but step 1's omission comes first.

- [ ] verified

---
