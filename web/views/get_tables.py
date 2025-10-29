from starlette.responses import JSONResponse

from sqlalchemy import create_engine, MetaData, Table, select, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime


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

def create_get_tables(db_manager): 
    async def get_tables(request):
        """Возвращает список всех таблиц во всех базах данных"""
        try:
            tables_info = db_manager.get_all_databases_info()
            
            return JSONResponse({"databases": tables_info})
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return get_tables

def create_get_table_details(db_manager):
    async def get_table_details(request):
        """Возвращает детальную информацию о таблице"""
        try:
            template_name = request.path_params.get('template_name')
            table_name = request.path_params.get('table_name')
            
            if not template_name or not table_name:
                return JSONResponse({"error": "Template name and table name are required"}, status_code=400)
            
            table_info = db_manager.get_table_info(template_name, table_name)
            return JSONResponse(table_info)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return get_table_details

def create_get_table_data(db_manager):
    async def get_table_data(request):
        """Возвращает все данные из таблицы"""
        try:
            template_name = request.path_params.get('template_name')
            table_name = request.path_params.get('table_name')
            
            if not template_name or not table_name:
                return JSONResponse({"error": "Template name and table name are required"}, status_code=400)
            
            table_data = db_manager.get_all_table_data_orm(template_name=template_name, table_name=table_name)
            return JSONResponse({
                "template_name": template_name,
                "table_name": table_name,
                "data": table_data,
                "count": len(table_data)
            })
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return get_table_data