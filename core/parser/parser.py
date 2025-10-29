import yaml, logging

def load_parsing_template(template_path="configs.yaml"):
    """
    Загружает шаблон парсинга из YAML файла
    """
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            return config.get('parsing_template', {})
    except FileNotFoundError:
        logging.error(f"Файл шаблона {template_path} не найден")
        return {}
    except yaml.YAMLError as e:
        logging.error(f"Ошибка парсинга YAML: {e}")
        return {}

def parse_sensor_data(data_string, template):
    """
    Парсит данные датчиков согласно YAML-шаблону
    """
    if not template or not data_string:
        return {}
    
    try:
        result = {}
        delimiter = template.get('delimiter', ';')
        key_value_sep = template.get('key_value_separator', ':')
        
        # Разбиваем строку на части
        parts = [part.strip() for part in data_string.split(delimiter) if part.strip()]
        
        current_sensor = None
        
        for part in parts:
            if key_value_sep in part:
                key, value = part.split(key_value_sep, 1)
                key = key.strip()
                value = value.strip()
                
                # Определяем к какому датчику относятся данные
                if key == "Sensor":
                    current_sensor = value
                    result[current_sensor] = {}
                elif current_sensor and key:
                    # Сохраняем данные для текущего датчика
                    result[current_sensor][key] = value
        
        return result
        
    except Exception as e:
        logging.error(f"Ошибка парсинга данных: {e}")
        return {}