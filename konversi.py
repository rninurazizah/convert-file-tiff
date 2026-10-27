import csv
import re
from pathlib import Path

import rasterio
from rasterio.transform import Affine

# ===== PENGATURAN =====
BASE_DIR = Path(r"C:\Users\bpssg\Downloads\output-perubahan nama file\gagal")
INPUT_DIR = BASE_DIR
OUTPUT_DIR = Path(r"C:\Users\bpssg\Downloads\output-perubahan nama file") / "tif"
CSV_CRS = Path(r"C:\Users\bpssg\Downloads\output-perubahan nama file\detail_klasifikasi_crs.csv")

if not INPUT_DIR.exists():
    raise FileNotFoundError(f"Folder input tidak ditemukan: {INPUT_DIR}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def baca_jgw(jgw_file):
    with open(jgw_file, "r", encoding="utf-8-sig") as f:
        v = [float(l.strip()) for l in f if l.strip()]
    if len(v) != 6:
        raise ValueError("File JGW harus berisi 6 angka.")
    A, D, B, E, C, F = v
    # JGW = pusat piksel kiri atas -> geser ke sudut kiri atas
    return Affine(A, B, C - (A + B) / 2, D, E, F - (D + E) / 2)


def deteksi_crs(transform, lebar, tinggi):
    x, y = transform * (lebar / 2, tinggi / 2)
    if abs(x) <= 180 and abs(y) <= 90:
        return "EPSG:4326"
    if abs(x) > 1e7:
        return "EPSG:3857"
    return None  # kemungkinan UTM -> harus dari CSV


def baca_csv(path):
    """Membaca CSV; pemisah (tab / ; / ,) dideteksi otomatis."""
    data = {}
    if not path.exists():
        print(f"PERINGATAN: CSV tidak ditemukan: {path}")
        return data

    with open(path, newline="", encoding="utf-8-sig") as f:
        baris_pertama = f.readline()
        f.seek(0)
        pemisah = max(["\t", ";", ","], key=baris_pertama.count)
        reader = csv.DictReader(f, delimiter=pemisah)
        reader.fieldnames = [h.strip().lower() for h in reader.fieldnames]
        print(f"Kolom CSV    : {reader.fieldnames} (pemisah: {repr(pemisah)})")

        for r in reader:
            nama = (r.get("nama_file") or r.get("file_jgw") or "").strip()
            if not nama:
                continue
            nama = nama.replace("\\", "/").split("/")[-1]
            if (r.get("status") or "").strip().upper() != "OK":
                continue
            kandidat = set(re.findall(r"EPSG:(\d+)", r.get("kelompok") or ""))
            data[Path(nama).stem.lower()] = (
                f"EPSG:{kandidat.pop()}" if len(kandidat) == 1 else None
            )
    return data


info_csv = baca_csv(CSV_CRS)
images = sorted(f for f in INPUT_DIR.iterdir()
                if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg"})
jgw_map = {f.stem.lower(): f for f in INPUT_DIR.iterdir()
           if f.is_file() and f.suffix.lower() == ".jgw"}

print(f"Ditemukan    : {len(images)} JPG, {len(jgw_map)} JGW, {len(info_csv)} baris CSV OK\n")
berhasil = gagal = 0

for jpg in images:
    try:
        jgw = jgw_map.get(jpg.stem.lower())
        if jgw is None:
            raise FileNotFoundError("File JGW tidak ditemukan.")
        transform = baca_jgw(jgw)

        with rasterio.open(jpg) as src:
            crs_deteksi = deteksi_crs(transform, src.width, src.height)
            crs_csv = info_csv.get(jpg.stem.lower())

            if crs_csv and crs_deteksi and crs_csv != crs_deteksi:
                raise ValueError(f"CRS CSV ({crs_csv}) beda dengan koordinat JGW ({crs_deteksi})")
            crs = crs_csv or crs_deteksi
            if crs is None:
                raise ValueError("CRS tidak bisa ditentukan (kemungkinan UTM), cek CSV")

            tif = OUTPUT_DIR / f"{jpg.stem}.tif"

            profile = src.profile.copy()
            profile.update(driver="GTiff", transform=transform, crs=crs, compress="lzw")
            for k in ("photometric", "quality"):
                profile.pop(k, None)
            with rasterio.open(tif, "w", **profile) as dst:
                dst.write(src.read())

        print(f"[BERHASIL] {jpg.name} -> {tif.name} ({crs})")
        berhasil += 1
    except Exception as e:
        print(f"[GAGAL] {jpg.name}: {e}")
        gagal += 1

print(f"\nSelesai. Berhasil: {berhasil}, Gagal: {gagal}")
print(f"Folder output: {OUTPUT_DIR}")