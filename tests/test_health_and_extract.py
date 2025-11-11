import io
import os
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


def test_health_ok():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_extract_rejects_when_no_file():
    res = client.post("/extraction/extract-text")
    assert res.status_code == 422 or res.status_code == 400


def test_extract_accepts_pdf_stub(monkeypatch):
    # Use repository PDF and mock PDF processing to avoid external dependencies
    from app.utils import tools as tools_mod

    def fake_process_pdf(pdf_bytes: bytes, filename: str = "unknown"):
        assert isinstance(pdf_bytes, (bytes, bytearray)) and len(pdf_bytes) > 0
        return {"1": "$x^2 + y^2 = z^2$"}

    monkeypatch.setattr(tools_mod, "process_pdf_with_tool", fake_process_pdf)

    pdf_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Blockchain test-case.pdf"))
    with open(pdf_path, "rb") as f:
        data = f.read()

    files = {"file": ("Blockchain test-case.pdf", io.BytesIO(data), "application/pdf")}
    res = client.post("/extraction/extract-text", files=files)
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") is True
    assert isinstance(body.get("extracted_text"), dict)
    assert "1" in body["extracted_text"]

