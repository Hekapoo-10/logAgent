# I/O Node Failure

## Kategori
Hardware - I/O Subsystem

## Severity
HIGH

## Deskripsi
Pada arsitektur BGL, I/O node adalah node khusus yang bertanggung jawab menangani semua operasi input/output untuk sekelompok compute node (biasanya rasio 1 I/O node untuk 64 atau 128 compute node). I/O node menghubungkan compute node ke storage system (GPFS/Lustre) dan jaringan eksternal.

Kegagalan I/O node menyebabkan semua compute node yang bergantung padanya kehilangan akses ke filesystem, checkpoint system, dan output data. Ini adalah titik kegagalan tunggal (single point of failure) yang berdampak besar.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- IOLINK
- IO_ERROR
- ciod
- CIOD
- GPFS
- filesystem
- NFS timeout
- I/O timeout

Contoh entri log tipikal:
"ciod: ERROR: failed to read from I/O node"
"IOLINK: connection lost to I/O node rack-R01-M0-N01"
"GPFS: filesystem /bgl/home not responding, timeout after 120s"
"kernel: NFS: I/O error on server io-node-001"

## Kondisi Pemicu
- Kegagalan hardware pada I/O node (disk, NIC, memory)
- Crash pada daemon CIOD (Console I/O Daemon) yang mengelola I/O
- Network congestion berlebihan pada jalur I/O node ke storage
- Deadlock pada GPFS atau Lustre filesystem
- Konfigurasi quota storage yang terlampaui menyebabkan write failure

## Dampak
- Semua compute node yang bergantung pada I/O node yang gagal kehilangan akses filesystem
- Checkpoint job tidak dapat ditulis — risiko kehilangan progress komputasi
- Job output tidak dapat disimpan
- Job baru tidak dapat di-launch karena tidak bisa membaca binary dari filesystem
- Potensi data corruption jika write I/O terpotong di tengah operasi

## Rekomendasi Tindakan
1. Segera identifikasi I/O node mana yang gagal dari pesan log (biasanya ada node ID)
2. Cek status filesystem pada storage head node
3. Restart daemon CIOD pada I/O node jika node masih responsif via management network
4. Jika I/O node tidak responsif, trigger failover ke I/O node backup jika tersedia
5. Notifikasi job owner — semua checkpoint terbaru mungkin hilang
6. Setelah recovery, verifikasi integritas filesystem dengan fsck atau GPFS equivalent

## Hubungan dengan Anomali Lain
- Sering diikuti APPLICATION_FAILURE pada semua job di bawah I/O node yang gagal
- Dapat menyebabkan NODE_DOWN massal jika compute node hang menunggu I/O
- Terkait dengan NETWORK_FAULT jika penyebabnya adalah link antara compute node dan I/O node
