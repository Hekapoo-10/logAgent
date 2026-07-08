# Node Down / Node Unavailable

## Kategori
Infrastructure - Node Availability

## Severity
HIGH

## Deskripsi
Node down adalah kondisi di mana satu atau lebih compute node pada BGL tidak dapat digunakan untuk komputasi. Ini bisa terjadi karena berbagai sebab: hardware failure, kernel panic, planned maintenance, atau node secara otomatis di-quarantine oleh sistem monitoring setelah mendeteksi terlalu banyak error.

Pada BGL, node management dilakukan melalui Control System yang memantau status setiap node secara real-time. Ketika node mengalami masalah, Control System dapat secara otomatis mengeluarkan node dari pool aktif (fence/quarantine) untuk mencegah job baru dijadwalkan di node tersebut.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- NODE_DOWN
- node down
- BOOT
- boot failure
- free pages
- node unavailable
- hardware error
- RAS

Contoh entri log tipikal:
"RAS: node R01-M0-N04 removed from partition due to hardware error"
"boot: node R02-M1-N08 failed to boot after 3 attempts"
"FATAL: node R03-M2-N12 unreachable via management network"
"system: node quarantined after exceeding error threshold"

## Kondisi Pemicu
- Hasil eskalasi dari MEMORY_UE, KERNEL_PANIC, atau THERMAL_ALERT
- Boot failure: node tidak berhasil booting setelah restart (bisa karena disk, firmware, atau hardware)
- Management network timeout: node tidak merespons heartbeat dari Control System
- Manual quarantine oleh operator untuk maintenance atau inspeksi
- Firmware update yang gagal menyebabkan node brick

## Dampak
- Node tidak tersedia untuk scheduling job baru
- Efektif kapasitas komputasi cluster berkurang
- Jika banyak node down bersamaan, antrian job meningkat drastis
- Job yang sedang berjalan di node tersebut terminated

## Rekomendasi Tindakan
1. Identifikasi penyebab node down dari log sebelumnya (biasanya ada chain of events)
2. Coba remote reboot via management network (IPMI/BMC)
3. Jika reboot berhasil, jalankan diagnostic test sebelum kembalikan ke pool
4. Jika reboot gagal, flag untuk inspeksi fisik oleh tim hardware
5. Periksa apakah ada pola — banyak node down di rack yang sama mengindikasikan masalah power atau cooling rack-level
6. Update inventory dengan status node dan estimasi waktu recovery

## Hubungan dengan Anomali Lain
- Sering merupakan outcome dari KERNEL_PANIC, MEMORY_UE, atau THERMAL_ALERT
- NODE_DOWN massal dapat mengindikasikan HARDWARE_CASCADE
- Boot failure berulang mengindikasikan persistent hardware fault yang butuh penggantian komponen
