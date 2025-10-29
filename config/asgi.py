from starlette import APIRouter, HTTPException, Depends

router = APIRouter(prefix="/api/v0/templates", tags=["templates"])
router +=APIRouter(...) 

from starlette import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from pathlib import Path
import uvicorn
from core.database.endpoints import router as templates_router

app = FastAPI(title="Arduino Cloud Template Editor")

# CORS для клиентского редактора
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(templates_router)

# Статические файлы редактора
app.mount("/editor", StaticFiles(directory="editor"), name="editor")

@app.get("/")
async def serve_editor():
    """Отдает клиентский редактор"""
    return FileResponse("editor/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)