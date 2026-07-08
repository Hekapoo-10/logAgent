# Application / Job Failure

## Kategori
Software - Application Layer

## Severity
MEDIUM to HIGH

## Deskripsi
Application failure merujuk pada kegagalan proses komputasi (job) yang berjalan di atas infrastruktur BGL, bukan kegagalan hardware atau OS itu sendiri. Pada supercomputer BGL, aplikasi umumnya berjalan sebagai MPI (Message Passing Interface) job yang melibatkan ratusan hingga ribuan proses paralel di berbagai node.

Kegagalan satu proses MPI dalam suatu job biasanya menyebabkan seluruh job gagal karena MPI tidak dirancang untuk toleran terhadap kegagalan sebagian. CIOD (Console I/O Daemon) adalah daemon kritis yang mengelola lifecycle setiap MPI job.

## Pola di BGL Log
Log key yang sering muncul bersamaan dengan anomali ini:
- CIOD
- ciod
- APP_KILLED
- SIGKILL
- SIGTERM
- job killed
- exit code
- mpirun
- abnormal termination

Contoh entri log tipikal:
"ciod: ERROR: node R01-M0-N04 terminated abnormally, exit code 139"
"FATAL: MPI_Allreduce failed: process killed on rank 47"
"job 12345 killed by signal SIGSEGV on node R02-M1-N08"
"mpirun: job aborted: process died with exit code 1"

## Kondisi Pemicu
- Segmentation fault (SIGSEGV) dalam kode aplikasi — bug dalam program
- Out of memory: aplikasi menggunakan memori lebih dari yang dialokasikan
- MPI timeout: satu rank tidak merespons collective operation dalam batas waktu
- Hardware error pada node yang menyebabkan proses terminated paksa
- Walltime exceeded: job melebihi batas waktu yang dijadwalkan dan di-kill scheduler
- User error: parameter input salah menyebabkan crash

## Dampak
- Job harus diulang dari checkpoint terakhir (jika aplikasi mendukung checkpointing)
- Jika tidak ada checkpoint, semua komputasi sejak awal hilang
- Resource komputasi terbuang — node-node yang terlibat tidak menghasilkan output
- Jika penyebabnya hardware, job yang sama akan terus gagal sampai hardware diperbaiki

## Rekomendasi Tindakan
1. Cek exit code — code 139 biasanya SIGSEGV, code 137 biasanya OOM killer
2. Identifikasi rank/node mana yang pertama kali gagal — biasanya ada di log CIOD
3. Jika satu node berulang kali jadi penyebab failure, curigai hardware node tersebut
4. Cek memory usage job — jika OOM, perlu tuning parameter memori atau kurangi jumlah proses per node
5. Untuk bug aplikasi, koordinasikan dengan job owner untuk analisis core dump
6. Restart job dengan menghindari node yang bermasalah jika scheduler mengizinkan

## Hubungan dengan Anomali Lain
- Sering merupakan dampak sekunder dari MEMORY_UE, IO_NODE_FAILURE, atau NODE_DOWN
- Dapat terjadi independen karena bug aplikasi (tidak selalu indikasi masalah hardware)
- Berulangnya failure pada job yang sama di node berbeda mengindikasikan bug software
- Berulangnya failure di node yang sama dengan job berbeda mengindikasikan hardware fault
