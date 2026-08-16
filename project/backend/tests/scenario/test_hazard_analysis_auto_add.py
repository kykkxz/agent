from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_if_empty


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


client = TestClient(app)


def login() -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "safety", "password": "Safety@123456"},
    )
    return response.json()["data"]["access_token"]


def list_hazards(token: str) -> dict:
    return client.get(
        "/api/v1/hazards",
        headers={"Authorization": f"Bearer {token}"},
        params={"page_size": 100},
    ).json()["data"]


def test_analysis_creates_one_aggregate_hazard(monkeypatch) -> None:
    token = login()
    before = list_hazards(token)["total"]

    monkeypatch.setattr(
        "app.routers.hazard_analysis.analyze_hazard_image",
        lambda *_args: {
            "job_id": "job-with-two-risks",
            "image_url": "/api/v1/files/hazard-analysis/job-with-two-risks/annotated.png",
            "original_url": "/api/v1/files/hazard-analysis/job-with-two-risks/original.png",
            "count": 2,
            "items": [
                {
                    "label": "临边防护缺失",
                    "risk": "高",
                    "note": "桥面左侧",
                    "fix": "立即设置防护栏杆。",
                },
                {
                    "label": "未佩戴安全帽",
                    "risk": "中",
                    "note": "作业区中央",
                    "fix": "进入现场前正确佩戴安全帽。",
                },
            ],
            "model": "test-vision-model",
        },
    )

    response = client.post(
        "/api/v1/hazard-analysis/analyze",
        headers={"Authorization": f"Bearer {token}"},
        data={"prompt": "识别全部隐患"},
        files={"image": ("site.png", b"fake-png", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["created_hazard"]["hazard_id"]
    assert payload["created_hazard"]["level"] == "critical"
    assert list_hazards(token)["total"] == before + 1

    detail = client.get(
        f"/api/v1/hazards/{payload['created_hazard']['hazard_id']}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["data"]
    assert "临边防护缺失" in detail["description"]
    assert "未佩戴安全帽" in detail["description"]
    assert detail["media"]["images"] == [payload["original_url"], payload["image_url"]]


def test_analysis_with_no_findings_does_not_create_hazard(monkeypatch) -> None:
    token = login()
    before = list_hazards(token)["total"]

    monkeypatch.setattr(
        "app.routers.hazard_analysis.analyze_hazard_image",
        lambda *_args: {
            "job_id": "job-without-risks",
            "image_url": "/api/v1/files/hazard-analysis/job-without-risks/annotated.png",
            "original_url": "/api/v1/files/hazard-analysis/job-without-risks/original.png",
            "count": 0,
            "items": [],
            "model": "test-vision-model",
        },
    )

    response = client.post(
        "/api/v1/hazard-analysis/analyze",
        headers={"Authorization": f"Bearer {token}"},
        data={"prompt": "识别全部隐患"},
        files={"image": ("site.png", b"fake-png", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["data"]["created_hazard"] is None
    assert list_hazards(token)["total"] == before
