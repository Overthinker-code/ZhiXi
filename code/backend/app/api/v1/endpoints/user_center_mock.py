from typing import Any

from fastapi import APIRouter, File, UploadFile

router = APIRouter()


@router.post("/api/user/my-project/list")
def my_project_list():
    return [
        {
            "id": 1,
            "name": "Database Fundamentals Lab",
            "description": "Core SQL practice, schema design, and query tuning.",
            "peopleNumber": 126,
            "contributors": [
                {
                    "name": "Alice",
                    "email": "alice@example.com",
                    "avatar": "https://i.pravatar.cc/100?img=1",
                },
                {
                    "name": "Bob",
                    "email": "bob@example.com",
                    "avatar": "https://i.pravatar.cc/100?img=2",
                },
            ],
        },
        {
            "id": 2,
            "name": "Transactions and Concurrency",
            "description": "Isolation level experiments and deadlock analysis.",
            "peopleNumber": 98,
            "contributors": [
                {
                    "name": "Carol",
                    "email": "carol@example.com",
                    "avatar": "https://i.pravatar.cc/100?img=3",
                }
            ],
        },
    ]


@router.post("/api/user/my-team/list")
def my_team_list():
    return [
        {
            "id": 1,
            "avatar": "https://i.pravatar.cc/100?img=5",
            "name": "DB Teaching Team A",
            "peopleNumber": 12,
        },
        {
            "id": 2,
            "avatar": "https://i.pravatar.cc/100?img=6",
            "name": "SQL Lab Mentors",
            "peopleNumber": 8,
        },
        {
            "id": 3,
            "avatar": "https://i.pravatar.cc/100?img=7",
            "name": "Curriculum Design Group",
            "peopleNumber": 6,
        },
    ]


@router.post("/api/user/latest-activity")
def latest_activity():
    return [
        {
            "id": 1,
            "title": "New assignment published",
            "description": "Window functions practice has been assigned to Class DB-2026.",
            "avatar": "https://i.pravatar.cc/100?img=8",
        },
        {
            "id": 2,
            "title": "Submission trend updated",
            "description": "This week's SQL submissions increased by 12%.",
            "avatar": "https://i.pravatar.cc/100?img=9",
        },
    ]


@router.post("/api/user/save-info")
def save_info(payload: dict[str, Any]):
    return {"ok": True, "saved": payload}


@router.post("/api/user/certification")
def user_certification():
    return {
        "enterpriseInfo": {
            "accountType": "Enterprise Account",
            "status": 1,
            "time": "2025-09-18 14:30:12",
            "legalPerson": "Li **",
            "certificateType": "ID Card",
            "authenticationNumber": "130************123",
            "enterpriseName": "Database Teaching Center",
            "enterpriseCertificateType": "Business License",
            "organizationCode": "7*******9",
        },
        "record": [
            {
                "certificationType": 1,
                "certificationContent": "Enterprise real-name verification completed.",
                "status": 1,
                "time": "2025-09-18 14:30:12",
            },
            {
                "certificationType": 1,
                "certificationContent": "Enterprise profile update submitted.",
                "status": 0,
                "time": "2025-10-06 09:18:40",
            },
        ],
    }


@router.post("/api/user/upload")
async def upload_user_avatar(file: UploadFile = File(...)):
    filename = file.filename or "avatar.png"
    return {"ok": True, "url": f"https://example.com/uploads/{filename}"}
