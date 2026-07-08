# RAS General Alert (Reliability, Availability, Serviceability)

## Kategori
System - RAS Framework

## Severity
LOW to HIGH (tergantung sub-tipe)

## Deskripsi
RAS (Reliability, Availability, Serviceability) adalah framework monitoring bawaan IBM BGL yang mengumpulkan dan mengklasifikasikan semua event hardware dan software secara real-time. Semua anomali hardware pada BGL pada umumnya dilaporkan melalui framework RAS ini sebelum dikategorikan lebih spesifik.

RAS alert yang berdiri sendiri (tanpa diikuti error yang lebih spesifik) biasanya merupakan warning level — hardware mendeteksi kondisi yang tidak normal tetapi masih dalam batas toleransi operasional. Meskipun demikian, RAS alert yang muncul berulang kali pada node yang sama dalam waktu singkat adalah indikator kuat adanya masalah yang akan berkembang.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- RAS
- ALERT
- WARNING
- RAS KERNEL INFO
- RAS KERNEL WARNING
- threshold

Contoh entri log tipikal:
"RAS KERNEL INFO: processor recoverable error on node R01-M0-N04"
"RAS KERNEL WARNING: DDR memory threshold exceeded"
"RAS: error rate threshold exceeded on node, monitoring increased"
"RAS FATAL: unrecoverable error — node will be fenced"

## Level Klasifikasi RAS
- **RAS INFO**: Informatif, tidak perlu tindakan segera. Log untuk tracking.
- **RAS WARNING**: Perlu perhatian. Pantau frekuensi dan eskalasi jika meningkat.
- **RAS FATAL**: Perlu tindakan segera. Node kemungkinan akan difence otomatis.

## Kondisi Pemicu
- Accumulated error count melampaui threshold yang dikonfigurasi
- Hardware event yang tidak masuk kategori error spesifik lainnya
- Periodic health check yang mendeteksi kondisi sub-optimal
- Transient error yang berhasil dipulihkan tetapi tetap dilaporkan untuk tracking

## Dampak
- RAS INFO/WARNING: Biasanya tidak ada dampak langsung pada job
- RAS FATAL: Node akan difence dan semua job dihentikan
- Banyak RAS WARNING dalam waktu singkat: indikasi hardware akan segera gagal

## Rekomendasi Tindakan
1. Catat node ID dan frekuensi RAS event — buat baseline normal untuk perbandingan
2. Jika RAS WARNING muncul lebih dari 5 kali dalam 10 menit pada node yang sama, tingkatkan monitoring
3. Untuk RAS FATAL, ikuti prosedur yang sama dengan KERNEL_PANIC atau MEMORY_UE
4. Review trend RAS event secara mingguan untuk deteksi dini hardware degradation
5. Korelasikan RAS event dengan beban komputasi — beban tinggi kadang memicu lebih banyak transient error

## Hubungan dengan Anomali Lain
- RAS adalah "umbrella" framework yang mencakup semua anomali hardware lainnya
- RAS INFO sering mendahului MEMORY_CE
- RAS WARNING yang meningkat frekuensinya sering mendahului MEMORY_UE atau KERNEL_PANIC
- RAS FATAL biasanya bersamaan dengan NODE_DOWN
