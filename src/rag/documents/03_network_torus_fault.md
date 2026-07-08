# Network / Torus Link Fault

## Kategori
Hardware - Interconnect Network

## Severity
HIGH

## Deskripsi
Supercomputer BGL menggunakan topologi jaringan 3D Torus untuk komunikasi antar-node. Setiap node terhubung ke 6 tetangga (atas, bawah, kiri, kanan, depan, belakang) melalui link dedicated berkecepatan tinggi. Network fault terjadi ketika satu atau lebih link Torus mengalami gangguan, baik karena kerusakan fisik kabel, kegagalan port pada ASIC jaringan, atau packet loss berlebihan.

Karena aplikasi HPC (High Performance Computing) di BGL sangat bergantung pada komunikasi MPI antar-node, bahkan satu link Torus yang bermasalah dapat menyebabkan penurunan performa signifikan atau deadlock pada komunikasi kolektif.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- NETWORK
- TORUS
- link down
- packet loss
- MPI timeout
- collective timeout
- FATAL torus

Contoh entri log tipikal:
"FATAL torus receiver overrun on link X+"
"network: link X- dropped, rerouting traffic"
"MPI collective operation timeout after 300 seconds"
"torus: excessive CRC errors on dimension Y"

## Kondisi Pemicu
- Kegagalan fisik kabel fiber optik atau copper pada interconnect
- Kerusakan port pada ASIC (Application-Specific Integrated Circuit) jaringan
- Electromagnetic interference (EMI) yang menyebabkan CRC error berulang
- Overheating pada network ASIC
- Firmware bug pada network controller yang menyebabkan link flapping

## Dampak
- Performa: Bandwidth MPI turun drastis, latency meningkat
- Stabilitas: Timeout pada operasi collective (MPI_Allreduce, MPI_Barrier) menyebabkan hang
- Availability: Jika link utama dan backup sama-sama gagal, node menjadi terisolir dari jaringan
- Job impact: MPI job yang melibatkan node dengan link bermasalah bisa hang atau crash

## Rekomendasi Tindakan
1. Identifikasi link spesifik yang bermasalah dari log (dimensi X/Y/Z, arah +/-)
2. Cek apakah BGL firmware melakukan rerouting otomatis — jika ya, monitor performa
3. Jika packet loss > 1%, eskalasikan ke tim jaringan untuk inspeksi fisik kabel
4. Jika terjadi link down total, pertimbangkan untuk memindahkan job ke partisi lain
5. Cek log node tetangga — network fault sering terdeteksi dari dua sisi link

## Hubungan dengan Anomali Lain
- Link fault yang persisten dapat menyebabkan NODE_DOWN pada node yang terisolir
- Sering bersamaan dengan THERMAL_ALERT jika penyebabnya adalah overheating ASIC
- Dapat memicu APPLICATION_FAILURE pada MPI job yang membutuhkan komunikasi intensif
