# Software / Firmware Error

## Kategori
Software - System Software

## Severity
MEDIUM to HIGH

## Deskripsi
Software error pada BGL mencakup bug, crash, atau misbehavior pada lapisan software sistem — termasuk firmware node, kernel module, system daemon, atau middleware HPC seperti scheduler (LoadLeveler) dan MPI runtime. Berbeda dengan hardware fault, software error secara teoritis dapat diperbaiki tanpa penggantian komponen fisik.

Firmware error khususnya berbahaya karena firmware berjalan di level paling rendah (di bawah OS) dan bug di level ini dapat menyebabkan hardware tampak seolah rusak padahal sebenarnya hanya butuh firmware update atau rollback.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- firmware
- software error
- driver
- assertion failed
- stack overflow
- segmentation fault
- SIGSEGV
- LoadLeveler
- scheduler error

Contoh entri log tipikal:
"firmware: assertion failed in packet router module, node R01-M0-N04"
"LoadLeveler: scheduler core dump on head node"
"kernel module bglnet: BUG at line 347 in bglnet_interrupt"
"firmware version mismatch between node and I/O processor"

## Kondisi Pemicu
- Firmware update yang tidak kompatibel atau tidak lengkap
- Race condition dalam driver atau kernel module yang jarang terjadi tetapi berdampak fatal
- Scheduler bug yang menyebabkan job double-scheduled atau tidak pernah di-launch
- Memory leak pada daemon jangka panjang yang akhirnya menyebabkan crash
- Versi software yang tidak kompatibel antar komponen sistem

## Dampak
- Umumnya lebih terlokalisir dari hardware failure — hanya komponen software yang bermasalah
- Dapat menyebabkan node malfungsi yang terlihat seperti hardware failure
- Scheduler crash dapat mengganggu seluruh cluster meskipun tidak ada hardware yang rusak
- Recovery biasanya lebih cepat — restart daemon atau rollback firmware

## Rekomendasi Tindakan
1. Identifikasi komponen software yang crash dari stack trace atau assertion message
2. Cek apakah ada firmware atau software update baru yang baru-baru ini di-deploy
3. Coba restart service/daemon yang bermasalah sebelum memutuskan reboot penuh
4. Jika berhubungan dengan firmware, pertimbangkan rollback ke versi sebelumnya
5. Collect core dump dan log lengkap untuk dilaporkan ke tim software atau vendor IBM
6. Cek apakah ada node lain dengan versi firmware/software yang sama yang mengalami masalah serupa

## Hubungan dengan Anomali Lain
- Software error dapat mensimulasikan gejala HARDWARE_FAILURE sehingga diagnosis butuh lebih hati-hati
- Scheduler error dapat menyebabkan banyak APPLICATION_FAILURE secara bersamaan
- Firmware bug pada network driver dapat menyebabkan gejala NETWORK_FAULT
