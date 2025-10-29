from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.orm import declared_attr
from config.settings import Base
from core.parser.template_manager import TemplateConfig
from datetime import datetime
from typing import Dict, Type

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now)
    sensor_id = Column(String(50))

def create_dynamic_models(template_config: TemplateConfig) -> Dict[str, Type[BaseModel]]:
    """Динамически создает модели таблиц на основе шаблона"""
    models = {}
    
    for sensor_config in template_config.sensors:
        attributes = {
            '__tablename__': sensor_config.table_name,
            '__table_args__': {'extend_existing': True},
        }
        
        # Добавляем поля датчика
        for field_config in sensor_config.fields:
            # Определяем тип поля SQLAlchemy
            if field_config.db_type.upper() == 'REAL':
                field_type = Float
            elif field_config.db_type.upper() == 'INTEGER':
                field_type = Integer
            elif field_config.db_type.upper() == 'TEXT':
                field_type = Text
            else:
                field_type = String(100)
            
            attributes[field_config.name] = Column(field_type)
        
        # Создаем класс модели
        model_class = type(
            f"{sensor_config.table_name.capitalize()}Model",
            (BaseModel,),
            attributes
        )
        
        models[sensor_config.sensor_id] = model_class
    
    return models