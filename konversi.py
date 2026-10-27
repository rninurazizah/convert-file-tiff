from pathlib import Path
import rasterio
from rasterio.transform import Affine

# ==================================
# PENGATURAN FOLDER
# ==================================
BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "data" / "610501"
OUTPUT_DIR = BASE_DIR / "output"

# Ganti sesuai koordinat di file JGW:
#   - EPSG:4326  -> koordinat derajat (lon/lat)
#   - EPSG:32649 / EPSG:32650 -> UTM (nilai koordinat ratusan ribu / jutaan)
CRS = "EPSG:4326"

# ==================================
# CEK FOLDER
# ==================================
if not INPUT_DIR.exists():
    raise FileNotFoundError(f"Folder input tidak ditemukan: {INPUT_DIR}")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ==================================
# MEMBACA FILE JGW
# ==================================
def baca_jgw(jgw_file):
    with open(jgw_file, "r", encoding="utf-8-sig") as f:
        values = [float(line.strip()) for line in f if line.strip()]

    if len(values) != 6:
        raise ValueError("File JGW harus berisi 6 angka.")

    A, D, B, E, C, F = values

    # Koordinat JGW adalah pusat piksel kiri atas.
    # Konversi ke sudut kiri atas untuk GeoTIFF.
    return Affine(
        A, B, C - (A + B) / 2,
        D, E, F - (D + E) / 2
    )


# ==================================
# DAFTAR FILE
# ==================================
images = sorted(
    f for f in INPUT_DIR.iterdir()
    if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg"}
)

# Peta nama file JGW (tanpa membedakan kapital)
jgw_map = {
    f.stem.lower(): f
    for f in INPUT_DIR.iterdir()
    if f.is_file() and f.suffix.lower() == ".jgw"
}

print(f"Folder input : {INPUT_DIR}")
print(f"Ditemukan    : {len(images)} file JPG, {len(jgw_map)} file JGW\n")

# ==================================
# KONVERSI SEMUA JPG
# ==================================
berhasil = 0
gagal = 0

for jpg in images:
    try:
        jgw = jgw_map.get(jpg.stem.lower())
        if jgw is None:
            raise FileNotFoundError(f"File JGW untuk {jpg.name} tidak ditemukan.")

        transform = baca_jgw(jgw)
        tif = OUTPUT_DIR / f"{jpg.stem}.tif"

        with rasterio.open(jpg) as src:
            profile = src.profile.copy()
            profile.update(
                driver="GTiff",
                transform=transform,
                crs=CRS,
                compress="lzw",
            )
            # Hapus opsi khusus JPEG agar tidak error di GTiff
            for key in ("photometric", "quality"):
                profile.pop(key, None)

            with rasterio.open(tif, "w", **profile) as dst:
                dst.write(src.read())

        print(f"[BERHASIL] {jpg.name} -> {tif.name}")
        berhasil += 1

    except Exception as e:
        print(f"[GAGAL] {jpg.name}: {e}")
        gagal += 1

print("\n========== SELESAI ==========")
print(f"Jumlah JPG   : {len(images)}")
print(f"Berhasil     : {berhasil}")
print(f"Gagal        : {gagal}")
print(f"Folder output: {OUTPUT_DIR}")