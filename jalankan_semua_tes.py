#!/usr/bin/env python3
# jalankan_semua_tes.py — Satu pintu untuk menjalankan SEMUA tes TeamUp + ringkasan hasil (Pertemuan 13)
#
# Masalah sebelumnya: ada 9 berkas tes dengan format laporan berbeda-beda, harus dijalankan satu per satu, dan
# beberapa (tes_thread, tes_paginasi) mengubah teamup.db asli sehingga harus di-`git restore` setiap kali.
#
# Pelari ini:
#   1. menjalankan tiap tes di PROSES TERPISAH (satu tes yang crash / macet tidak menjatuhkan yang lain),
#   2. mengisolasi tiap tes: salinan database sendiri (TEAMUP_DB), folder data sendiri (TEAMUP_DATA), kunci acak
#      (tidak terpengaruh .env milik developer), dan tanpa jendela (offscreen),
#   3. membuktikan teamup.db ASLI tidak berubah (sidik jari SHA-256 sebelum dan sesudah),
#   4. membaca hasil dari kode keluar + keluaran tes, dan membedakan: LULUS / GAGAL (asersi salah) / ERROR (crash)
#      / TIMEOUT (macet) / FLAKY (hasil berubah-ubah, dengan --ulangi),
#   5. jujur tentang kualitas tes: tes tanpa asersi ([LULUS]/[GAGAL]) ditandai "tanpa asersi", karena kode keluar 0
#      di sana hanya berarti "tidak crash", bukan "hasilnya benar".
#
# Contoh:
#   python3 jalankan_semua_tes.py                 semua tes
#   python3 jalankan_semua_tes.py keamanan crud   hanya tes yang namanya memuat kata itu
#   python3 jalankan_semua_tes.py --ulangi 3      jalankan tiap tes 3x, tandai yang hasilnya tidak konsisten (flaky)
#   python3 jalankan_semua_tes.py --detail        tampilkan seluruh keluaran tiap tes
#   python3 jalankan_semua_tes.py --json laporan.json   simpan laporan untuk dibaca program lain
#   python3 jalankan_semua_tes.py --tampil-gui    jendela sungguhan (bukan offscreen) saat melihat tes UI
#
# Kode keluar: 0 kalau semua lulus, 1 kalau ada yang gagal / error / timeout / flaky. Hanya modul bawaan Python.
import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

FOLDER_SKRIP = os.path.dirname(os.path.abspath(__file__))
BATAS_DETIK_BAWAAN = 300

POLA_LULUS_GAGAL = re.compile(r"LULUS:\s*(\d+)\s+GAGAL:\s*(\d+)")
POLA_UNITTEST = re.compile(r"Ran (\d+) tests? in")
POLA_ITEM = re.compile(r"^\s*\[(LULUS|GAGAL)\]", re.MULTILINE)
POLA_TRACEBACK = re.compile(r"Traceback \(most recent call last\)")
POLA_KESIMPULAN = re.compile(r"^\s*KESIMPULAN:\s*(.+)$", re.MULTILINE)


# ============================================================== 1. Menemukan tes
def cari_tes(folder, pola, lewati):
    """Semua tes_*.py di 'folder' (urut nama). 'pola' = kata kunci pada nama; kosong = semua."""
    semua = sorted(n for n in os.listdir(folder) if n.startswith("tes_") and n.endswith(".py"))
    if pola:
        semua = [n for n in semua if any(p.lower() in n.lower() for p in pola)]
    return [n for n in semua if not any(l.lower() in n.lower() for l in lewati)]


def sidik_jari(path):
    """SHA-256 sebuah berkas (None kalau tidak ada). Dipakai untuk membuktikan teamup.db asli tidak berubah."""
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for potongan in iter(lambda: f.read(1024 * 1024), b""):
            h.update(potongan)
    return h.hexdigest()


