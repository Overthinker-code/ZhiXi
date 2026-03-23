from fastapi import APIRouter

from app.api.routes.ud import router as ud_router
from app.api.routes.teachers import router as teachers_router
from app.api.routes.courses import router as courses_router
from app.api.routes.tc import router as tc_router
from app.api.routes.course_plans import router as course_plans_router
from app.api.routes.students import router as students_router
from app.api.routes.videos import router as videos_router

router = APIRouter()

# 添加所有子路由
router.include_router(ud_router, prefix="/ud", tags=["university-department"])
router.include_router(teachers_router, prefix="/teachers", tags=["teachers"])
router.include_router(courses_router, prefix="/courses", tags=["courses"])
router.include_router(tc_router, prefix="/tc", tags=["teaching-classes"])
router.include_router(
    course_plans_router, prefix="/course-plans", tags=["course-plans"]
)
router.include_router(students_router, prefix="/students", tags=["students"])
router.include_router(videos_router, prefix="/videos", tags=["videos"])
