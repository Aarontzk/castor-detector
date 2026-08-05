"""Second batch of semi-natural trajectories (owner request K8): 20 more
chains through the same qwen2.5:3b information-bottleneck setup as
agent_chain.py. Writes organic-09..28 into validation/organic/.

Run:  .venv/Scripts/python validation/agent_chain_batch2.py
"""
from __future__ import annotations

import json

from agent_chain import OUT_DIR, run_chain

TASKS = [
    {
        "id": "organic-09",
        "question": "What is the company's net profit after tax for Q3?",
        "source": "Bright Foods Ltd reported Q3 revenue of 1,250,000 dollars and operating costs of 890,000 dollars. Corporate tax is charged at 22 percent on operating profit. A one-time equipment write-off of 40,000 dollars is deducted before tax but excluded from operating profit reporting.",
    },
    {
        "id": "organic-10",
        "question": "Can the driver complete both deliveries within the same shift?",
        "source": "Driver Morales starts his shift at 08:00 and works a maximum of 9 hours including a mandatory 30-minute break. Delivery A takes 3 hours 15 minutes round trip. Delivery B takes 4 hours 45 minutes round trip. Delivery B requires a signed customs form only if the shipment crosses the state line, which adds 20 minutes.",
    },
    {
        "id": "organic-11",
        "question": "Is the pipeline pressure within safe limits?",
        "source": "The pipeline's safe operating pressure is between 120 and 180 psi. Gauge 1 currently reads 165 psi, gauge 2 reads 158 psi. Gauge 1 has a known calibration drift of plus 6 psi and is due for service next week. Pressure above 175 psi triggers automatic shutdown.",
    },
    {
        "id": "organic-12",
        "question": "Is the night shift adequately staffed for the ICU?",
        "source": "Hospital policy requires 1 nurse per 4 patients on the night shift. The ICU currently has 18 patients. 5 nurses are rostered for the night shift. One of the rostered nurses is a trainee who counts as half a staff unit under policy.",
    },
    {
        "id": "organic-13",
        "question": "Apakah stok cukup untuk memenuhi pesanan 600 unit minggu ini?",
        "source": "Gudang Cikarang memiliki 340 unit siap kirim. Gudang Bandung memiliki 410 unit, namun 80 unit di antaranya sudah dialokasikan untuk pesanan lain yang belum dibatalkan. Pengiriman antar gudang membutuhkan waktu 1 hari kerja.",
    },
    {
        "id": "organic-14",
        "question": "How much overtime pay is owed to the employee this week?",
        "source": "Employee Chen worked 46 hours this week. The standard work week is 40 hours, and overtime is paid at 1.5 times the base hourly rate of 22 dollars. The first 2 overtime hours each week are paid at the standard rate as part of a flexible-hours pilot program still in effect this quarter.",
    },
    {
        "id": "organic-15",
        "question": "Is the prescribed dosage within the safe daily limit?",
        "source": "The maximum safe daily dose of the medication is 60 mg per day for adult patients. The patient is prescribed 15 mg three times a day. Patients over 65 years old require a reduced maximum of 45 mg per day. The patient's chart lists their age as 68.",
    },
    {
        "id": "organic-16",
        "question": "Is there enough cement on site to finish the foundation pour?",
        "source": "The foundation pour requires 85 bags of cement. The site currently has 70 bags in the main storage and 25 bags in the secondary shed. 10 bags in the secondary shed are reserved for a separate retaining-wall job and are not available for the foundation.",
    },
    {
        "id": "organic-17",
        "question": "Apakah jadwal irigasi perlu diubah minggu ini?",
        "source": "Tanaman jagung membutuhkan penyiraman setiap 3 hari dengan curah air minimal 20 mm. Curah hujan alami minggu ini tercatat 15 mm pada hari Selasa. Sensor kelembaban tanah sempat rusak selama 2 hari dan datanya untuk periode itu tidak dapat dipakai.",
    },
    {
        "id": "organic-18",
        "question": "How much of the claim will the insurer reimburse?",
        "source": "The policy covers water damage up to 10,000 dollars per incident with a 500 dollar deductible. The claim submitted totals 8,200 dollars in damage. Damage caused by gradual leaks rather than sudden incidents is excluded from coverage, and the inspector's report flags 1,500 dollars of the claim as gradual-leak damage.",
    },
    {
        "id": "organic-19",
        "question": "What is the final price the customer pays for the jacket?",
        "source": "The jacket is listed at 120 dollars. A storewide 20 percent discount applies today. The customer also has a 10 dollar loyalty coupon. Store policy states percentage discounts and dollar coupons cannot be combined on clearance items, and this jacket was moved to clearance yesterday.",
    },
    {
        "id": "organic-20",
        "question": "What is the customer's total electricity bill for the month?",
        "source": "The utility charges 0.12 dollars per kWh for the first 500 kWh and 0.18 dollars per kWh above that. The customer used 640 kWh this month. A fixed 15 dollar service fee applies, but is waived for customers enrolled in autopay, which this customer joined last month.",
    },
    {
        "id": "organic-21",
        "question": "Apakah anggaran BBM bulan ini cukup untuk seluruh rute pengiriman?",
        "source": "Anggaran BBM bulan ini sebesar 8 juta rupiah. Rute reguler membutuhkan 5.2 juta rupiah. Ada 2 rute tambahan musiman yang masing-masing membutuhkan 1.4 juta rupiah, tapi salah satu rute tambahan dibiayai terpisah oleh klien dan tidak masuk anggaran internal.",
    },
    {
        "id": "organic-22",
        "question": "Will the server cluster handle the expected traffic spike?",
        "source": "The cluster currently handles 4,000 requests per second at peak with 6 nodes active. Each node supports roughly 700 requests per second. The upcoming event is expected to bring 5,200 requests per second. One node is scheduled for maintenance during the event window and will be offline.",
    },
    {
        "id": "organic-23",
        "question": "Has the appeal been filed within the legal deadline?",
        "source": "The appeal must be filed within 30 calendar days of the ruling, issued on March 3rd. The filing was submitted on April 1st. Court holidays do not extend the deadline, but the filing window pauses for court closures, and the court was closed for 3 days in late March for a facility issue.",
    },
    {
        "id": "organic-24",
        "question": "Has enough food been ordered for the conference lunch?",
        "source": "The conference has 240 registered attendees. Catering was ordered for 220 meals based on typical no-show rates. A workshop added late brought 15 additional confirmed attendees who are not yet reflected in the catering count. Historical no-show rate is about 8 percent.",
    },
    {
        "id": "organic-25",
        "question": "Apakah kelas tambahan perlu dibuka untuk semester ini?",
        "source": "Kapasitas maksimal per kelas adalah 32 siswa. Jumlah pendaftar saat ini 95 siswa untuk 3 kelas paralel yang sudah ada. Ada 8 siswa pindahan yang baru dikonfirmasi minggu ini dan belum masuk hitungan pendaftar di atas.",
    },
    {
        "id": "organic-26",
        "question": "Does the buyer qualify for the loan under the debt-to-income limit?",
        "source": "The lender requires a debt-to-income ratio no higher than 43 percent. The buyer's gross monthly income is 7,000 dollars and existing monthly debts total 1,800 dollars. The proposed mortgage payment would be 1,400 dollars per month. The buyer also co-signed a car loan for a family member with a 250 dollar monthly payment that does not appear on the buyer's own credit report.",
    },
    {
        "id": "organic-27",
        "question": "Is the team under the salary cap after the new signing?",
        "source": "The league salary cap is 118 million dollars. The team's current committed salary is 109 million dollars. The new signing adds a 12 million dollar salary. Players on rookie contracts count at only 50 percent of their listed salary against the cap in their first year, and the new signee is on a rookie contract.",
    },
    {
        "id": "organic-28",
        "question": "Will the customer be charged before their trial ends?",
        "source": "The free trial lasts 14 days from signup on June 1st. Billing occurs automatically at the start of day 15 unless canceled. The customer canceled on June 10th, but cancellations submitted after 6 PM are processed the next calendar day per the terms of service, and the cancellation was submitted at 9 PM on June 10th.",
    },
]


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for task in TASKS:
        print(f"{task['id']}: {task['question']}")
        result = run_chain(task)
        out = OUT_DIR / f"{task['id']}.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  -> {out.name}")


if __name__ == "__main__":
    main()
