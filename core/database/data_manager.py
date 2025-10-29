from sqlalchemy import insert, select
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from core.database.schemas import TemplateConfig
from core.database.db_manager import DatabaseManager
from core.utils.parsing import parse_sensor_data

class DataManager:
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    # async def insert_sensor_data(self, template_config: TemplateConfig, 
    #                            port_name: str, raw_data: str) -> bool:
    #     """Вставляет данные датчика в БД"""
    #     try:
    #         # Получаем движок для этого шаблона
    #         engine = self.db_manager.get_engine(template_config.template_name)
    #         if not engine:
    #             logging.debug(f"TemplateConfig type: {type(template_config)}")
    #             logging.debug(f"TemplateConfig attributes: {dir(template_config)}")
    #             logging.debug(f"TemplateConfig template_name: {getattr(template_config, 'template_name', 'NOT FOUND')}")
        
    #             logging.error(f"Движок для шаблона {template_config.template_name} не найден")
    #             return False
            
    #         # Парсим данные
    #         parsed_data = parse_sensor_data(raw_data, template_config)
    #         if not parsed_data:
    #             logging.warning(f"Не удалось распарсить данные: {raw_data}")
    #             return False
            
    #         # Подключаемся к БД
    #         with engine.connect() as conn:
    #             with conn.begin():
    #                 for sensor_id, sensor_data in parsed_data.items():
    #                     # Находим конфигурацию сенсора
    #                     sensor_config = next(
    #                         (s for s in template_config.sensors if s.sensor_id == sensor_id), 
    #                         None
    #                     )
    #                     if not sensor_config:
    #                         logging.warning(f"Неизвестный сенсор {sensor_id} в шаблоне {template_config.template_name}")
    #                         continue
                        
    #                     # Подготавливаем данные для вставки
    #                     insert_data = {
    #                         'timestamp': '2025-02-01',#datetime.now(),
    #                         'sensor_id': sensor_id,
    #                         'port_name': port_name
    #                     }
                        
    #                     # Добавляем данные полей
    #                     for field_config in sensor_config.fields:
    #                         if field_config.source in sensor_data:
    #                             insert_data[field_config.name] = sensor_data[field_config.source]
    #                         else:
    #                             # Если поле отсутствует в данных, ставим None
    #                             insert_data[field_config.name] = None
                        
    #                     # Вставляем данные
    #                     logging.info(f"db_manager sensor_config {sensor_config}\n insert data: {insert_data}")
    #                     table = self.db_manager.metadata.tables[sensor_config.table_name]
    #                     stmt = insert(table).values(**insert_data)
    #                     conn.execute(stmt)
            
    #         logging.debug(f"Данные с порта {port_name} записаны в БД")
    #         return True
            
    #     except Exception as e:
    #         logging.error(f"Ошибка записи в БД: {e}")
    #         return False
    def insert_sensor_data(self, template_config: TemplateConfig, 
                        port_name: str, raw_data: str) -> bool:
        """Вставляет данные датчика в БД"""
        try:
            # Получаем движок для этого шаблона
            engine = self.db_manager.get_engine(template_config.template_name)
            if not engine:
                logging.error(f"Движок для шаблона {template_config.template_name} не найден")
                return False
            
            # Парсим данные
            parsed_data = parse_sensor_data(raw_data, template_config)
            if not parsed_data:
                logging.warning(f"Не удалось распарсить данные: {raw_data}")
                return False
            
            # Используем синхронное подключение
            with engine.connect() as conn:
                with conn.begin():
                    for sensor_id, sensor_data in parsed_data.items():
                        # Находим конфигурацию сенсора
                        sensor_config = next(
                            (s for s in template_config.sensors if s.sensor_id == sensor_id), 
                            None
                        )
                        if not sensor_config:
                            logging.warning(f"Неизвестный сенсор {sensor_id}")
                            continue
                        
                        # Получаем таблицу через db_manager
                        table = self.db_manager.get_table(sensor_config.table_name)
                        logging.info(f"{sensor_config} \n\n\n {sensor_config.table_name}")
                        # Подготавливаем данные для вставки
                        insert_data = {
                            'timestamp': datetime.now(),
                            'sensor_id': sensor_id,
                            # 'port_name': "COM5"
                        }
                        
                        # Добавляем данные полей
                        for field_config in sensor_config.fields:
                            if field_config.source in sensor_data:
                                insert_data[field_config.name] = sensor_data[field_config.source]
                            else:
                                insert_data[field_config.name] = None
                        
                        # Вставляем данные
                        logging.info(f"Добавление данных в таблицу {sensor_config.table_name}")
                        
                        stmt = insert(table).values(**insert_data)
                        conn.execute(stmt)
            
            logging.debug(f"Данные с порта {port_name} успешно записаны в БД")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка записи в БД: {e}")
            import traceback
            logging.error(f"Трассировка: {traceback.format_exc()}")
            return False

    
    async def get_last_sensor_data(self, template_config: TemplateConfig, 
                                 sensor_id: str, limit: int = 10) -> List[Dict]:
        """Получает последние данные сенсора"""
        try:
            engine = self.db_manager.get_engine(template_config.template_name)
            if not engine:
                return []
            
            sensor_config = next(
                (s for s in template_config.sensors if s.sensor_id == sensor_id), 
                None
            )
            if not sensor_config:
                return []
            
            with engine.connect() as conn:
                table = self.db_manager.metadata.tables[sensor_config.table_name]
                stmt = select(table).order_by(table.c.timestamp.desc()).limit(limit)
                result = conn.execute(stmt)
                
                return [dict(row) for row in result]
                
        except Exception as e:
            logging.error(f"Ошибка чтения из БД: {e}")
            return []