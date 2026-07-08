# Thermal Alert / Overheating

## Kategori
Hardware - Cooling System

## Severity
HIGH

## Deskripsi
Thermal alert terjadi ketika sensor suhu pada node atau komponen hardware melaporkan temperatur yang mendekati atau melampaui batas operasional yang aman. Supercomputer BGL memiliki ribuan sensor suhu yang memonitor CPU, DRAM, ASIC jaringan, dan power supply secara real-time.

Overheating adalah salah satu penyebab utama hardware failure pada supercomputer. Suhu tinggi mempercepat degradasi komponen elektronik secara eksponensial (setiap kenaikan 10°C mengurangi umur komponen hingga 50%) dan dapat langsung menyebabkan thermal throttling hingga emergency shutdown.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- THERMAL
- TEMP
- temperature
- overheat
- cooling
- fan failure
- throttle
- TCRIT

Contoh entri log tipikal:
"THERMAL: CPU temperature 85°C exceeds warning threshold (80°C)"
"cooling: fan speed reduced, inlet temperature 35°C"
"ACPI: critical temperature reached, initiating emergency shutdown"
"processor thermal throttling activated at 90°C"

## Kondisi Pemicu
- Kegagalan sistem pendingin (AC failure di data center, fan blade patah)
- Penyumbatan aliran udara (dust buildup, cable management buruk)
- Workload komputasi yang sangat intensif tanpa cukup pendinginan
- Sensor suhu malfungsi (false alarm)
- Kegagalan pada liquid cooling system (untuk node yang menggunakan water cooling)

## Dampak
- Thermal throttling: CPU mengurangi kecepatan clock untuk menurunkan panas — performa turun signifikan
- Emergency shutdown: Jika suhu terus naik, hardware akan mati paksa untuk mencegah kerusakan
- Hardware accelerated aging: Bahkan jika tidak shutdown, suhu tinggi memperpendek umur komponen
- Data center-wide impact: Kegagalan AC dapat mempengaruhi ratusan node sekaligus

## Rekomendasi Tindakan
1. Cek sensor suhu spesifik mana yang memicu alert (CPU, DRAM, inlet, outlet)
2. Verifikasi status fan pada node — cek RPM melalui IPMI/BMC
3. Jika inlet temperature tinggi, kemungkinan masalah data center level — eskalasikan ke fasilitas
4. Kurangi beban komputasi pada node yang bersangkutan jika memungkinkan
5. Jangan restart node saat dalam kondisi overheating — tunggu suhu turun dulu
6. Inspeksi fisik: cek dust filter, pastikan tidak ada kabel yang menghalangi airflow

## Hubungan dengan Anomali Lain
- Suhu tinggi mempercepat terjadinya MEMORY_CE dan MEMORY_UE
- Dapat menyebabkan NETWORK_FAULT jika ASIC jaringan yang overheat
- Emergency thermal shutdown setara dengan KERNEL_PANIC dari perspektif dampak job
- Sering mendahului HARDWARE_FAILURE jika tidak segera ditangani
