# Memory Uncorrectable Error (UE)

## Kategori
Hardware - Memory Subsystem

## Severity
CRITICAL

## Deskripsi
Memory Uncorrectable Error (UE) terjadi ketika hardware mendeteksi kesalahan pada DRAM yang tidak dapat diperbaiki oleh mekanisme ECC. Ini berarti lebih dari satu bit mengalami flip secara bersamaan, melampaui kemampuan koreksi ECC standar (yang hanya mampu memperbaiki single-bit error). UE adalah kejadian kritis yang hampir selalu mengakibatkan kernel panic, node crash, atau job termination secara paksa.

Pada supercomputer BGL, UE langsung memicu mekanisme failover dan node yang bersangkutan dikeluarkan dari pool komputasi aktif secara otomatis.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- MEMORY_UE
- RAS KERNEL FATAL
- uncorrectable
- machine check
- kernel panic
- SIGKILL

Contoh entri log tipikal:
"RAS KERNEL FATAL double-bit ECC error detected on processor memory"
"machine check exception: uncorrectable DRAM error"
"kernel: EDAC MC0: 2 UE errors on cpu_socket"

## Kondisi Pemicu
- Kegagalan fisik modul DRAM (sering didahului CE yang tidak tertangani)
- Multiple simultaneous bit flips akibat radiasi tinggi
- Kegagalan total satu chip DRAM pada modul
- Power surge atau voltage spike pada memory subsystem

## Dampak
- Immediate: Node crash dan semua job yang berjalan di node tersebut terminated
- Data loss: Semua data in-memory yang belum di-flush ke disk hilang
- Job restart: Semua MPI job yang melibatkan node ini harus diulang dari checkpoint terakhir
- Availability: Node tidak tersedia sampai hardware diganti dan node di-reboot

## Rekomendasi Tindakan
1. SEGERA tandai node sebagai "tidak tersedia" — jangan assign job baru ke node ini
2. Simpan log lengkap node tersebut untuk analisis hardware tim
3. Notifikasi tim hardware untuk penggantian modul DRAM prioritas tinggi
4. Cek apakah node tetangga di rack yang sama menunjukkan gejala CE — kemungkinan masalah rack-level
5. Restore job dari checkpoint terakhir di node cadangan
6. Setelah penggantian hardware, jalankan memory diagnostic test sebelum node dikembalikan ke pool

## Hubungan dengan Anomali Lain
- Sering merupakan eskalasi dari MEMORY_CE yang tidak tertangani
- Hampir selalu diikuti NODE_DOWN dan APPLICATION_FAILURE
- Dapat memicu HARDWARE_CASCADE jika node tetangga ikut terpengaruh
