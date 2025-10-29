from typing import Dict, Any, Optional
from core.parser.template_manager import TemplateManager, TemplateConfig
import logging

def parse_sensor_data(data_string: str, template: TemplateConfig) -> Optional[Dict[str, Any]]:
    """Парсит данные датчиков согласно шаблону"""
    if not data_string or not template:
        return None
    
    try:
        result = {}
        delimiter = template.parsing.delimiter
        key_value_sep = template.parsing.key_value_separator
        
        # Убираем лишние символы
        data_string = data_string.strip().replace('\r', '').replace('\n', '')
        parts = [part.strip() for part in data_string.split(delimiter) if part.strip()]
        
        current_sensor = None
        
        for part in parts:
            if key_value_sep in part:
                key, value = part.split(key_value_sep, 1)
                key, value = key.strip(), value.strip()
                
                if key == "Sensor":
                    current_sensor = value
                    result[current_sensor] = {}
                elif current_sensor and key:
                    # Конвертируем числовые значения
                    try:
                        if '.' in value:
                            numeric_value = float(value)
                        else:
                            numeric_value = int(value)
                        result[current_sensor][key] = numeric_value
                    except (ValueError, TypeError):
                        result[current_sensor][key] = value
        
        return result if result else None
        
    except Exception as e:
        logging.error(f"Ошибка парсинга данных '{data_string}': {e}")
        return None