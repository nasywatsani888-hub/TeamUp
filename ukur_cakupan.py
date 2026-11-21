#!/usr/bin/env python3
# ukur_cakupan.py — Cakupan tes (code coverage): berapa persen BARIS kode yang benar-benar dijalankan oleh tes (Pertemuan 13)
#
# Pertanyaan yang dijawab: "Bagian kode mana yang TIDAK pernah disentuh tes sama sekali?" Baris yang tidak pernah
# dijalankan oleh tes pasti tidak terjaga dari regresi; di situlah bug paling mungkin bersembunyi.
#
# Cara kerja: tiap berkas tes dijalankan di proses terpisah (terisolasi seperti jalankan_semua_tes.py). Di dalam proses
# itu, sebuah pengumpul mencatat setiap baris kode proyek yang dieksekusi. Hasil semua tes digabung, lalu dibandingkan
# dengan DAFTAR SEMUA BARIS yang bisa dijalankan (diambil dari bytecode hasil kompilasi, bukan menghitung baris teks).
#
# Dua pengumpul (dipilih otomatis):
#   sys.monitoring (Python 3.12+) : peristiwa LINE yang dimatikan per baris setelah tercatat pertama kali -> overhead hampir nol
#   sys.settrace   (Python lama)  : memanggil fungsi pelacak untuk tiap baris -> lebih lambat, hasil sama
#
# Yang TIDAK dicakup (disampaikan terus terang): ini cakupan BARIS, bukan cakupan CABANG. Baris `if x: a() else: b()` yang
# dua-duanya ada di satu baris dihitung tercakup walau cabang lainnya tak pernah diuji. Lebih penting lagi: baris yang
# "dijalankan" belum tentu "diperiksa hasilnya". Cakupan tinggi bukan jaminan benar; cakupan rendah adalah jaminan ADA bagian
# yang tidak terjaga. Tes yang menjalankan proses anak sendiri (mis. tes_skala) tidak terukur di proses anaknya.
#
# Pengecualian: tulis `# pragma: no cover` di akhir sebuah baris untuk mengecualikannya; kalau baris itu membuka blok
# (def / if / else / try ...), seluruh blok ikut dikecualikan. Docstring tidak dihitung.
#
# Contoh:
#   python3 ukur_cakupan.py                     semua tes
#   python3 ukur_cakupan.py keamanan crud       hanya tes tertentu
#   python3 ukur_cakupan.py --detail            tampilkan baris yang belum tercakup untuk SEMUA berkas
#   python3 ukur_cakupan.py --minimum 60        keluar dengan kode 1 kalau total cakupan < 60% (gerbang mutu)
#   python3 ukur_cakupan.py --html cakupan.html laporan HTML berwarna per baris (untuk presentasi)
#   python3 ukur_cakupan.py --json cakupan.json ringkasan untuk program lain
#
# Hanya modul bawaan Python.
import argparse
import ast
import html
import json
import os
import re
import runpy
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types

BASE = os.path.dirname(os.path.abspath(__file__))
FOLDER_DIKECUALIKAN = {"__pycache__", ".git", ".venv", "venv", "env", "node_modules", "build", "dist", "site-packages", "tmp"}
POLA_TES = re.compile(r"^(tes_|test_|demo_)")
BERKAS_ALAT = {"jalankan_semua_tes.py", "profil_cpu.py", "ukur_cakupan.py"}


# ============================================================== 1. Daftar baris yang bisa dijalankan
def cari_berkas_sumber(folder, termasuk_tes=False):
    """Semua .py proyek yang dihitung cakupannya (tanpa tes, alat ukur, dan folder pustaka)."""
    hasil = []
    for induk, subfolder, daftar in os.walk(folder):
        subfolder[:] = sorted(d for d in subfolder if d not in FOLDER_DIKECUALIKAN and not d.startswith("."))
        for nama in sorted(daftar):
            if not nama.endswith(".py"):
                continue
            if not termasuk_tes and (POLA_TES.match(nama) or nama in BERKAS_ALAT) and induk == folder:
                continue
            hasil.append(os.path.realpath(os.path.join(induk, nama)))
    return hasil


