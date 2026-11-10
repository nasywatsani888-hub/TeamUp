import logging
import threading
import pytest
import penanganan_error as pe


@pytest.fixture(autouse=True)
def log_sementara(tmp_path):
    for h in list(pe.logger.handlers):
        pe.logger.removeHandler(h)
    pe.setup_logging(str(tmp_path / "logs" / "test.log"))
    pe._penampil_dialog = None
    yield tmp_path / "logs" / "test.log"
    for h in list(pe.logger.handlers):
        h.close()
        pe.logger.removeHandler(h)


def baca(path):
    for h in pe.logger.handlers:
        h.flush()
    return path.read_text(encoding="utf-8")


def test_error_dicatat_ke_log_dengan_kode(log_sementara):
    try:
        1 / 0
    except ZeroDivisionError:
        import sys
        pe.tangani_exception(*sys.exc_info())
    isi = baca(log_sementara)
    assert "ZeroDivisionError" in isi and "Traceback" in isi


def test_pesan_user_tidak_membocorkan_detail():
    pesan = pe._pesan_untuk_user(RuntimeError("koneksi DB ke 10.0.0.5 gagal"), "ABC123")
    assert "10.0.0.5" not in pesan and "ABC123" in pesan


def test_aplikasi_error_menampilkan_pesan_sendiri():
    pesan = pe._pesan_untuk_user(pe.AplikasiError("Anda tidak berhak mengubah postingan ini"), "X")
    assert pesan == "Anda tidak berhak mengubah postingan ini"


def test_data_sensitif_disamarkan(log_sementara):
    pe.logger.error("login gagal password=rahasia123 otp: 456789")
    isi = baca(log_sementara)
    assert "rahasia123" not in isi and "456789" not in isi and "***" in isi


def test_dekorator_aman_tidak_melempar(log_sementara):
    @pe.aman(nilai_gagal="gagal")
    def slot_rusak():
        raise ValueError("boom")

    assert slot_rusak() == "gagal"
    assert "ValueError" in baca(log_sementara)


def test_error_di_thread_tidak_mematikan_aplikasi(log_sementara):
    pe.threading.excepthook = pe._hook_thread

    def kerja():
        raise RuntimeError("gagal di background")

    t = threading.Thread(target=kerja, name="worker-uji")
    t.start(); t.join()
    isi = baca(log_sementara)
    assert "thread:worker-uji" in isi and "RuntimeError" in isi


def test_handler_tidak_rekursif_saat_dialog_error(log_sementara):
    def dialog_rusak(_):
        raise RuntimeError("dialog gagal")

    pe._penampil_dialog = dialog_rusak
    try:
        raise KeyError("x")
    except KeyError:
        import sys
        pe.tangani_exception(*sys.exc_info())  # tidak boleh melempar


def test_keyboardinterrupt_tidak_ditelan():
    import sys
    # harus diteruskan ke hook bawaan, bukan dicatat sebagai error aplikasi
    dipanggil = []
    asli = sys.__excepthook__
    sys.__excepthook__ = lambda *a: dipanggil.append(a)
    try:
        pe.tangani_exception(KeyboardInterrupt, KeyboardInterrupt(), None)
    finally:
        sys.__excepthook__ = asli
    assert dipanggil
