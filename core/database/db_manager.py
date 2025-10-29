from sqlalchemy import create_engine, Table, Column, MetaData, inspect
from sqlalchemy import Integer, String, Float, DateTime, Boolean
from pathlib import Path
from typing import Dict, Optional, List
import logging
import os
from core.parser.template_manager import TemplateManager, TemplateConfig
from starlette.responses import JSONResponse

from sqlalchemy import create_engine, MetaData, Table, select, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime


class DatabaseManager:
    def __init__(self, databases_dir: Path = Path("databases")):
        self.databases_dir = databases_dir
        self.databases_dir.mkdir(exist_ok=True)
        self.metadata = MetaData()
        self.engines: Dict[str, any] = {}  # Храним движки для каждой БД
        self._load_existing_databases()
    
    def _load_existing_databases(self):
        """Загружает все существующие базы данных из папки databases"""
        try:
            # Ищем все .db файлы в папке databases
            db_files = list(self.databases_dir.glob("*.db"))
            
            for db_file in db_files:
                # Имя базы данных без расширения
                db_name = db_file.stem
                template_name = db_name  # Предполагаем, что имя файла = имя шаблона
                
                # Создаем движок для существующей БД
                engine = create_engine(f"sqlite:///{db_file}")
                self.engines[template_name] = engine
                
                # Отражаем метаданные из БД
                self.metadata.reflect(bind=engine)
                
                logging.info(f"Загружена существующая БД: {template_name}")
                
        except Exception as e:
            logging.error(f"Ошибка загрузки существующих БД: {e}")
    
    def create_database(self, template_config: TemplateConfig) -> bool:
        """Создает базу данных и таблицы по шаблону"""
        try:
            db_path = self.databases_dir / template_config.database.db_name
            engine = create_engine(f"sqlite:///{db_path}")
            
            # Создаем таблицы для каждого датчика
            for sensor_config in template_config.sensors:
                self._create_sensor_table(sensor_config, template_config)
            
            # Создаем все таблицы
            self.metadata.create_all(engine)
            
            # Сохраняем движок
            self.engines[template_config.template_name] = engine
            
            logging.info(f"База данных {template_config.database.db_name} создана")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка создания БД: {e}")
            return False
    
    def create_engine(self, template_config: TemplateConfig):
        """Создает и возвращает движок для базы данных"""
        try:
            db_path = self.databases_dir / template_config.database.db_name
            engine = create_engine(f"sqlite:///{db_path}")
            self.engines[template_config.template_name] = engine
            return engine
        except Exception as e:
            logging.error(f"Ошибка создания движка: {e}")
            return None
    
    def get_engine(self, template_name: str):
        """Возвращает движок для шаблона"""
        if template_name in self.engines:
            return self.engines[template_name]
        
        # Если движка нет, пытаемся создать из существующей БД
        db_path = self.databases_dir / f"{template_name}.db"
        if db_path.exists():
            try:
                engine = create_engine(f"sqlite:///{db_path}")
                self.engines[template_name] = engine
                # Отражаем метаданные
                self.metadata.reflect(bind=engine)
                return engine
            except Exception as e:
                logging.error(f"Ошибка загрузки движка для {template_name}: {e}")
        
        # Если БД не существует, пытаемся создать через шаблон
        template_manager = TemplateManager()
        template = template_manager.load_template(template_name)
        if template:
            return self.create_engine(template)
        
        return None
    
    def _create_sensor_table(self, sensor_config, template_config):
        """Создает таблицу для датчика"""
        columns = [
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('timestamp', DateTime),
            Column('sensor_id', String(50)),
            Column('port_name', String(20))
        ]
        
        # Добавляем специфичные поля датчика
        for field_config in sensor_config.fields:
            column_type = self._get_column_type(field_config.db_type)
            columns.append(Column(field_config.name, column_type))
        
        # Создаем таблицу
        Table(
            sensor_config.table_name,
            self.metadata,
            *columns
        )
    
    def _get_column_type(self, db_type: str):
        """Возвращает SQLAlchemy тип колонки"""
        type_mapping = {
            'INTEGER': Integer,
            'REAL': Float,
            'TEXT': String(255),
            'STRING': String(255),
            'BOOLEAN': Boolean,
            'DATETIME': DateTime,
            'FLOAT': Float
        }
        return type_mapping.get(db_type.upper(), String(255))
    
    def get_table(self, table_name: str):
        """Возвращает таблицу по имени"""
        if table_name in self.metadata.tables:
            return self.metadata.tables[table_name]
        
        # Если таблицы нет, пытаемся отразить её из БД
        try:
            for engine in self.engines.values():
                self.metadata.reflect(bind=engine)
                if table_name in self.metadata.tables:
                    return self.metadata.tables[table_name]
        except Exception as e:
            logging.error(f"Ошибка отражения таблицы {table_name}: {e}")
        
        return None

    def get_all_tables(self, template_name: str) -> List[str]:
        """Возвращает список всех таблиц в базе данных шаблона"""
        try:
            engine = self.get_engine(template_name)
            if not engine:
                return []
            
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            return tables
            
        except Exception as e:
            logging.error(f"Ошибка получения списка таблиц для {template_name}: {e}")
            return []

    def get_table_info(self, template_name: str, table_name: str) -> Dict:
        """Возвращает информацию о таблице (колонки и их типы)"""
        try:
            engine = self.get_engine(template_name)
            if not engine:
                return {}
            
            inspector = inspect(engine)
            
            # Проверяем существование таблицы
            if table_name not in inspector.get_table_names():
                return {}
            
            columns = inspector.get_columns(table_name)
            column_info = []
            for column in columns:
                column_info.append({
                    'name': column['name'],
                    'type': str(column['type']),
                    'nullable': column['nullable'],
                    'primary_key': column.get('primary_key', False)
                })
            
            indexes = inspector.get_indexes(table_name)
            
            return {
                'table_name': table_name,
                'columns': column_info,
                'indexes': indexes
            }
            
        except Exception as e:
            logging.error(f"Ошибка получения информации о таблице {table_name}: {e}")
            return {}

    def get_all_databases_info(self) -> Dict[str, List[str]]:
        """Возвращает информацию о всех базах данных и их таблицах"""
        databases_info = {}
        
        # Ищем все .db файлы в папке
        db_files = list(self.databases_dir.glob("*.db"))
        
        for db_file in db_files:
            template_name = db_file.stem
            try:
                tables = self.get_all_tables(template_name)
                databases_info[template_name] = tables
            except Exception as e:
                logging.error(f"Ошибка получения информации о БД {template_name}: {e}")
                databases_info[template_name] = []
        
        return databases_info

    def database_exists(self, template_name: str) -> bool:
        """Проверяет существует ли база данных для шаблона"""
        db_path = self.databases_dir / f"{template_name}.db"
        return db_path.exists()

    def get_database_stats(self, template_name: str) -> Dict:
        """Возвращает статистику по базе данных"""
        try:
            engine = self.get_engine(template_name)
            if not engine:
                return {}
            
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            stats = {
                'template_name': template_name,
                'table_count': len(tables),
                'tables': []
            }
            
            for table_name in tables:
                columns = inspector.get_columns(table_name)
                stats['tables'].append({
                    'name': table_name,
                    'column_count': len(columns)
                })
            
            return stats
            
        except Exception as e:
            logging.error(f"Ошибка получения статистики БД {template_name}: {e}")
            return {}
        
    def get_all_table_data(self, template_name: str, table_name: str) -> List[Dict]:
        """Возвращает все данные из таблицы с датами"""
        try:
            logging.info(f"Поиск данных: template={template_name}, table={table_name}")
            
            engine = self.get_engine(template_name)
            if not engine:
                logging.warning(f"Движок для шаблона {template_name} не найден")
                return []
            
            inspector = inspect(engine)
            
            # Проверяем существование таблицы
            tables = inspector.get_table_names()
            logging.info(f"Доступные таблицы: {tables}")
            
            if table_name not in tables:
                logging.warning(f"Таблица {table_name} не найдена")
                return []
            
            # Получаем все данные из таблицы
            with engine.connect() as conn:
                result = conn.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC")
                rows = result.fetchall()
                
                logging.info(f"Найдено {len(rows)} записей")
                
                # Преобразуем в список словарей
                data = []
                for row in rows:
                    row_dict = dict(row._mapping)
                    # Преобразуем все datetime объекты в строки
                    for key, value in row_dict.items():
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                    data.append(row_dict)
                
                return data
                
        except Exception as e:
            logging.error(f"Ошибка получения данных из {table_name}: {e}")
            return []
        
    def get_all_table_data_orm(self, template_name: str, table_name: str):
        """Возвращает все данные из таблицы с использованием ORM"""
        try:
            engine = self.get_engine(template_name)
            if not engine:
                return []
            
            # Создаем базовый класс
            Base = declarative_base()
            
            # Динамически создаем класс таблицы
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            
            # Создаем атрибуты для класса
            attrs = {'__tablename__': table_name}
            for column in columns:
                column_type = self._get_column_type(str(column['type']))
                attrs[column['name']] = Column(column_type)
            
            # Создаем класс динамически
            TableClass = type(table_name, (Base,), attrs)
            
            # Создаем сессию
            Session = sessionmaker(bind=engine)
            with Session() as session:
                # Получаем все записи
                records = session.query(TableClass).all()
                
                # Преобразуем в словари
                data = []
                for record in records:
                    record_dict = {}
                    for column in columns:
                        value = getattr(record, column['name'])
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        record_dict[column['name']] = value
                    data.append(record_dict)
                
                return data
                
        except Exception as e:
            # logging.error(f"ORM ошибка: {e}")
            return []