# ============================================================== 2. Membaca hasil
def analisis(keluaran, kode, habis_waktu):
    """Ubah keluaran mentah + kode keluar menjadi ringkasan. Urutan prioritas pembacaan jumlah pemeriksaan:
       'LULUS: n  GAGAL: m' (skrip bergaya TeamUp) -> 'Ran n tests' (unittest) -> hitung baris [LULUS]/[GAGAL]."""
    lulus = gagal = None
    jenis = "tanpa asersi"
    kesimpulan = POLA_KESIMPULAN.findall(keluaran)
    if kesimpulan:
        jenis = "ambang"                     # skrip ukur (memori / responsif): kode keluar ditentukan oleh ambang batas
    cocok = POLA_LULUS_GAGAL.findall(keluaran)
    if cocok:
        lulus, gagal = int(cocok[-1][0]), int(cocok[-1][1])
        jenis = "asersi"
    elif POLA_UNITTEST.search(keluaran):
        total = int(POLA_UNITTEST.search(keluaran).group(1))
        m = re.search(r"FAILED \(([^)]*)\)", keluaran)
        salah = sum(int(x) for x in re.findall(r"=(\d+)", m.group(1))) if m else 0
        lulus, gagal, jenis = total - salah, salah, "unittest"
    else:
        item = POLA_ITEM.findall(keluaran)
        if item:
            lulus, gagal, jenis = item.count("LULUS"), item.count("GAGAL"), "asersi"

    ada_traceback = bool(POLA_TRACEBACK.search(keluaran))
    baris_gagal = [b.strip() for b in keluaran.splitlines() if "[GAGAL]" in b][:12]
    if habis_waktu:
        status = "TIMEOUT"
    elif kode != 0 and ada_traceback and not (gagal or 0):
        status = "ERROR"
    elif kode != 0 or (gagal or 0) > 0:
        status = "GAGAL"
    else:
        status = "LULUS"
    ringkasan_error = ""
    if status == "ERROR":
        baris = [b for b in keluaran.strip().splitlines() if b.strip()]
        ringkasan_error = baris[-1][:160] if baris else ""
    return {"status": status, "jenis": jenis, "lulus": lulus, "gagal": gagal, "kode": kode,
            "kesimpulan": kesimpulan[-1].strip() if kesimpulan else "",
            "baris_gagal": baris_gagal, "ringkasan_error": ringkasan_error}


# ============================================================== 3. Menjalankan satu tes
def jalankan_satu(folder, nama, batas, tampil_gui, pakai_env, induk_tmp):
    """Jalankan satu berkas tes di proses terpisah dengan lingkungan terisolasi. Mengembalikan dict hasil."""
    tmp = tempfile.mkdtemp(prefix=f"{nama[:-3]}_", dir=induk_tmp)
    db_asli = os.path.join(folder, "teamup.db")
    db_salinan = os.path.join(tmp, "teamup.db")
    if os.path.isfile(db_asli):
        shutil.copy2(db_asli, db_salinan)
    env = os.environ.copy()
    env["PYTHONPATH"] = folder + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env["TEAMUP_DATA"] = os.path.join(tmp, "data")
    env["TEAMUP_DB"] = db_salinan
    if not tampil_gui:
        env["QT_QPA_PLATFORM"] = "offscreen"
    if not pakai_env:
        env["HMAC_SECRET_KEY"] = secrets.token_hex(32)       # tidak terpengaruh .env developer (baca_env tidak menimpa)
        env.pop("TEAMUP_ADMIN", None)
    mulai = time.perf_counter()
    habis_waktu = False
    try:
        hasil = subprocess.run([sys.executable, nama], cwd=folder, env=env, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=batas)
        keluaran, kode = hasil.stdout + hasil.stderr, hasil.returncode
    except subprocess.TimeoutExpired as e:
        habis_waktu = True
        sisa = (e.stdout or b"") if isinstance(e.stdout, bytes) else (e.stdout or "")
        keluaran = sisa.decode("utf-8", "replace") if isinstance(sisa, bytes) else sisa
        kode = -1
    durasi = time.perf_counter() - mulai
    shutil.rmtree(tmp, ignore_errors=True)
    hasil = analisis(keluaran, kode, habis_waktu)
    hasil.update(nama=nama, durasi=durasi, keluaran=keluaran)
    return hasil


