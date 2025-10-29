import yaml
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import logging
from config.settings import BASE_DIR

class SensorFieldConfig(BaseModel):
    name: str
    source: str
    db_type: str
    unit: Optional[str] = None
    description: Optional[str] = None

class SensorConfig(BaseModel):
    sensor_id: str
    table_name: str
    fields: List[SensorFieldConfig]

class DatabaseConfig(BaseModel):
    db_name: str
    driver: str = "sqlite"

class ParsingConfig(BaseModel):
    delimiter: str = ";"
    key_value_separator: str = ":"

class TemplateConfig(BaseModel):
    template_name: str
    template_version: str = "1.0"
    description: Optional[str] = None
    database: DatabaseConfig
    sensors: List[SensorConfig]
    parsing: ParsingConfig = ParsingConfig()

class TemplateManager:
    def __init__(self, templates_dir: Path = BASE_DIR / "templates"):
        self.templates_dir = templates_dir
        self.templates_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, TemplateConfig] = {}
        
    # def load_template(self, template_name: str) -> Optional[TemplateConfig]:
    #     """Загружает шаблон из YAML файла"""
    #     template_path = self.templates_dir / f"{template_name}.yaml"
    #     logging.info(f"template_manager path {template_path}")
    #     try:
    #         if template_path.exists():
    #             with open(template_path, 'r', encoding='utf-8') as f:
    #                 template_data = yaml.safe_load(f)
    #                 logging.info(f"template_manager data {template_data}")
                    
    #                 return TemplateConfig(**template_data)
    #     except Exception as e:
    #         logging.error(f"Ошибка загрузки шаблона {template_name}: {e}")
        
    #     return None
    def load_template(self, template_name: str) -> Optional[TemplateConfig]:
        """Загружает шаблон из YAML файла"""
        # Если хотите всегда использовать indoor_sensor.yaml
        template_path = self.templates_dir / "indoor_sensor.yaml"
        
        # Или сделать маппинг имен
        template_mapping = {
            "weather_station": "indoor_sensor.yaml",
            # другие маппинги...
        }
        filename = template_mapping.get(template_name, f"{template_name}.yaml")
        template_path = self.templates_dir / filename
        
        logging.info(f"template_manager path {template_path}")
        try:
            if template_path.exists():
                with open(template_path, 'r', encoding='utf-8') as f:
                    template_data = yaml.safe_load(f)
                    logging.info(f"template_manager data {template_data}")
                    return TemplateConfig(**template_data)
        except Exception as e:
            logging.error(f"Ошибка загрузки шаблона {template_name}: {e}")
        
        return None
    
    def save_template(self, template_config: TemplateConfig) -> bool:
        """Сохраняет шаблон в YAML файл"""
        try:
            template_path = self.templates_dir / f"{template_config.template_name}.yaml"
            
            with open(template_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_config.dict(), f, allow_unicode=True, sort_keys=False)
            
            logging.info(f"Шаблон {template_config.template_name} сохранен")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка сохранения шаблона: {e}")
            return False
    
    def list_templates(self) -> List[str]:
        """Возвращает список доступных шаблонов"""
        return [f.stem for f in self.templates_dir.glob("*.yaml")]
    
    def delete_template(self, template_name: str) -> bool:
        """Удаляет шаблон"""
        try:
            template_path = self.templates_dir / f"{template_name}.yaml"
            if template_path.exists():
                template_path.unlink()
                return True
        except Exception as e:
            logging.error(f"Ошибка удаления шаблона {template_name}: {e}")
        return False