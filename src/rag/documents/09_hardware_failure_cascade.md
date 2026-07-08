# Hardware Failure Cascade

## Kategori
Hardware - System-wide

## Severity
CRITICAL

## Deskripsi
Hardware failure cascade adalah kondisi di mana kegagalan satu komponen hardware memicu kegagalan berantai pada komponen lain yang terhubung atau bergantung padanya. Ini adalah salah satu skenario paling berbahaya pada supercomputer karena dapat menyebabkan downtime yang luas dan tidak terduga.

Pada BGL, cascade sering dimulai dari kegagalan power supply atau cooling system yang berdampak pada seluruh rack atau midplane. Sistem monitoring BGL memiliki mekanisme deteksi cascade untuk membatasi penyebaran kegagalan.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- HW_FAULT
- CASCADE
- hardware error
- multiple nodes
- rack failure
- power supply
- midplane
- bulk power module

Contoh entri log tipikal:
"FATAL: hardware failure cascade detected on midplane R01-M0"
"power: bulk power module R01-M0-BPM0 voltage out of range"
"RAS: 16 nodes quarantined in rack R01 due to cascading errors"
"system: midplane R02-M1 taken offline — multiple hardware failures"

## Kondisi Pemicu
- Power supply failure yang menyebabkan unstable voltage ke semua node dalam satu midplane
- Cooling failure yang menyebabkan overheating pada banyak node sekaligus
- Backplane failure yang mempengaruhi koneksi semua node dalam satu rack
- Software bug dalam firmware yang di-deploy ke banyak node bersamaan

## Dampak
- Puluhan hingga ratusan node dapat down secara bersamaan
- Semua job yang berjalan di affected nodes terminated tanpa warning
- Kapasitas cluster berkurang drastis — SLA ke pengguna terganggu
- Recovery time lebih lama karena melibatkan hardware repair dan rebooting banyak node
- Potensi data loss yang signifikan

## Rekomendasi Tindakan
1. SEGERA eskalasikan ke on-call engineer dan tim data center operations
2. Isolasi area yang terdampak — hentikan scheduling job baru ke rack/midplane yang bermasalah
3. Prioritaskan identifikasi root cause: apakah power, cooling, atau software?
4. Jangan coba restart semua node sekaligus — lakukan bertahap untuk mencegah power surge
5. Aktifkan incident response protocol dan dokumentasikan timeline kejadian
6. Notifikasi semua pengguna yang job-nya terdampak
7. Setelah hardware diperbaiki, lakukan stress test sebelum kembalikan ke production

## Hubungan dengan Anomali Lain
- Merupakan eskalasi dari beberapa THERMAL_ALERT atau MEMORY_UE yang tidak tertangani
- Menghasilkan banyak NODE_DOWN secara bersamaan
- Dapat menyebabkan IO_NODE_FAILURE jika I/O node ikut terdampak
- Sering disertai banyak APPLICATION_FAILURE bersamaan