def gabung_pengulangan(daftar):
    """Beberapa kali jalan untuk tes yang sama -> satu hasil. Hasil berbeda antar-jalan = FLAKY."""
    if len(daftar) == 1:
        return daftar[0]
    status = [h["status"] for h in daftar]
    terakhir = dict(daftar[-1])
    terakhir["durasi"] = sum(h["durasi"] for h in daftar) / len(daftar)
    terakhir["pengulangan"] = status
    if len(set(status)) > 1:
        terakhir["status"] = "FLAKY"
        terakhir["baris_gagal"] = next((h["baris_gagal"] for h in daftar if h["status"] != "LULUS"), [])
    return terakhir


# ============================================================== 4. Tampilan
WARNA = {"LULUS": "32", "GAGAL": "31", "ERROR": "31", "TIMEOUT": "33", "FLAKY": "33"}


def berwarna(teks, status, aktif):
    return f"\033[{WARNA.get(status, '0')}m{teks}\033[0m" if aktif else teks


def keterangan(h):
    if h["lulus"] is None and h["kesimpulan"]:
        return f"ambang batas: {h['kesimpulan']}"[:56]
    if h["lulus"] is None:
        return "tanpa asersi (hanya diperiksa tidak crash)"
    jenis = "unittest" if h["jenis"] == "unittest" else "pemeriksaan"
    total = h["lulus"] + (h["gagal"] or 0)
    return f"{h['lulus']}/{total} {jenis}"


