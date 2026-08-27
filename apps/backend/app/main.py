"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.content.api import router as content_router
from app.core.config import get_settings
from app.identity.api import router as identity_router
from app.student_space.api import router as student_space_router
from app.teacher_space.api import router as teacher_space_router
from app.teacher_space.api.activity_content_router import router as activity_content_router
from app.teacher_space.api.activity_router import router as activity_router
from app.teacher_space.api.assessment_review_router import (
    router as assessment_review_router,
)
from app.teacher_space.api.course_router import router as course_router
from app.teacher_space.api.environment_router import router as environment_router
from app.teacher_space.api.learning_unit_router import router as learning_unit_router
from app.teacher_space.api.section_router import router as section_router

settings = get_settings()
app = FastAPI(title="Education Platform API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(identity_router)
app.include_router(content_router)
app.include_router(student_space_router)
app.include_router(teacher_space_router)
app.include_router(assessment_review_router)
app.include_router(activity_router)
app.include_router(activity_content_router)
app.include_router(course_router)
app.include_router(environment_router)
app.include_router(section_router)
app.include_router(learning_unit_router)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    """Report process health without depending on external services."""
    return {"status": "ok", "environment": settings.app_env}
