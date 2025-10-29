from typing import List
from starlette import HTTPException

from config.settings import DatabaseFactory
from config.asgi import router

from core.database.schemas import (TemplateCreate, 
                                   TemplateResponse,
                                   DataInsertRequest
                                )

from core.database.dynamic_models import create_dynamic_models
from core.parser.template_manager import TemplateManager, TemplateConfig


template_manager = TemplateManager()
db_factory = DatabaseFactory()

@router.post("/", response_model=TemplateResponse)
async def create_template(template_data: TemplateCreate):
    """Создает новый шаблон из клиента"""
    template_config = TemplateConfig(
        template_name=template_data.template_name,
        description=template_data.description,
        database=template_data.database,
        sensors=template_data.sensors,
        parsing=template_data.parsing or {}
    )
    
    if template_manager.save_template(template_config):
        # Создаем БД и таблицы для этого шаблона
        db_factory.create_engine_for_template(template_config)
        create_dynamic_models(template_config)
        
        # TODO: Создать миграции Alembic
        
        return template_config.dict()
    
    raise HTTPException(500, "Ошибка создания шаблона")

@router.get("/", response_model=List[str])
async def list_templates():
    """Возвращает список доступных шаблонов"""
    return template_manager.list_templates()

@router.get("/{template_name}", response_model=TemplateResponse)
async def get_template(template_name: str):
    """Возвращает конфигурацию шаблона"""
    template = template_manager.load_template(template_name)
    if not template:
        raise HTTPException(404, "Шаблон не найден")
    return template.dict()

@router.post("/{template_name}/data")
async def insert_data(template_name: str, request: DataInsertRequest):
    """Вставляет данные в базу шаблона"""
    template = template_manager.load_template(template_name)
    if not template:
        raise HTTPException(404, "Шаблон не найден")
    
    # TODO: Реализовать вставку данных
    return {"message": "Данные получены", "template": template_name}