"""Shared config: book list (Drive file ids) and dataset paths."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "dataset" / "raw"
CLEANED_DIR = ROOT / "dataset" / "cleaned"

BOOKS = [
    {
        "slug": "chien_quoc_sach",
        "name": "Chiến Quốc Sách",
        "han_id": "1mI0pRTRAKs9uOY16vPo5PJBtNeB1vO5N",
        "viet_id": "1lPYxr1j7dy5rziCDyd94uWNPWbFXE2YM",
    },
    {
        "slug": "liet_nu_truyen",
        "name": "Liệt Nữ Truyện",
        "han_id": "1sUM_MNpThyFammF7BC45XdCINemgu8eK",
        "viet_id": "10bXyKWCuGFqZQjybfuUbI1R6sEM6rTg0",
    },
    {
        "slug": "su_ky_tu_ma_thien",
        "name": "Sử Ký Tư Mã Thiên",
        "han_id": "1S5ijemxpcQulqKFPIl0VC2_reZQXN3kM",
        "viet_id": "1AF87BbpWObUDdS4vIyDXVJnvAZmS0OYg",
    },
    {
        "slug": "tam_quoc_chi",
        "name": "Tam Quốc Chí",
        "han_id": "1-RuBLkFIsIdk9_rbH9LQtnNn2n0hdEmk",
        "viet_id": "1yAHRP3x-sXDtleikiThq_ntAIKK5IllH",
    },
]