def _telusuri_kode(kode, garis):
    for _awal, _akhir, baris in kode.co_lines():
        if baris is not None and baris > 0:
            garis.add(baris)
    for konstanta in kode.co_consts:
        if isinstance(konstanta, types.CodeType):
            _telusuri_kode(konstanta, garis)


def baris_dapat_dijalankan(path):
    """(dapat_dijalankan, dikecualikan). Diambil dari bytecode: baris yang benar-benar punya instruksi.
    Docstring dan baris/blok bertanda `# pragma: no cover` dikeluarkan dari hitungan."""
    with open(path, "r", encoding="utf-8") as f:
        sumber = f.read()
    try:
        kode = compile(sumber, path, "exec")
        pohon = ast.parse(sumber)
    except (SyntaxError, ValueError):
        return set(), set()
    garis = set()
    _telusuri_kode(kode, garis)
    dikecualikan = set()
    for node in ast.walk(pohon):                                   # docstring bukan "logika": jangan dihitung
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            pertama = node.body[0]
            if isinstance(pertama, ast.Expr) and isinstance(getattr(pertama, "value", None), ast.Constant) \
                    and isinstance(pertama.value.value, str):
                dikecualikan.update(range(pertama.lineno, (pertama.end_lineno or pertama.lineno) + 1))
    bertanda = {i for i, b in enumerate(sumber.splitlines(), 1) if "pragma: no cover" in b}
    if bertanda:
        for node in ast.walk(pohon):
            if getattr(node, "lineno", None) in bertanda:
                dikecualikan.update(range(node.lineno, (getattr(node, "end_lineno", None) or node.lineno) + 1))
        dikecualikan.update(bertanda)
    return garis - dikecualikan, dikecualikan & garis


# ============================================================== 2. Pengumpul (berjalan di proses tes)
class Pengumpul:
    """Mencatat (berkas -> kumpulan nomor baris) yang dieksekusi. Hanya berkas target yang dicatat."""

    def __init__(self, target, mode="otomatis"):
        self.target = set(target)
        self.terlihat = {}
        self._keputusan = {}                       # co_filename -> path target atau None (disimpan agar cepat)
        self.mode = mode if mode != "otomatis" else ("monitoring" if hasattr(sys, "monitoring") else "settrace")
        self._id = None

    def _cocokkan(self, nama_berkas):
        hasil = self._keputusan.get(nama_berkas, False)
        if hasil is False:
            try:
                nyata = os.path.realpath(nama_berkas)
            except (OSError, ValueError):
                nyata = nama_berkas
            hasil = nyata if nyata in self.target else None
            self._keputusan[nama_berkas] = hasil
        return hasil

    def mulai(self):
        if self.mode == "monitoring":
            mon = sys.monitoring
            self._id = mon.COVERAGE_ID
            mon.use_tool_id(self._id, "teamup_cakupan")

            def saat_baris(kode, baris):
                target = self._cocokkan(kode.co_filename)
                if target is not None:
                    self.terlihat.setdefault(target, set()).add(baris)
                return mon.DISABLE                  # baris ini sudah tercatat: tidak perlu diberi tahu lagi (overhead ~0)

            mon.register_callback(self._id, mon.events.LINE, saat_baris)
            mon.set_events(self._id, mon.events.LINE)
        else:
            def pelacak(frame, peristiwa, _arg):
                target = self._cocokkan(frame.f_code.co_filename)
                if target is None:
                    return None
                if peristiwa in ("line", "call"):
                    self.terlihat.setdefault(target, set()).add(frame.f_lineno)
                return pelacak
            self._pelacak = pelacak
            sys.settrace(pelacak)
            threading.settrace(pelacak)

    def berhenti(self):
        if self.mode == "monitoring":
            mon = sys.monitoring
            mon.set_events(self._id, 0)
            mon.register_callback(self._id, mon.events.LINE, None)
            mon.free_tool_id(self._id)
        else:
            sys.settrace(None)
            threading.settrace(None)

    def sebagai_dict(self):
        return {berkas: sorted(garis) for berkas, garis in self.terlihat.items()}


