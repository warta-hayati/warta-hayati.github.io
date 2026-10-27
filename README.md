# Warta Hayati

[![Bangun dan terbitkan](https://github.com/warta-hayati/warta-hayati.github.io/actions/workflows/build.yml/badge.svg)](https://github.com/warta-hayati/warta-hayati.github.io/actions/workflows/build.yml)

Agregator berita dan artikel bidang pertanian, perikanan, kehutanan, dan ilmu hayati dari sumber
tepercaya di Asia. Situs statis tanpa basis data, dibangun ulang setiap tiga jam.

- Situs: <https://warta-hayati.github.io>
- Keadaan tiap sumber: <https://warta-hayati.github.io/status/>
- Repositori: <https://github.com/warta-hayati/warta-hayati.github.io>

Sasaran pembaca: petani, pekebun, pembudidaya ikan, ilmuwan, mahasiswa, dan pelajar di Indonesia
yang ingin mengikuti perkembangan bidang ini langsung dari sumber primer — lembaga pemerintah,
lembaga riset, jurnal, dan media. Tidak ada media sosial, algoritma rekomendasi, atau iklan di
dalamnya.

Tata letaknya mengikuti gaya [Techurls](https://techurls.com): satu kotak per sumber, berisi judul
terbaru dalam teks polos.

## Fitur

- **Delapan topik**: Pertanian, Perkebunan, Perikanan Tawar, Perikanan Payau/Laut, Kehutanan,
  Botani, Zoologi, dan Mikrobiologi.
- **Label tingkat sumber** pada setiap kotak: Pemerintah, Lembaga, Riset, Jurnal, Preprint, dan
  Media. Kotak preprint mencantumkan catatan bahwa isinya belum ditelaah sejawat.
- **Filter bahasa (ID/EN) dan pencarian judul**, keduanya berjalan di peramban tanpa server.
- **Penemuan feed otomatis** untuk sumber yang alamat feed-nya belum diketahui.
- **Aksen warna per topik** pada judul seksi, kepala kotak, tab, dan pita tepi atas halaman.
- **Tampilan ponsel**: tab topik dibungkus ke beberapa baris, target sentuh minimal 44px, dan
  tabel status berubah menjadi kartu.
- **Riwayat judul per sumber**, sehingga kotak tetap terisi ketika feed sedang kosong atau gagal.
- **Halaman status** berisi sumber yang gagal, alasan galatnya, dan kandidat yang belum aktif.
- **Halaman tentang** berbahasa awam berisi cara pakai dan jalur kontak.
- **Ekspor `data.json`** untuk dipakai ulang peneliti dan pengembang lain.

Kotak yang tidak punya judul disembunyikan dari beranda dan halaman topik.

## Cara kerja

```mermaid
flowchart LR
    CFG[config/sources.yaml] --> FET[Pengambil feed dan halaman]
    CRON[GitHub Actions tiap 3 jam] --> FET
    FET --> NRM[Normalisasi dan deduplikasi]
    NRM --> ST[(data/state.json)]
    ST --> GEN[Generator HTML Jinja2]
    GEN --> DST[dist/ situs statis]
    DST --> PG[GitHub Pages]
```

1. [`config/sources.yaml`](config/sources.yaml) mendaftar sumber, topik, bahasa, tingkat, dan
   penyaring kata kunci.
2. Pengambil memuat semua feed secara paralel. Sumber dengan `feed: auto` dicari lewat tag
   `<link rel="alternate">` dan jalur umum seperti `/feed/` dan `/rss.xml`. Sumber tanpa RSS
   memakai aturan `list` untuk membaca daftar berita dari halaman biasa.
3. Normalisasi membersihkan HTML dari judul, membuang parameter pelacak (`utm_*`, `fbclid`),
   menolak tautan selain http(s), lalu membuang duplikat berdasarkan URL dan judul.
4. Generator menulis `index.html`, satu halaman per topik, `status/`, `tentang/`, dan `data.json`.
5. Hanya judul, tanggal, dan tautan keluar yang disimpan. Isi artikel tidak disalin.

## Struktur repositori

```text
warta-hayati/
├── config/sources.yaml        daftar sumber, topik, dan tingkat
├── src/wartahayati/
│   ├── config.py              muat dan validasi konfigurasi
│   ├── fetcher.py             ambil feed, temukan feed, simpan riwayat
│   ├── listpage.py            baca daftar berita dari halaman tanpa RSS
│   ├── normalize.py           pembersihan, penyaring, penggabungan
│   ├── render.py              pembangun situs statis
│   └── cli.py                 perintah build, fetch, render, check
├── templates/                 templat Jinja2 (beranda, topik, status, tentang)
├── static/                    style.css, app.js, logo, dan ikon situs
├── tests/                     pengujian pytest
├── .github/workflows/build.yml
└── data/                      state.json dibuat saat dijalankan (tidak masuk Git)
```

## Memulai

Prasyarat: Python 3.11 atau lebih baru.

```bash
git clone https://github.com/warta-hayati/warta-hayati.github.io.git warta-hayati
cd warta-hayati
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

wartahayati build               # ambil feed, lalu bangun situs ke dist/
python -m http.server -d dist 8000
```

Buka <http://localhost:8000>. Untuk memeriksa tampilan ponsel, biarkan peladen berjalan lalu buka
`http://<IP-lokal-komputer>:8000` dari ponsel di jaringan Wi-Fi yang sama; alamat IP komputer
terlihat dengan `hostname -I`.

| Perintah | Fungsi |
|---|---|
| `wartahayati build` | Ambil semua feed, lalu bangun situs. |
| `wartahayati fetch` | Ambil feed dan perbarui `data/state.json` tanpa membangun situs. |
| `wartahayati render` | Bangun situs dari `data/state.json` yang sudah ada. Cocok untuk mengubah templat. |
| `wartahayati check` | Ambil feed, cetak laporan kesehatan per sumber, dan keluar dengan kode 1 bila ada yang gagal. |

Opsi umum: `--config`, `--data`, `--out`, dan `-v` untuk log rinci.

## Mengelola sumber

Setiap sumber berupa satu entri di [`config/sources.yaml`](config/sources.yaml):

```yaml
- id: kementan
  name: "Kementerian Pertanian RI"
  url: "https://www.pertanian.go.id/"
  tier: pemerintah                 # pemerintah, lembaga, riset, jurnal, preprint, media
  lang: id                         # id atau en
  topics: [pertanian, perkebunan]
  list: {item: "a:has(h4)", title: "h4", date: "time"}
  note: "Tanpa RSS. Berita dan pengumuman dibaca dari halaman depan memakai aturan 'list'."
```

Kunci yang dikenali: `feed` (URL eksplisit, bawaan `auto`), `include` (penyaring kata kunci),
`max_items` (bawaan 6), serta `enabled: false` beserta `note` untuk kandidat yang belum aktif.

Sumber tanpa RSS memakai aturan `list`. Aturan ini tidak boleh dipakai bersama `feed`.

```yaml
- id: fao-asia-pasifik
  name: "FAO Asia dan Pasifik"
  url: "https://www.fao.org/asiapacific/news/"   # halaman daftar berita
  tier: lembaga
  lang: en
  topics: [pertanian, perikanan-tawar, perikanan-laut, kehutanan]
  list:
    item: "div.d-list-news"          # wadah tiap berita
    title: "h5.title-link a"         # elemen judul
    date: "h6.date"                  # opsional: elemen tanggal
    summary: "div.d-list-content p"  # opsional: elemen ringkasan
    # link: "a"                      # opsional: bawaan tautan pertama di dalam item
    # date_in_title: false           # opsional: tanggal dibaca dari judul lalu dibuang
```

Pemilihnya sederhana: tag, `.kelas`, `#id`, `:has(...)`, hubungan keturunan dengan spasi, dan
gabungan dengan koma. Tanggal dikenali dalam bentuk `21-09-2026`, `23/10/2026`, `2026-10-27`,
`25 Oktober 2026`, dan `27 Okt 2026`, baik nama hari dan bulan Indonesia maupun Inggris. Pembaca
halaman daftar hanya memakai pustaka standar `html.parser`.

Aturan divalidasi saat config dimuat: kunci tak dikenal, nilai kosong, atau `list` bersama `feed`
ditolak dengan pesan yang menyebut id sumbernya.

Topik pertama pada `topics` menentukan tempat sumber tampil di beranda; halaman topik menampilkan
semua sumber yang memuat topik tersebut. Sumber yang melayani beberapa topik dengan penyaring
berbeda didaftarkan sebagai beberapa entri dengan `url` sama — pengambil hanya mengunduh satu kali
per alamat.

Setelah mengubah daftar, jalankan `wartahayati check` dan baca keluarannya. `pytest` ikut
memvalidasi struktur berkas, memastikan setiap topik punya sumber utama, dan memastikan setiap
sumber nonaktif membawa `note`.

### Kriteria masuk sumber

1. Identitas penerbit dapat diverifikasi.
2. Ada kebijakan redaksi atau telaah sejawat yang dapat dibaca publik.
3. Jurnal terdaftar di DOAJ atau diterbitkan penerbit ilmiah mapan. Penerbit dengan rekam jejak
   jurnal predator tidak diterima.
4. Sumber menyediakan feed atau halaman daftar yang dapat dibaca mesin.
5. Cakupannya relevan dengan Asia, atau sumber global dilengkapi penyaring `include`.
6. Sumber tidak menjadikan unggahan media sosial sebagai dasar pemberitaan.
7. Preprint wajib berlabel `preprint`.

Sumber yang belum memenuhi kriteria diberi `enabled: false` beserta `note`. Sumber yang feed-nya
gagal dimuat tidak dinonaktifkan: kegagalannya tampil di halaman status, judul lama tetap terisi
sampai feed-nya pulih, dan sumber itu kembali menyumbang judul begitu penerbit memperbaikinya.

Keadaan tiap sumber selalu terbaru di [halaman status](https://warta-hayati.github.io/status/),
tidak di berkas ini.

## Pengujian

```bash
pytest -q
```

Pengujian mencakup pembersihan teks, penyaringan tautan tidak aman, deduplikasi, validasi
konfigurasi, pembacaan halaman daftar berita dari fixture HTML, dan pembangunan semua halaman
dengan data kosong. Sebagian pengujian menjaga hal yang mudah rusak tanpa terlihat: aturan warna
dan atribut `data-topik` setiap topik, titik henti ponsel serta target sentuh 44px, `data-label`
pada sel tabel status, keikutsertaan logo dan halaman `tentang/`, dan tidak bocornya jalur kontak
ke halaman selain `tentang/`.

## Menerbitkan ke GitHub Pages

1. Dorong kode ke cabang `main`.
2. Di **Settings > Pages**, pilih **Build and deployment > Source: GitHub Actions**.
3. Jalankan workflow **Bangun dan terbitkan** sekali secara manual dari tab Actions.
4. Situs terbit di <https://warta-hayati.github.io/>. Semua tautan internal memakai alamat relatif,
   jadi situs juga berjalan di domain sendiri atau di subfolder.

Workflow berjalan setiap tiga jam dan menyimpan riwayat judul lewat `actions/cache`. Bila cache
terhapus, kotak terisi ulang dari feed terbaru pada putaran berikutnya. GitHub menonaktifkan
workflow terjadwal pada repositori publik setelah 60 hari tanpa aktivitas; satu commit kecil atau
tombol **Enable workflow** di tab Actions mengaktifkannya kembali.

## Hak cipta dan etika pengambilan data

- Situs hanya menampilkan judul, tanggal, dan tautan keluar. Hak atas isi tetap pada penerbit asli.
- Pengambil memakai user agent `WartaHayatiBot` yang mencantumkan alamat repositori, mengambil
  setiap alamat sekali per putaran, dan memakai feed yang memang diterbitkan untuk sindikasi.
- Penerbit yang ingin dikeluarkan dari daftar dapat membuka issue; entri dihapus pada putaran
  berikutnya.
- Kode dilisensikan MIT (lihat [LICENSE](LICENSE)). Lisensi berlaku untuk kode saja; judul dan
  tautan tetap milik sumber.

## Peta jalan

- Halaman **Referensi** berisi tautan pencarian ilmiah dan alur kerja penelusuran: Google Scholar
  dengan operator `site:`, DOAJ untuk memeriksa status akses terbuka, AGRIS, dan CORE.
- Pengambil OAI-PMH untuk repositori DSpace dan jurnal OJS Indonesia (Garuda, portal perguruan
  tinggi).
- Pemantauan otomatis perubahan struktur halaman untuk sumber `list`: peringatan di halaman status
  bila jumlah butir turun mendadak.
- Peramban tanpa antarmuka opsional untuk situs berita ber-JavaScript, hanya bila dependensi
  tambahan disetujui.
- Terjemahan judul otomatis dari Inggris ke Indonesia.
- Penyaring Asia otomatis untuk sumber global.
- Mode gelap dan self-hosting huruf untuk melepas ketergantungan pada Google Fonts.
- Pemilih topik satu baris untuk ponsel, bila daftar tab yang dibungkus dirasa terlalu tinggi.

## Kontribusi

Usulan sumber baru diajukan lewat issue atau pull request yang mengubah
[`config/sources.yaml`](config/sources.yaml). Sertakan alamat feed bila ada, tingkat sumber, dan
bukti bahwa kriteria masuk terpenuhi.

Bagi yang tidak memakai GitHub, usulan dan koreksi bisa dikirim lewat surel ke
<ekajogja@gmail.com>, atau lewat [halaman tentang](https://warta-hayati.github.io/tentang/) di
situs. Pengelola: Eka Y Saputra.
