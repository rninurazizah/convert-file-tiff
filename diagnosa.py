
from pathlib import Path

INPUT_DIR = Path(__file__).resolve().parent / "data" / "610501"

# True jika JGW berada di subfolder
RECURSIVE = True



import shutil
from pathlib import Path

for drive in ["C:\\", "D:\\", "G:\\"]:
    try:
        total, used, free = shutil.disk_usage(drive)
        print(f"\nDrive {drive}")
        print(f"Total      : {total / (1024**3):.2f} GB")
        print(f"Terpakai   : {used / (1024**3):.2f} GB")
        print(f"Tersedia   : {free / (1024**3):.2f} GB")
    except Exception as e:
        print(f"\nDrive {drive}: {type(e).__name__}: {e}")

if RECURSIVE:
    files = sorted(
        p for p in INPUT_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() == ".jgw"
    )
else:
    files = sorted(
        p for p in INPUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() == ".jgw"
    )

print(f"Jumlah JGW ditemukan: {len(files)}\n")

jumlah_error = 0

for path in files:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()

        values = []
        for nomor, line in enumerate(lines, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                values.append(float(line))
            except ValueError:
                raise ValueError(
                    f"Baris {nomor} bukan angka: {line!r}"
                )

        if len(values) != 6:
            raise ValueError(
                f"Seharusnya 6 angka, ditemukan {len(values)}"
            )

    except Exception as e:
        jumlah_error += 1
        print(f"\nERROR: {path.name}")
        print(f"Penyebab: {type(e).__name__}: {e}")

        try:
            print("Isi file:")
            print(repr(path.read_bytes()[:500]))
        except Exception as baca_error:
            print(f"Gagal membaca bytes: {baca_error}")

        # Tampilkan maksimal 10 file error agar hasil tidak terlalu panjang
        if jumlah_error >= 10:
            break

print(f"\nJumlah error yang ditampilkan: {jumlah_error}")