def jalankan_anak(argumen):
    """Titik masuk proses anak: mulai pengumpul -> jalankan berkas tes seperti `python3 tes_x.py` -> simpan hasil."""
    tes, keluar, daftar_target, mode = argumen
    with open(daftar_target, "r", encoding="utf-8") as f:
        target = json.load(f)
    pengumpul = Pengumpul(target, mode)
    kode_keluar = 0
    sys.argv = [tes]
    sys.path.insert(0, os.path.dirname(os.path.abspath(tes)))
    pengumpul.mulai()
    try:
        runpy.run_path(tes, run_name="__main__")
    except SystemExit as e:
        kode_keluar = e.code if isinstance(e.code, int) else (0 if e.code in (None, "") else 1)
    finally:
        pengumpul.berhenti()
        with open(keluar, "w", encoding="utf-8") as f:
            json.dump(pengumpul.sebagai_dict(), f)
    sys.stdout.flush()
    os._exit(kode_keluar)                          # tanpa penutupan Qt/thread yang kadang crash saat keluar


# ============================================================== 3. Orkestrasi (proses induk)
def sidik_jari(path):
    import hashlib
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def cari_tes(folder, pola, lewati):
    semua = sorted(n for n in os.listdir(folder) if n.startswith("tes_") and n.endswith(".py"))
    if pola:
        semua = [n for n in semua if any(p.lower() in n.lower() for p in pola)]
    return [n for n in semua if not any(x.lower() in n.lower() for x in lewati)]


def jalankan_tes_terukur(folder, nama, target_json, mode, batas, induk_tmp, tampil_gui):
    tmp = tempfile.mkdtemp(prefix=f"{nama[:-3]}_", dir=induk_tmp)
    db_asli = os.path.join(folder, "teamup.db")
    db_salinan = os.path.join(tmp, "teamup.db")
    if os.path.isfile(db_asli):
        shutil.copy2(db_asli, db_salinan)
    env = os.environ.copy()
    env.update(PYTHONPATH=folder + os.pathsep + env.get("PYTHONPATH", ""), PYTHONIOENCODING="utf-8",
               TEAMUP_DATA=os.path.join(tmp, "data"), TEAMUP_DB=db_salinan, HMAC_SECRET_KEY=secrets.token_hex(32))
    env.pop("TEAMUP_ADMIN", None)
    if not tampil_gui:
        env["QT_QPA_PLATFORM"] = "offscreen"
    keluar = os.path.join(tmp, "terlihat.json")
    mulai = time.perf_counter()
    status, kode = "LULUS", 0
    try:
        hasil = subprocess.run([sys.executable, os.path.abspath(__file__), "--anak", nama, keluar, target_json, mode],
                               cwd=folder, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=batas)
        kode = hasil.returncode
        if kode != 0:
            status = "GAGAL"
    except subprocess.TimeoutExpired:
        status, kode = "TIMEOUT", -1
    durasi = time.perf_counter() - mulai
    terlihat = {}
    if os.path.isfile(keluar):
        with open(keluar, "r", encoding="utf-8") as f:
            terlihat = {b: set(g) for b, g in json.load(f).items()}
    shutil.rmtree(tmp, ignore_errors=True)
    return {"nama": nama, "status": status, "durasi": durasi, "terlihat": terlihat}


def ringkas_rentang(nomor):
    """[1,2,3,7,9,10] -> '1-3, 7, 9-10'."""
    nomor = sorted(nomor)
    bagian, awal, akhir = [], None, None
    for n in nomor:
        if awal is None:
            awal = akhir = n
        elif n == akhir + 1:
            akhir = n
        else:
            bagian.append(f"{awal}-{akhir}" if akhir > awal else str(awal))
            awal = akhir = n
    if awal is not None:
        bagian.append(f"{awal}-{akhir}" if akhir > awal else str(awal))
    return ", ".join(bagian)


