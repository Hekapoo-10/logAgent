# Power Supply Fault

## Kategori
Hardware - Power Subsystem

## Severity
HIGH to CRITICAL

## Deskripsi
Power supply fault terjadi ketika unit catu daya (PSU) pada node atau rack mengalami masalah sehingga tidak dapat menyediakan daya yang stabil dan sesuai spesifikasi. Pada BGL, setiap midplane memiliki Bulk Power Module (BPM) yang mendistribusikan daya ke semua node di dalamnya.

Ketidakstabilan daya adalah penyebab yang sangat merusak karena dapat mempengaruhi semua komponen sekaligus — CPU, DRAM, storage, dan network interface semuanya sensitif terhadap fluktuasi voltase. Berbeda dengan hardware fault lain yang umumnya terlokalisir, power fault dapat mempengaruhi seluruh rack atau midplane.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- power supply
- voltage
- BPM
- bulk power
- UPS
- power fault
- POWER_ERROR
- undervoltage
- overvoltage

Contoh entri log tipikal:
"power: BPM R01-M0-BPM0 output voltage out of range: 11.2V (expected 12V)"
"FATAL: power supply fault on midplane R02-M1, 16 nodes affected"
"UPS: utility power failure, running on battery"
"power: redundant PSU failure on node R01-M0-N04 — now single PSU"

## Kondisi Pemicu
- Kegagalan fisik kapasitor atau komponen internal PSU akibat usia
- Masalah pada utilitas daya data center (PLN atau utility power fluctuation)
- UPS (Uninterruptible Power Supply) bermasalah atau kapasitas baterai habis
- Overloading: beban komputasi yang menyebabkan konsumsi daya melebihi kapasitas PSU
- Kegagalan redundant PSU yang menyebabkan sistem berjalan dengan single PSU (reduced redundancy)

## Dampak
- Undervoltage: komponen beroperasi tidak stabil, meningkatkan error rate secara dramatis
- Overvoltage: dapat langsung merusak komponen elektronik secara permanen
- Power loss: semua node yang terdampak mati tanpa graceful shutdown — risiko data corruption tinggi
- Reduced redundancy: kegagalan PSU pertama (saat masih ada backup) butuh segera ditangani sebelum PSU kedua juga gagal

## Rekomendasi Tindakan
1. SEGERA notifikasi tim facilities/data center — ini bukan hanya masalah IT
2. Identifikasi apakah masalah dari utility power atau internal PSU dengan memeriksa UPS status
3. Jika voltage out-of-range terdeteksi pada BPM, isolasi midplane yang bersangkutan
4. Aktifkan generator backup jika tersedia dan utilitas power sedang bermasalah
5. Jangan jalankan job baru di area yang terdampak sampai power stabil
6. Setelah penggantian PSU, verifikasi voltase stabil minimal 30 menit sebelum kembalikan ke produksi

## Hubungan dengan Anomali Lain
- Sering menjadi root cause tersembunyi dari MEMORY_CE, MEMORY_UE, dan THERMAL_ALERT
- Power fault yang tidak segera ditangani hampir pasti memicu HARDWARE_CASCADE
- Voltage fluctuation dapat menyebabkan banyak KERNEL_PANIC bersamaan
- Kegagalan total power supply menyebabkan NODE_DOWN massal
