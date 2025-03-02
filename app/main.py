from fastapi import FastAPI

from app.auth.routes import auth_router
from contextlib import asynccontextmanager
from app.db.session import create_db_and_tables
from app.object_detection.routes import yolo_router
from app.auth.services import AdminService
from app.db.session import AsyncSessionLocal
from app.auth.schemas import AdminCreateModel
from app.middleware import register_middleware

version = "v1"
description = """
A REST API for a object detection web services.

This REST API is able to:
- Signup, Login, Forget password/Reset password
- Detection of colony in microbiology laboratory.
- .,
"""
version_prefix = f"/api/{version}"

admin_services = AdminService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    async with AsyncSessionLocal() as session:
        admin_data = AdminCreateModel()
        await admin_services.create_admin(admin_data=admin_data, session=session)
    yield


app = FastAPI(
    title="Detection of colony",
    description=description,
    version=version,
    license_info={"name": "Name xxxyyy", "url": "https://opensource.org/licence/mit"},
    contact={
        "name": "Hao Nguyen",
        "url": "https://github.com/haontuhcmut",
        "email": "nmhao.sdh232@hcmut.edu.vn",
    },
    terms_of_service="https://example.com/tos",
    openapi_url=f"{version_prefix}/openapi.json",
    docs_url=f"{version_prefix}/docs",
    redoc_url=f"{version_prefix}/redoc",
    lifespan=lifespan,
)

register_middleware(app)

app.include_router(auth_router, prefix=f"{version_prefix}/auth", tags=["auth"])
app.include_router(
    yolo_router, prefix=f"{version_prefix}/obj", tags=["object detection"]
)