def cetak_hasil(indeks, jumlah, h, warna):
    status = berwarna(f"{h['status']:<7}", h["status"], warna)
    nama = h["nama"][:-3]
    lebar = len(str(jumlah))
    print(f" [{indeks:>{lebar}}/{jumlah}] {nama:<22} {status} {keterangan(h):<56} {h['durasi']:6.1f} dtk", flush=True)
    if h["status"] == "FLAKY":
        print(f"        hasil tiap jalan: {', '.join(h['pengulangan'])}")
    for b in h["baris_gagal"]:
        print(f"        {b}")
    if h["status"] == "ERROR" and h["ringkasan_error"]:
        print(f"        crash: {h['ringkasan_error']}")
    if h["status"] == "TIMEOUT":
        print("        melebihi batas waktu; kemungkinan macet (deadlock / menunggu dialog)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Jalankan semua tes TeamUp dengan isolasi dan ringkasan.")
    ap.add_argument("pola", nargs="*", help="kata kunci nama tes (kosong = semua)")
    ap.add_argument("--folder", default=FOLDER_SKRIP, help="folder berisi tes_*.py (bawaan: folder skrip ini)")
    ap.add_argument("--lewati", nargs="*", default=[], help="kata kunci nama tes yang dilewati")
    ap.add_argument("--ulangi", type=int, default=1, help="jalankan tiap tes N kali; hasil berbeda = FLAKY")
    ap.add_argument("--batas", type=int, default=BATAS_DETIK_BAWAAN, help="batas waktu per tes (detik)")
    ap.add_argument("--detail", action="store_true", help="tampilkan seluruh keluaran tiap tes")
    ap.add_argument("--json", metavar="BERKAS", help="simpan laporan JSON")
    ap.add_argument("--daftar", action="store_true", help="hanya tampilkan daftar tes lalu keluar")
    ap.add_argument("--tampil-gui", action="store_true", help="jendela sungguhan (bukan offscreen)")
    ap.add_argument("--pakai-env", action="store_true", help="biarkan .env / HMAC_SECRET_KEY milik developer dipakai")
    a = ap.parse_args(argv)

    folder = os.path.abspath(a.folder)
    tes = cari_tes(folder, a.pola, a.lewati)
    if a.daftar:
        print("\n".join(t[:-3] for t in tes) or "(tidak ada tes)")
        return 0
    if not tes:
        print("Tidak ada berkas tes_*.py yang cocok.")
        return 1

    warna = sys.stdout.isatty()
    db_asli = os.path.join(folder, "teamup.db")
    sidik_awal = sidik_jari(db_asli)
    print("=== MENJALANKAN TES TEAMUP ===")
    print(f"Folder   : {folder}")
    print(f"Tampilan : {'jendela sungguhan' if a.tampil_gui else 'tanpa jendela (offscreen)'}")
    print(f"Isolasi  : database salinan, folder data sendiri, kunci acak per tes"
          + (f" | diulang {a.ulangi}x" if a.ulangi > 1 else ""))
    print()

    induk_tmp = tempfile.mkdtemp(prefix="teamup_semua_tes_")
    hasil_semua = []
    mulai = time.perf_counter()
    try:
        for i, nama in enumerate(tes, 1):
            jalan = [jalankan_satu(folder, nama, a.batas, a.tampil_gui, a.pakai_env, induk_tmp) for _ in range(max(1, a.ulangi))]
            h = gabung_pengulangan(jalan)
            hasil_semua.append(h)
            cetak_hasil(i, len(tes), h, warna)
            if a.detail:
                print("-" * 70 + "\n" + h["keluaran"].rstrip() + "\n" + "-" * 70)
    except KeyboardInterrupt:
        print("\nDihentikan oleh pengguna.")
    finally:
        shutil.rmtree(induk_tmp, ignore_errors=True)
    total_durasi = time.perf_counter() - mulai

    hitung = {s: sum(1 for h in hasil_semua if h["status"] == s) for s in ("LULUS", "GAGAL", "ERROR", "TIMEOUT", "FLAKY")}
    total_lulus = sum(h["lulus"] or 0 for h in hasil_semua)
    total_gagal = sum(h["gagal"] or 0 for h in hasil_semua)
    tanpa_asersi = [h["nama"][:-3] for h in hasil_semua
                    if h["status"] == "LULUS" and h["lulus"] is None and not h["kesimpulan"]]
    sidik_akhir = sidik_jari(db_asli)

    print("\n" + "=" * 70)
    print("RINGKASAN")
    print(f"  Berkas tes   : {len(hasil_semua)}   LULUS {hitung['LULUS']}   GAGAL {hitung['GAGAL']}   ERROR {hitung['ERROR']}"
          f"   TIMEOUT {hitung['TIMEOUT']}   FLAKY {hitung['FLAKY']}")
    print(f"  Pemeriksaan  : {total_lulus + total_gagal}   lulus {total_lulus}   gagal {total_gagal}")
    print(f"  Waktu total  : {total_durasi:.1f} detik")
    if tanpa_asersi:
        print(f"  Catatan      : {', '.join(tanpa_asersi)} tidak punya asersi; kode keluar 0 hanya berarti tidak crash.")
    if sidik_awal is None:
        print("  teamup.db    : tidak ada di folder ini")
    elif sidik_awal == sidik_akhir:
        print("  teamup.db    : asli TIDAK berubah (sidik jari SHA-256 sama sebelum dan sesudah)")
    else:
        print("  teamup.db    : BERUBAH! Ada tes yang menulis ke database asli (isolasi bocor).")
    semua_baik = (hitung["LULUS"] == len(hasil_semua) and len(hasil_semua) > 0 and sidik_awal == sidik_akhir)
    print("  HASIL        : " + berwarna("SEMUA LULUS" if semua_baik else "ADA YANG BERMASALAH", "LULUS" if semua_baik else "GAGAL", warna))

    if a.json:
        laporan = {"waktu": time.strftime("%Y-%m-%d %H:%M:%S"), "durasi_total": round(total_durasi, 2),
                   "database_asli_berubah": sidik_awal != sidik_akhir,
                   "tes": [{k: (round(v, 2) if k == "durasi" else v) for k, v in h.items() if k != "keluaran"} for h in hasil_semua]}
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(laporan, f, indent=2, ensure_ascii=False)
        print(f"  Laporan JSON : {a.json}")
    return 0 if semua_baik else 1


if __name__ == "__main__":
    sys.exit(main())
