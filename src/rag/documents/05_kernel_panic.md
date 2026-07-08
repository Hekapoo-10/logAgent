# Kernel Panic / System Crash

## Kategori
Software - Operating System

## Severity
CRITICAL

## Deskripsi
Kernel panic adalah kondisi di mana kernel sistem operasi Linux pada node BGL mendeteksi kondisi fatal yang tidak dapat dipulihkan dan menghentikan eksekusi secara paksa untuk mencegah kerusakan data lebih lanjut. Ini adalah mekanisme keamanan OS — ketika kernel tidak tahu cara melanjutkan dengan aman, ia memilih untuk berhenti sepenuhnya.

Pada BGL, kernel panic biasanya dipicu oleh hardware error yang tidak dapat ditangani (seperti UE), driver bug, atau stack overflow pada proses kernel. Setelah panic, node memerlukan reboot penuh.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- kernel panic
- PANIC
- Oops
- BUG
- segfault
- kernel: fatal
- call trace
- RIP

Contoh entri log tipikal:
"Kernel panic - not syncing: Fatal exception in interrupt"
"BUG: unable to handle kernel NULL pointer dereference"
"kernel: Oops: general protection fault"
"EXT4-fs error: Journal has aborted"

## Kondisi Pemicu
- Memory Uncorrectable Error yang mempengaruhi kernel address space
- Driver bug dalam modul kernel (network driver, filesystem driver)
- Hardware interrupt storm yang menghabiskan semua kapasitas CPU
- Watchdog timeout — proses kernel tidak merespons dalam batas waktu
- Corrupted kernel data structure akibat hardware fault

## Dampak
- Node langsung berhenti semua operasi — tidak ada graceful shutdown
- Semua job yang berjalan di node tersebut terminated tanpa checkpoint
- Node tidak tersedia sampai reboot selesai (bisa 5-15 menit pada BGL)
- Potensi filesystem corruption jika journal tidak sempat di-flush sebelum panic

## Rekomendasi Tindakan
1. Catat kernel panic message lengkap — biasanya mengandung informasi penyebab
2. Analisis call trace untuk mengidentifikasi modul kernel atau driver yang bermasalah
3. Trigger automatic reboot melalui management network (tidak perlu intervensi fisik)
4. Setelah reboot, jalankan filesystem check sebelum node dikembalikan ke pool
5. Jika panic berulang di node yang sama setelah reboot, tandai node untuk inspeksi hardware
6. Kirim core dump ke tim software untuk analisis lebih lanjut

## Hubungan dengan Anomali Lain
- Sering merupakan dampak akhir dari MEMORY_UE
- Dapat menyebabkan IO_NODE_FAILURE jika terjadi pada I/O node
- Selalu diikuti NODE_DOWN dan APPLICATION_FAILURE
- Dapat memicu HARDWARE_CASCADE jika penyebabnya adalah hardware yang mempengaruhi banyak node
