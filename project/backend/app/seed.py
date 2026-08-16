from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import QuickQuestion
from app.models.exam import ExamPaper, Question
from app.models.hazard import Hazard, HazardLog
from app.models.notification import Notification
from app.models.user import User
from app.security import hash_password


def seed_if_empty(db: Session) -> None:
    if db.scalar(select(User.id).limit(1)):
        return

    users = [
        User(
            id="U001",
            username="admin",
            name="系统管理员",
            password_hash=hash_password("Admin@123456"),
            role="Admin",
            department="安全生产部",
            project="集团本部",
            phone="13800000001",
        ),
        User(
            id="U002",
            username="safety",
            name="李安全",
            password_hash=hash_password("Safety@123456"),
            role="SafetyOfficer",
            department="安全生产部",
            project="成绵高速扩容项目",
            phone="13800000002",
        ),
        User(
            id="U003",
            username="worker",
            name="王施工",
            password_hash=hash_password("Worker@123456"),
            role="Employee",
            department="一分部",
            project="成绵高速扩容项目",
            phone="13800000003",
        ),
        User(
            id="U004",
            username="zhangsan",
            name="张三",
            password_hash=hash_password("Zhang@123456"),
            role="Employee",
            department="二分部",
            project="成绵高速扩容项目",
            phone="13800000004",
        ),
    ]
    db.add_all(users)
    # Questions, hazards, and exam papers reference these fixed user IDs.
    # Flush first because the ORM models deliberately do not declare relations.
    db.flush()

    now = datetime.now(UTC)
    hazards = [
        Hazard(
            id="HD-20260812-0001",
            title="3号桥墩临边防护缺失",
            description="桥墩施工区域临边护栏缺失约5米，作业面距地面超过8米，存在高处坠落风险。",
            level="major",
            category="edge_protection",
            location="K12+350 3号桥墩",
            location_coords="104.12345,30.67890",
            project="成绵高速扩容项目",
            occurred_at="2026-08-12T09:30:00+08:00",
            status="processing",
            reporter_id="U004",
            assignee_id="U003",
            assignment_json=json.dumps(
                {
                    "assignee": {"id": "U003", "name": "王施工"},
                    "requirements": "立即设置临时防护，48小时内安装正式护栏",
                    "deadline": "2026-08-15T18:00:00+08:00",
                    "priority": "urgent",
                },
                ensure_ascii=False,
            ),
        ),
        Hazard(
            id="HD-20260811-0002",
            title="配电箱未设置漏电保护",
            description="临电二级箱未见漏电保护器，接地线松动。",
            level="critical",
            category="temp_electricity",
            location="拌合站东侧临电箱",
            project="成绵高速扩容项目",
            occurred_at="2026-08-11T14:10:00+08:00",
            status="pending",
            reporter_id="U003",
        ),
        Hazard(
            id="HD-20260810-0003",
            title="脚手架连墙件间距超标",
            description="现场抽查发现连墙件竖向间距超过规范要求，局部缺少扫地杆。",
            level="major",
            category="height_work",
            location="K8+120 盖梁作业区",
            project="成绵高速扩容项目",
            occurred_at="2026-08-10T08:40:00+08:00",
            status="pending_review",
            reporter_id="U004",
            assignee_id="U003",
            rectification_json=json.dumps(
                {
                    "measures": "已按规范补齐连墙件并恢复扫地杆，现场复查合格。",
                    "completed_at": "2026-08-12T16:00:00+08:00",
                    "images_after": [],
                },
                ensure_ascii=False,
            ),
        ),
        Hazard(
            id="HD-20260808-0004",
            title="灭火器过期未更换",
            description="项目部会议室灭火器压力指针进入红区。",
            level="minor",
            category="fire_safety",
            location="项目部二楼会议室",
            project="成绵高速扩容项目",
            occurred_at="2026-08-08T11:00:00+08:00",
            status="closed",
            reporter_id="U002",
            assignee_id="U003",
            reviewer_id="U002",
        ),
    ]
    db.add_all(hazards)
    db.add_all(
        [
            HazardLog(hazard_id="HD-20260812-0001", node="上报", operator_id="U004", note="隐患首次上报"),
            HazardLog(hazard_id="HD-20260812-0001", node="派单", operator_id="U002", note="指派王施工处理"),
            HazardLog(hazard_id="HD-20260811-0002", node="上报", operator_id="U003", note="重大临电隐患"),
            HazardLog(hazard_id="HD-20260810-0003", node="上报", operator_id="U004", note="脚手架专项检查"),
            HazardLog(hazard_id="HD-20260810-0003", node="整改", operator_id="U003", note="已完成整改待验收"),
            HazardLog(hazard_id="HD-20260808-0004", node="上报", operator_id="U002", note="日常巡查"),
            HazardLog(hazard_id="HD-20260808-0004", node="验收", operator_id="U002", note="已更换合格灭火器"),
        ]
    )

    questions = [
        Question(
            type="single_choice",
            content="根据《安全生产法》，从业人员有权对本单位安全生产工作中存在的问题提出批评、（ ）、控告。",
            options_json=json.dumps({"A": "检举", "B": "举报", "C": "投诉", "D": "建议"}, ensure_ascii=False),
            answer="A",
            explanation="《安全生产法》规定从业人员有权对本单位安全生产工作中存在的问题提出批评、检举、控告。",
            score=2,
            difficulty="medium",
            category="安全生产法",
            tags_json='["安全生产法","从业人员权利"]',
            created_by="U001",
        ),
        Question(
            type="true_false",
            content="生产经营单位的主要负责人对本单位的安全生产工作全面负责。",
            options_json=json.dumps({"A": "正确", "B": "错误"}, ensure_ascii=False),
            answer="正确",
            explanation="《安全生产法》明确规定主要负责人对本单位安全生产工作全面负责。",
            score=2,
            difficulty="easy",
            category="安全生产法",
            tags_json='["主要负责人"]',
            created_by="U001",
        ),
        Question(
            type="multi_choice",
            content="高处作业应采取的防护措施包括（ ）。",
            options_json=json.dumps(
                {"A": "佩戴安全带", "B": "设置防护栏杆", "C": "使用安全网", "D": "酒后作业提高反应"},
                ensure_ascii=False,
            ),
            answer="ABC",
            explanation="高处作业必须落实个体防护和临边洞口防护，严禁酒后作业。",
            score=3,
            difficulty="medium",
            category="高处作业",
            tags_json='["高处作业"]',
            created_by="U001",
        ),
        Question(
            type="single_choice",
            content="临时用电实行（ ）配电系统。",
            options_json=json.dumps(
                {"A": "二级配电、一级保护", "B": "三级配电、两级保护", "C": "一级配电", "D": "无要求"},
                ensure_ascii=False,
            ),
            answer="B",
            explanation="施工现场临时用电应采用三级配电、两级漏电保护系统。",
            score=2,
            difficulty="medium",
            category="临时用电",
            tags_json='["临电"]',
            created_by="U001",
        ),
        Question(
            type="fill_blank",
            content="建设工程实行施工总承包的，由（ ）对施工现场的安全生产负总责。",
            options_json="{}",
            answer="总承包单位",
            explanation="《建设工程安全生产管理条例》规定总承包单位对施工现场安全生产负总责。",
            score=2,
            difficulty="hard",
            category="建设工程条例",
            tags_json='["总承包"]',
            created_by="U001",
        ),
        Question(
            type="essay",
            content="简述发现重大隐患后应立即采取的处置步骤。",
            options_json="{}",
            answer="立即停工撤离、设置警戒、上报安全员、落实整改并验收闭环。",
            explanation="按隐患闭环流程执行。",
            score=5,
            difficulty="medium",
            category="隐患管理",
            tags_json='["隐患闭环"]',
            created_by="U001",
        ),
    ]
    db.add_all(questions)
    db.flush()

    paper = ExamPaper(
        title="2026年第三季度全员安全考试",
        description="覆盖安全生产法、高处作业、临电与隐患闭环。",
        duration_minutes=45,
        pass_score=60,
        question_ids_json=json.dumps([q.id for q in questions]),
        start_at=(now - timedelta(days=1)).isoformat(),
        end_at=(now + timedelta(days=14)).isoformat(),
        status="published",
        created_by="U001",
    )
    db.add(paper)

    db.add_all(
        [
            QuickQuestion(category="法规类", question="安全生产法对从业人员的权利有哪些规定？", is_hot=1),
            QuickQuestion(category="作业类", question="高处作业安全带应如何正确使用？", is_hot=1),
            QuickQuestion(category="隐患类", question="重大隐患整改期限有什么要求？", is_hot=0),
            QuickQuestion(category="应急类", question="施工现场火灾初期应如何处置？", is_hot=0),
        ]
    )
    db.add(
        Notification(
            user_id="U003",
            title="您有一条待整改隐患",
            content="3号桥墩临边防护缺失已派发给您，请在截止日期前完成整改。",
            type="hazard",
            related_id="HD-20260812-0001",
        )
    )
    db.commit()
