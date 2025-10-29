import yaml

from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from typing import Dict, List, Any, Optional


BASE_DIR = Path(__file__).parent.parent

DB_PATH = BASE_DIR / "sensors_data.sqlite3"
CONFIG_PATH = BASE_DIR / "configs.yaml"

class DbSettings(BaseModel):
    url: str = f"sqlite+aiosqlite:///{DB_PATH}"
    echo: bool = True

class Settings(BaseSettings):
    api_v1_prefix: str = "/api/v0"

    db: DbSettings = DbSettings()

    # db_echo: bool = True


settings = Settings()

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession,
    async_sessionmaker
    
) 
from sqlalchemy.orm import (
    DeclarativeBase, 
    Mapped, 
    mapped_column, 
    declared_attr,
    sessionmaker
)
from typing import Dict, List, Any, Optional
from core.parser.template_manager import TemplateConfig, TemplateManager

class Base(DeclarativeBase):
    pass

class DatabaseFactory:
    def __init__(self, databases_dir: Path = Path("databases")):
        self.databases_dir = databases_dir
        self.databases_dir.mkdir(exist_ok=True)
        self.engines: Dict[str, any] = {}
        self.session_factories: Dict[str, any] = {}
    
    def get_database_url(self, template_config: TemplateConfig) -> str:
        """Генерирует URL для базы данных"""
        db_name = template_config.database.db_name
        driver = template_config.database.driver
        
        if driver == "sqlite":
            db_path = self.databases_dir / db_name
            return f"sqlite:///{db_path}"
        else:
            # Для других СУБД (PostgreSQL, MySQL)
            return f"{driver}://user:password@localhost/{db_name}"
    
    def create_engine_for_template(self, template_config: TemplateConfig):
        """Создает движок БД для шаблона"""
        template_name = template_config.template_name
        db_url = self.get_database_url(template_config)
        
        # Синхронный движок для миграций
        sync_engine = create_engine(db_url, echo=True)
        
        # Асинхронный движок для операций
        async_db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
        async_engine = create_async_engine(async_db_url, echo=True)
        
        # Фабрики сессий
        sync_session_factory = sessionmaker(sync_engine, expire_on_commit=False)
        async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
        
        self.engines[template_name] = {
            'sync': sync_engine,
            'async': async_engine,
            'sync_session': sync_session_factory,
            'async_session': async_session_factory
        }
        
        return self.engines[template_name]
    
    def get_engine(self, template_name: str):
        """Возвращает движок для шаблона"""
        return self.engines.get(template_name)
    
    def get_async_session(self, template_name: str) -> AsyncSession:
        """Возвращает асинхронную сессию для шаблона"""
        if template_name in self.engines:
            return self.engines[template_name]['async_session']()
        raise ValueError(f"Движок для шаблона {template_name} не найден")

