from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class SensorFieldCreate(BaseModel):
    name: str
    source: str
    db_type: str
    unit: Optional[str] = None
    description: Optional[str] = None

class SensorCreate(BaseModel):
    sensor_id: str
    table_name: str
    fields: List[SensorFieldCreate]

class TemplateCreate(BaseModel):
    template_name: str
    description: Optional[str] = None
    database: Dict[str, Any]
    sensors: List[SensorCreate]
    parsing: Optional[Dict[str, Any]] = None

class TemplateResponse(BaseModel):
    template_name: str
    description: Optional[str] = None
    database: Dict[str, Any]
    sensors: List[Dict[str, Any]]
    parsing: Dict[str, Any]

class DataInsertRequest(BaseModel):
    template_name: str
    sensor_id: str
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None

    # Дополнительные схемы для API
class TemplateListResponse(BaseModel):
    templates: List[str]
    count: int

class MigrationInfo(BaseModel):
    template_name: str
    last_migration: Optional[str] = None
    status: str  # 'current', 'outdated', 'new'

class PortTemplateAssignment(BaseModel):
    port_name: str
    template_name: str
    baudrate: int = 115200
    status: str  # 'active', 'inactive', 'error'

class SensorFieldConfig(BaseModel):
    name: str
    source: str
    db_type: str = "REAL"  # Значение по умолчанию
    unit: Optional[str] = None
    description: Optional[str] = None

class SensorConfig(BaseModel):
    sensor_id: str
    table_name: str
    fields: List[SensorFieldConfig]

class DatabaseConfig(BaseModel):
    db_name: str = "sensors.db"  # Значение по умолчанию
    driver: str = "sqlite"

class ParsingConfig(BaseModel):
    delimiter: str = ";"
    key_value_separator: str = ":"

class TemplateConfig(BaseModel):
    template_name: str
    template_version: str = "1.0"
    description: Optional[str] = None
    database: DatabaseConfig = DatabaseConfig()
    sensors: List[SensorConfig]
    parsing: ParsingConfig = ParsingConfig()