import csv
import shutil
from pathlib import Path

import rasterio

BASE_DIR = Path(r"\\humas\humas\Hasil Georeference\hasil-scan-peta\WSS")
HASIL_DIR = Path(r"C:\Users\bpssg\Downloads\output-perubahan nama file")
TIF_DIR = HASIL_DIR / "tif"
GAGAL_DIR = HASIL_DIR / "gagal"
LAPORAN = HASIL_DIR / "laporan_gagal.csv"

SALIN_KE_GAGAL = True   # False jika hanya ingin laporan CSV

GAGAL_DIR.mkdir(parents=True, exist_ok=True)

jpgs = {f.stem.lower(): f for f in BASE_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg"}}
jgws = {f.stem.lower(): f for f in BASE_DIR.iterdir()
        if f.is_file() and f.suffix.lower() == ".jgw"}
tifs = {f.stem.lower(): f for f in TIF_DIR.glob("*.tif")}

print(f"JPG: {len(jpgs)} | JGW: {len(jgws)} | TIF: {len(tifs)}\n")

gagal = []   # (nama_jpg, alasan)

for stem, jpg in sorted(jpgs.items()):
    tif = tifs.get(stem)

    if tif is None:
        alasan = "JGW tidak ada" if stem not in jgws else "TIF tidak terbentuk (gagal saat konversi)"
        gagal.append((jpg.name, alasan))
        continue

    # TIF ada: cek apakah sehat
    try:
        if tif.stat().st_size == 0:
            raise ValueError("TIF berukuran 0 byte")
        with rasterio.open(tif) as ds:
            if ds.crs is None:
                raise ValueError("TIF tanpa CRS")
            ds.read(1, window=((0, 1), (0, 1)))
    except Exception as e:
        gagal.append((jpg.name, f"TIF bermasalah: {e}"))

# Laporan
with open(LAPORAN, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["nama_file", "alasan"])
    w.writerows(gagal)

# Salin JPG + JGW yang gagal
if SALIN_KE_GAGAL:
    for nama, _ in gagal:
        stem = Path(nama).stem.lower()
        shutil.copy2(jpgs[stem], GAGAL_DIR / jpgs[stem].name)
        if stem in jgws:
            shutil.copy2(jgws[stem], GAGAL_DIR / jgws[stem].name)

for nama, alasan in gagal:
    print(f"[GAGAL] {nama}: {alasan}")

# JGW yatim (ada JGW tapi JPG-nya tidak ada)
yatim = sorted(set(jgws) - set(jpgs))
if yatim:
    print(f"\nJGW tanpa JPG: {len(yatim)} file")

print(f"\nTotal gagal: {len(gagal)} dari {len(jpgs)}")
print(f"Laporan: {LAPORAN}")