def hitung_cakupan(folder, target, terlihat_gabungan):
    """Per berkas: baris dapat dijalankan, yang tercakup, yang belum, persen."""
    hasil = {}
    for path in target:
        wajib, dikecualikan = baris_dapat_dijalankan(path)
        kena = terlihat_gabungan.get(path, set()) & wajib
        hasil[path] = {"berkas": os.path.relpath(path, folder), "wajib": wajib, "kena": kena,
                       "belum": wajib - kena, "dikecualikan": dikecualikan,
                       "persen": 100.0 * len(kena) / len(wajib) if wajib else 100.0}
    return hasil


def batang(persen, lebar=20):
    isi = round(persen / 100 * lebar)
    return "█" * isi + "·" * (lebar - isi)


# ============================================================== 4. Laporan HTML
def tulis_html(path_html, folder, cakupan, total_persen):
    css = """
    :root{--bg:#fff;--fg:#1f2328;--garis:#d0d7de;--hijau:#dafbe1;--merah:#ffebe9;--abu:#f6f8fa;--kuning:#fff8c5}
    @media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--garis:#30363d;--hijau:#12301d;--merah:#3d1418;--abu:#161b22;--kuning:#3a2f00}}
    body{margin:0;padding:24px;background:var(--bg);color:var(--fg);font:14px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif}
    h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 8px}
    table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid var(--garis);padding:4px 8px;text-align:left}
    .bar{display:inline-block;width:140px;height:10px;background:var(--merah);border-radius:5px;overflow:hidden;vertical-align:middle}
    .bar>i{display:block;height:100%;background:#2da44e}
    pre{margin:0;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap}
    td.n{width:48px;text-align:right;color:#8b949e;user-select:none}
    tr.kena td{background:var(--hijau)}tr.belum td{background:var(--merah)}tr.kecuali td{background:var(--kuning)}
    .scroll{overflow-x:auto;border:1px solid var(--garis);border-radius:6px}
    a{color:#0969da}
    """
    urut = sorted(cakupan.values(), key=lambda d: d["persen"])
    baris_tabel = []
    for i, d in enumerate(urut):
        baris_tabel.append(
            f"<tr><td><a href='#f{i}'>{html.escape(d['berkas'])}</a></td><td>{len(d['wajib'])}</td><td>{len(d['kena'])}</td>"
            f"<td>{d['persen']:.1f}%</td><td><span class='bar'><i style='width:{d['persen']:.1f}%'></i></span></td></tr>")
    bagian = []
    for i, d in enumerate(urut):
        with open(os.path.join(folder, d["berkas"]), "r", encoding="utf-8") as f:
            sumber = f.read().splitlines()
        isi = []
        for no, teks in enumerate(sumber, 1):
            kelas = "kena" if no in d["kena"] else "belum" if no in d["belum"] else "kecuali" if no in d["dikecualikan"] else ""
            isi.append(f"<tr class='{kelas}'><td class='n'>{no}</td><td><pre>{html.escape(teks) or ' '}</pre></td></tr>")
        bagian.append(f"<h2 id='f{i}'>{html.escape(d['berkas'])} — {d['persen']:.1f}% "
                      f"({len(d['kena'])}/{len(d['wajib'])} baris)</h2><div class='scroll'><table>{''.join(isi)}</table></div>")
    dokumen = (f"<!doctype html><html lang='id'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
               f"<title>Cakupan tes TeamUp</title><style>{css}</style></head><body>"
               f"<h1>Cakupan tes TeamUp: {total_persen:.1f}%</h1><div>Dibuat {time.strftime('%Y-%m-%d %H:%M:%S')}. "
               f"Hijau = dijalankan tes, merah = belum pernah dijalankan, kuning = dikecualikan (<code>pragma: no cover</code>).</div>"
               f"<h2>Ringkasan per berkas (terendah dulu)</h2><div class='scroll'><table><tr><th>Berkas</th><th>Baris</th><th>Tercakup</th>"
               f"<th>%</th><th></th></tr>{''.join(baris_tabel)}</table></div>{''.join(bagian)}</body></html>")
    with open(path_html, "w", encoding="utf-8") as f:
        f.write(dokumen)


