
from pathlib import Path
import csv
from collections import Counter
from pathlib import Path

# Folder sumber JGW
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "data" / "610501"

# Folder laporan CSV
REPORT_DIR = BASE_DIR / "output" / "610501" / "laporan_cek_crs"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Periksa file di dalam subfolder juga
RECURSIVE = True

# Lokasi file laporan
DETAIL_CSV = REPORT_DIR / "detail_klasifikasi_crs.csv"
RINGKASAN_CSV = REPORT_DIR / "ringkasan_crs.csv"


def baca_jgw(path):
    """Membaca enam nilai dari world file JGW."""
    raw = path.read_bytes()

    if not raw.strip():
        raise ValueError("File kosong (0 byte)")

    teks = None
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            teks = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if teks is None:
        raise ValueError("Encoding tidak dikenali")

    nilai = []
    for token in teks.replace(",", ".").split():
        try:
            nilai.append(float(token))
        except ValueError:
            raise ValueError(f"Bukan angka: {token!r}")

    if len(nilai) != 6:
        raise ValueError(
            f"Harus ada 6 angka, ditemukan {len(nilai)}"
        )

    A, D, B, E, C, F = nilai
    return {"A": A, "D": D, "B": B, "E": E, "C": C, "F": F}
    """Membaca enam nilai dari world file JGW."""
    with open(path, "r", encoding="utf-8-sig") as f:
        nilai = [
            float(baris.strip())
            for baris in f
            if baris.strip()
        ]

    if len(nilai) != 6:
        raise ValueError(
            f"Harus ada 6 angka, ditemukan {len(nilai)}"
        )

    A, D, B, E, C, F = nilai

    return {
        "A": A,
        "D": D,
        "B": B,
        "E": E,
        "C": C,
        "F": F,
    }


def klasifikasi_crs(data):
    """
    Mengelompokkan berdasarkan pola angka saja.
    Hasil merupakan kandidat CRS, bukan kepastian.
    """
    A = data["A"]
    E = data["E"]
    C = data["C"]
    F = data["F"]

    # Pastikan skala piksel tidak nol
    if A == 0 or E == 0:
        return (
            "TIDAK DIKENALI",
            "Ukuran piksel nol; periksa file JGW"
        )

    # Kandidat koordinat geografis dalam derajat.
    # C dan F pada JGW menunjukkan pusat piksel kiri-atas.
    if (
        -180 <= C <= 180
        and -90 <= F <= 90
        and abs(A) <= 1
        and abs(E) <= 1
    ):
        return (
            "GEOGRAFIS (kandidat EPSG:4326)",
            "Koordinat menyerupai bujur-lintang dalam derajat"
        )

    # Kandidat Web Mercator.
    # Rentang koordinat proyeksi sekitar +/- 20 juta meter.
    if (
        abs(C) <= 20_100_000
        and abs(F) <= 20_100_000
        and abs(C) > 1_000_000
    ):
        return (
            "WEB MERCATOR (kandidat EPSG:3857)",
            "Koordinat X besar; perlu validasi metadata"
        )

    # Kandidat koordinat UTM atau proyeksi lokal.
    # Zona dan belahan bumi tidak dapat dipastikan dari JGW saja.
    if (
        100_000 <= abs(C) <= 900_000
        and abs(F) <= 10_000_000
    ):
        return (
            "UTM/PROYEKSI LAIN",
            "Zona, datum, dan belahan bumi belum diketahui"
        )

    return (
        "TIDAK DIKENALI",
        "Perlu diperiksa melalui metadata atau GIS"
    )


def cari_jgw():
    if RECURSIVE:
        return sorted(
            p for p in INPUT_DIR.rglob("*")
            if p.is_file() and p.suffix.lower() == ".jgw"
        )

    return sorted(
        p for p in INPUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".jgw"
    )


def main():
    if not INPUT_DIR.exists():
        print("Folder input tidak ditemukan:")
        print(INPUT_DIR)
        print("\nPeriksa kembali alamat folder di script.")
        return

    daftar = cari_jgw()

    if not daftar:
        print("Tidak ditemukan file .jgw di:")
        print(INPUT_DIR)
        return

    hasil = []
    jumlah = Counter()

    print(f"Jumlah file JGW: {len(daftar)}")
    print("Mulai pemeriksaan...\n")

    for i, path in enumerate(daftar, start=1):
        try:
            data = baca_jgw(path)
            kelompok, keterangan = klasifikasi_crs(data)

            record = {
                "file_jgw": str(path),
                "nama_file": path.name,
                "kelompok": kelompok,
                "keterangan": keterangan,
                **data,
                "status": "OK",
            }

            jumlah[kelompok] += 1

        except Exception as e:
            record = {
                "file_jgw": str(path),
                "nama_file": path.name,
                "kelompok": "ERROR BACA",
                "keterangan": str(e),
                "A": "",
                "D": "",
                "B": "",
                "E": "",
                "C": "",
                "F": "",
                "status": "ERROR",
            }

            jumlah["ERROR BACA"] += 1

        hasil.append(record)

        print(
            f"[{i}/{len(daftar)}] "
            f"{record['nama_file']} -> "
            f"{record['kelompok']}"
        )

    # Laporan detail setiap JGW
    file_detail = REPORT_DIR / "detail_klasifikasi_crs.csv"

    kolom = [
        "file_jgw",
        "nama_file",
        "kelompok",
        "keterangan",
        "A", "D", "B", "E", "C", "F",
        "status",
    ]

    with open(
        file_detail, "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=kolom)
        writer.writeheader()
        writer.writerows(hasil)

    # Laporan ringkasan jumlah tiap kelompok
    file_ringkasan = REPORT_DIR / "ringkasan_crs.csv"

    with open(
        file_ringkasan, "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.writer(f)
        writer.writerow(["Kelompok", "Jumlah file"])

        for kelompok, total in jumlah.most_common():
            writer.writerow([kelompok, total])

    # Tampilkan ringkasan di terminal
    print("\n" + "=" * 55)
    print("RINGKASAN PEMERIKSAAN CRS")
    print("=" * 55)

    for kelompok, total in jumlah.most_common():
        print(f"{kelompok}: {total}")

    print("-" * 55)
    print(f"Total file diperiksa: {len(daftar)}")
    print(f"Laporan detail: {file_detail}")
    print(f"Laporan ringkasan: {file_ringkasan}")
    print("\nPemeriksaan selesai. Belum ada GeoTIFF yang dibuat.")


if __name__ == "__main__":
    main()
