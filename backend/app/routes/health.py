from fastapi import APIRouter

health_router = APIRouter(prefix="/api")


@health_router.get("/health")
def read_health() -> dict[str, str]:
    return {"status": "ok"}
