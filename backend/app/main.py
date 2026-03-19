from fastapi import FastAPI
from app.routes.violations import router as violations_router
from app.database import engine, Base

app = FastAPI()

app.include_router(violations_router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
def root():
    return {"status": "Backend running"}
