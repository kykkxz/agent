from __future__ import annotations

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app
from app.seed import seed_if_empty
from app.database import SessionLocal


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()


client = TestClient(app)


def login(username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    return payload["data"]["access_token"]


def test_login_and_me() -> None:
    token = login("admin", "Admin@123456")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["data"]["role"] == "Admin"


def test_login_failed() -> None:
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "bad"})
    assert response.status_code == 401
    assert response.json()["code"] == 40101


def test_hazard_workflow() -> None:
    admin = login("admin", "Admin@123456")
    worker = login("worker", "Worker@123456")
    created = client.post(
        "/api/v1/hazards/json",
        headers={"Authorization": f"Bearer {worker}"},
        json={
            "title": "基坑临边无防护",
            "description": "基坑东侧临边未设置防护栏杆，存在坠落风险。",
            "level": "critical",
            "category": "edge_protection",
            "location": "K1+100",
            "project": "成绵高速扩容项目",
            "occurred_at": "2026-08-13T09:00:00+08:00",
        },
    )
    assert created.json()["code"] == 0
    hazard_id = created.json()["data"]["hazard_id"]

    assigned = client.post(
        f"/api/v1/hazards/{hazard_id}/assign",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "assignee_id": "U003",
            "requirements": "立即设置防护并在两日内验收",
            "deadline": "2026-08-16T18:00:00+08:00",
            "priority": "urgent",
        },
    )
    assert assigned.json()["data"]["status"] == "processing"

    too_short = client.post(
        f"/api/v1/hazards/{hazard_id}/rectify-json",
        headers={"Authorization": f"Bearer {worker}"},
        json={"measures": "已处理"},
    )
    assert too_short.json()["code"] == 40008

    rectified = client.post(
        f"/api/v1/hazards/{hazard_id}/rectify-json",
        headers={"Authorization": f"Bearer {worker}"},
        json={"measures": "已设置临边防护栏杆并悬挂警示标志，现场复查合格。"},
    )
    assert rectified.json()["data"]["status"] == "pending_review"

    reviewed = client.post(
        f"/api/v1/hazards/{hazard_id}/review",
        headers={"Authorization": f"Bearer {admin}"},
        json={"result": "approved", "comment": "整改到位"},
    )
    assert reviewed.json()["data"]["status"] == "closed"


def test_exam_auto_grade() -> None:
    worker = login("worker", "Worker@123456")
    exams = client.get("/api/v1/exam/my-exams", headers={"Authorization": f"Bearer {worker}"}).json()["data"]
    paper_id = exams[0]["paper_id"]
    started = client.post(
        f"/api/v1/exam/my-exams/{paper_id}/start",
        headers={"Authorization": f"Bearer {worker}"},
    ).json()["data"]
    answers = {}
    for question in started["questions"]:
        if question["type"] == "single_choice":
            answers[str(question["question_id"])] = "A"
        elif question["type"] == "true_false":
            answers[str(question["question_id"])] = "正确"
        elif question["type"] == "multi_choice":
            answers[str(question["question_id"])] = "ABC"
        else:
            answers[str(question["question_id"])] = "总承包单位"
    submitted = client.post(
        f"/api/v1/exam/attempts/{started['attempt_id']}/submit",
        headers={"Authorization": f"Bearer {worker}"},
        json={"answers": answers},
    )
    assert submitted.json()["code"] == 0
    assert submitted.json()["data"]["score"] is not None


def test_exam_draft_can_be_reopened_and_updated() -> None:
    admin = login("admin", "Admin@123456")
    headers = {"Authorization": f"Bearer {admin}"}
    question = client.get("/api/v1/exam/questions", headers=headers).json()["data"]["items"][0]
    created = client.post(
        "/api/v1/exam/papers",
        headers=headers,
        json={
            "title": "待继续编辑的草稿",
            "description": "依据：高处作业",
            "duration_minutes": 30,
            "pass_score": 60,
            "question_ids": [question["question_id"]],
        },
    ).json()["data"]
    updated = client.put(
        f"/api/v1/exam/papers/{created['paper_id']}",
        headers=headers,
        json={
            "title": "已恢复编辑的草稿",
            "description": "依据：高处作业、安全生产法",
            "duration_minutes": 45,
            "pass_score": 70,
            "question_ids": [question["question_id"]],
        },
    )
    assert updated.status_code == 200
    detail = client.get(f"/api/v1/exam/papers/{created['paper_id']}", headers=headers)
    assert detail.json()["data"]["title"] == "已恢复编辑的草稿"
    assert detail.json()["data"]["duration_minutes"] == 45


def test_exam_generation_preserves_requested_question_types() -> None:
    admin = login("admin", "Admin@123456")
    response = client.post(
        "/api/v1/exam/ai/generate",
        headers={"Authorization": f"Bearer {admin}"},
        json={
            "knowledge_points": ["高处作业"],
            "types": ["multi_choice", "fill_blank", "essay"],
            "count": 3,
            "difficulty": "mixed",
        },
    )
    assert response.status_code == 200
    assert [item["type"] for item in response.json()["data"]] == [
        "multi_choice",
        "fill_blank",
        "essay",
    ]


def test_ai_sync_and_knowledge() -> None:
    token = login("safety", "Safety@123456")
    response = client.post(
        "/api/v1/ai/chat/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "安全生产法对从业人员的权利有哪些规定？"},
    )
    assert response.json()["code"] == 0
    assert "[1]" in response.json()["data"]["content"]
    assert response.json()["data"]["citations"]
    capabilities = client.get(
        "/api/v1/ai/capabilities", headers={"Authorization": f"Bearer {token}"}
    )
    assert capabilities.json()["data"]["agent"] == "LangChain create_agent"
    overview = client.get("/api/v1/knowledge/overview", headers={"Authorization": f"Bearer {token}"})
    assert overview.json()["code"] == 0


def test_hazard_analysis_contract(monkeypatch) -> None:
    token = login("safety", "Safety@123456")

    def fake_analysis(_content: bytes, suffix: str, prompt: str) -> dict:
        assert suffix == ".png"
        assert "隐患" in prompt
        return {
            "job_id": "test-job",
            "image_url": "/api/v1/files/hazard-analysis/test-job/annotated.png",
            "original_url": "/api/v1/files/hazard-analysis/test-job/original.png",
            "count": 1,
            "items": [{"label": "临边防护缺失", "risk": "高"}],
            "model": "test-vision-model",
        }

    monkeypatch.setattr(
        "app.routers.hazard_analysis.analyze_hazard_image", fake_analysis
    )
    response = client.post(
        "/api/v1/hazard-analysis/analyze",
        headers={"Authorization": f"Bearer {token}"},
        data={"prompt": "识别全部隐患"},
        files={"image": ("site.png", b"fake-png", "image/png")},
    )
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 1
