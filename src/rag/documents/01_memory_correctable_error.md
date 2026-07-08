# Memory Correctable Error (CE)

## Kategori
Hardware - Memory Subsystem

## Severity
MEDIUM

## Deskripsi
Memory Correctable Error (CE) terjadi ketika hardware mendeteksi bit flip pada modul DRAM dan berhasil memperbaikinya secara otomatis menggunakan mekanisme ECC (Error Correcting Code). Pada supercomputer BGL, setiap node komputasi dilengkapi dengan DRAM ber-ECC sehingga error tunggal dapat diperbaiki tanpa interupsi aplikasi.

Meskipun satu kejadian CE tidak mengakibatkan kegagalan sistem, frekuensi CE yang meningkat pada node yang sama adalah indikasi kuat bahwa modul DRAM mengalami degradasi fisik. Pola ini sering mendahului terjadinya Uncorrectable Error (UE) yang bersifat fatal.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- MEMORY_CE
- RAS KERNEL INFO
- ECC
- DRAM
- correctable

Contoh entri log tipikal:
"RAS KERNEL INFO instruction cache parity error corrected"
"correctable error threshold exceeded on processor"

## Kondisi Pemicu
- Degradasi fisik modul DRAM akibat usia atau stress termal
- Radiasi kosmik (single-event upset) yang membalik satu bit
- Ketidakstabilan voltase pada slot memori
- Suhu operasional node yang melebihi batas normal

## Dampak
- Jangka pendek: Tidak ada gangguan pada aplikasi yang berjalan
- Jangka menengah: Penurunan performa karena overhead koreksi ECC
- Jangka panjang: Risiko tinggi eskalasi ke Uncorrectable Error jika tidak ditangani

## Rekomendasi Tindakan
1. Catat node ID dan slot memori yang melaporkan CE
2. Monitor frekuensi CE — jika lebih dari 10 kejadian dalam 1 jam pada node yang sama, eskalasikan ke tim hardware
3. Jadwalkan penggantian modul DIMM pada window maintenance berikutnya
4. Periksa suhu node yang bersangkutan — thermal stress mempercepat degradasi DRAM
5. Jangan restart node secara paksa — CE masih dapat ditoleransi sampai maintenance terjadwal

## Hubungan dengan Anomali Lain
- Dapat berkembang menjadi MEMORY_UE jika tidak ditangani
- Sering muncul bersamaan dengan THERMAL_ALERT pada lingkungan bersuhu tinggi
- Bisa mengindikasikan masalah pada power delivery yang mempengaruhi seluruh rack