# ============================================================== 5. Program utama
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--anak":
        jalankan_anak(argv[1:5])
        return 0
    ap = argparse.ArgumentParser(description="Ukur cakupan baris kode TeamUp oleh suite tes.")
    ap.add_argument("pola", nargs="*", help="kata kunci nama tes (kosong = semua)")
    ap.add_argument("--folder", default=BASE, help="folder proyek (bawaan: folder skrip ini)")
    ap.add_argument("--lewati", nargs="*", default=[], help="kata kunci tes yang dilewati")
    ap.add_argument("--minimum", type=float, default=None, help="gerbang mutu: kode keluar 1 kalau total cakupan di bawah angka ini (%%)")
    ap.add_argument("--ambang", type=float, default=70.0, help="berkas di bawah angka ini diberi tanda peringatan (%%)")
    ap.add_argument("--detail", action="store_true", help="tampilkan baris yang belum tercakup untuk semua berkas")
    ap.add_argument("--termasuk-tes", action="store_true", help="hitung juga berkas tes_*.py / alat ukur")
    ap.add_argument("--batas", type=int, default=300, help="batas waktu per tes (detik)")
    ap.add_argument("--pengumpul", choices=("otomatis", "monitoring", "settrace"), default="otomatis")
    ap.add_argument("--tampil-gui", action="store_true")
    ap.add_argument("--html", metavar="BERKAS", help="tulis laporan HTML berwarna per baris")
    ap.add_argument("--json", metavar="BERKAS", help="tulis ringkasan JSON")
    a = ap.parse_args(argv)

    folder = os.path.realpath(a.folder)
    tes = cari_tes(folder, a.pola, a.lewati)
    target = cari_berkas_sumber(folder, a.termasuk_tes)
    if not tes or not target:
        print("Tidak ada tes atau tidak ada berkas sumber yang cocok.")
        return 1
    mode = a.pengumpul if a.pengumpul != "otomatis" else ("monitoring" if hasattr(sys, "monitoring") else "settrace")
    print("=== CAKUPAN TES TEAMUP (cakupan baris) ===")
    print(f"Folder    : {folder}")
    print(f"Pengumpul : {'sys.monitoring (overhead hampir nol)' if mode == 'monitoring' else 'sys.settrace (lebih lambat)'} | Python {sys.version.split()[0]}")
    print(f"Sasaran   : {len(target)} berkas sumber | {len(tes)} berkas tes\n")

    induk_tmp = tempfile.mkdtemp(prefix="teamup_cakupan_")
    target_json = os.path.join(induk_tmp, "target.json")
    with open(target_json, "w", encoding="utf-8") as f:
        json.dump(target, f)
    sidik_awal = sidik_jari(os.path.join(folder, "teamup.db"))
    hasil_tes, gabungan = [], {}
    mulai = time.perf_counter()
    try:
        for i, nama in enumerate(tes, 1):
            h = jalankan_tes_terukur(folder, nama, target_json, mode, a.batas, induk_tmp, a.tampil_gui)
            hasil_tes.append(h)
            for berkas, garis in h["terlihat"].items():
                gabungan.setdefault(berkas, set()).update(garis)
            jumlah = sum(len(g) for g in h["terlihat"].values())
            print(f" [{i:>{len(str(len(tes)))}}/{len(tes)}] {nama[:-3]:<22} {h['status']:<8} {jumlah:>6} baris tersentuh   {h['durasi']:6.1f} dtk", flush=True)
    finally:
        shutil.rmtree(induk_tmp, ignore_errors=True)
    total_durasi = time.perf_counter() - mulai

    cakupan = hitung_cakupan(folder, target, gabungan)
    total_wajib = sum(len(d["wajib"]) for d in cakupan.values())
    total_kena = sum(len(d["kena"]) for d in cakupan.values())
    total_persen = 100.0 * total_kena / total_wajib if total_wajib else 100.0

    print("\n" + "=" * 92)
    print("CAKUPAN PER BERKAS (terendah dulu)")
    print(f"  {'berkas':<34} {'baris':>6} {'tercakup':>9} {'%':>7}   ")
    urut = sorted(cakupan.values(), key=lambda d: d["persen"])
    for d in urut:
        tanda = " ⚠" if d["persen"] < a.ambang else ""
        print(f"  {d['berkas'][:34]:<34} {len(d['wajib']):>6} {len(d['kena']):>9} {d['persen']:6.1f}%   {batang(d['persen'])}{tanda}")
    print(f"\n  TOTAL: {total_kena:,} dari {total_wajib:,} baris dapat dijalankan tercakup = {total_persen:.1f}%")
    di_bawah = [d for d in urut if d["persen"] < a.ambang]
    print(f"  {len(di_bawah)} dari {len(urut)} berkas di bawah ambang {a.ambang:.0f}%  |  waktu {total_durasi:.1f} dtk")

    tampil = urut if a.detail else di_bawah[:5]
    if tampil:
        print("\nBARIS YANG BELUM PERNAH DIJALANKAN TES" + ("" if a.detail else " (5 berkas terendah; --detail untuk semua)"))
        for d in tampil:
            if d["belum"]:
                teks = ringkas_rentang(d["belum"])
                print(f"  {d['berkas']} ({len(d['belum'])} baris): {teks[:230]}{' ...' if len(teks) > 230 else ''}")

    semua_tercakup = [h["terlihat"] for h in hasil_tes]
    target_set = {p: cakupan[p]["wajib"] for p in cakupan}
    kontribusi = []
    for idx, h in enumerate(hasil_tes):
        sendiri, lain = set(), set()
        for p, wajib in target_set.items():
            sendiri |= {(p, n) for n in h["terlihat"].get(p, set()) & wajib}
            for j, t in enumerate(semua_tercakup):
                if j != idx:
                    lain |= {(p, n) for n in t.get(p, set()) & wajib}
        kontribusi.append((h["nama"][:-3], len(sendiri), len(sendiri - lain)))
    print("\nKONTRIBUSI TIAP TES (baris kode proyek yang disentuh | yang HANYA disentuh tes ini)")
    for nama, kena, unik in sorted(kontribusi, key=lambda x: -x[2]):
        print(f"  {nama:<22} {kena:>6} | {unik:>5} unik")

    if sidik_awal is not None:
        print("\n  teamup.db asli:", "TIDAK berubah" if sidik_jari(os.path.join(folder, "teamup.db")) == sidik_awal else "BERUBAH! (isolasi bocor)")
    kosong = [h["nama"][:-3] for h in hasil_tes if h["status"] == "LULUS" and not h["terlihat"]]
    if kosong:
        print(f"  Catatan: {', '.join(kosong)} tidak menyentuh kode proyek di prosesnya (kemungkinan menjalankan proses anak sendiri;"
              " cakupan di proses itu tidak terukur).")
    print("  Catatan: cakupan BARIS saja; baris yang dijalankan belum tentu diperiksa hasilnya.")
    if a.html:
        tulis_html(a.html, folder, cakupan, total_persen)
        print(f"  Laporan HTML: {a.html}")
    if a.json:
        laporan = {"total_persen": round(total_persen, 2), "baris_wajib": total_wajib, "baris_tercakup": total_kena,
                   "berkas": {d["berkas"]: {"persen": round(d["persen"], 2), "wajib": len(d["wajib"]), "tercakup": len(d["kena"]),
                                            "belum": sorted(d["belum"])} for d in urut},
                   "tes": [{"nama": h["nama"], "status": h["status"], "durasi": round(h["durasi"], 2)} for h in hasil_tes]}
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(laporan, f, indent=2, ensure_ascii=False)
        print(f"  Laporan JSON: {a.json}")
    gagal = [h["nama"] for h in hasil_tes if h["status"] != "LULUS"]
    if gagal:
        print(f"  PERINGATAN: tes berikut tidak lulus, cakupannya tidak lengkap: {', '.join(gagal)}")
    if a.minimum is not None:
        lolos = total_persen >= a.minimum
        print(f"  GERBANG MUTU: total {total_persen:.1f}% {'>=' if lolos else '<'} minimum {a.minimum:.1f}% -> {'LOLOS' if lolos else 'GAGAL'}")
        return 0 if lolos and not gagal else 1
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
