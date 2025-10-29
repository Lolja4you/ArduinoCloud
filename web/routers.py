from starlette.routing import Route

from core.parser.template_manager import TemplateManager
from core.serial.port_manager import PortTemplateManager
from core.database.db_manager import DatabaseManager

from web.views.get_templates import create_get_templates
from web.views.get_ports import create_get_ports
from web.views.root import create_root
from web.views.get_tables import (
    create_get_table_details, 
    create_get_tables,
    create_get_table_data,
)
# from views.health_check import health_check

# from .get_templates import create_get_templates
# from .get_ports import create_get_ports
# from .root import create_root
# from .health_check import create_health_check

# Создаем экземпляры менеджеров
template_manager = TemplateManager()
port_manager = PortTemplateManager()
db_manager = DatabaseManager()

def create_views(template_manager, port_manager):
    return {
        "root": create_root(),
        "get_templates": create_get_templates(template_manager),
        "get_ports": create_get_ports(port_manager),
        "get_table_details":create_get_table_details(db_manager),
        "get_tables":create_get_tables(db_manager),
        "get_table_data": create_get_table_data(db_manager),
    }


# Создаем view с зависимостями
views = create_views(template_manager, port_manager)

routes = [
    Route("/", views["root"]),
    # Route("/health", views["health_check"]),
    Route("/templates", views["get_templates"]),
    Route("/ports", views["get_ports"]),
    Route("/get_tables", views['get_tables']),
    Route(
        '/get_table_details/{table_name}/{template_name}', 
        views['get_table_details']
        ),
    Route(
        "/{table_name}/{template_name}",  
          views['get_table_data']
        )
]