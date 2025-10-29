import logging
import serial
from pathlib import Path
import asyncio
from typing import Dict

from config import settings
from core.logger.logger import start as logger_init
from core.parser.template_manager import TemplateManager
from core.database.migration_manager import MigrationManager
from core.database.db_manager import DatabaseManager
from core.serial.port_manager import PortTemplateManager
from core.database.data_manager import DataManager
from core.serial.async_port_operations import async_read_with_handshake
from core.serial.port_devices_functions import read_line_from_port

def setup_databases():
    """Настраивает базы данных на основе шаблонов"""
    template_manager = TemplateManager()
    migration_manager = MigrationManager()
    db_manager = DatabaseManager()
    
    for template_name in template_manager.list_templates():
        result = migration_manager.check_template_changes(template_name)
        
        if result['has_changes']:
            logging.info(f"Обнаружены изменения в шаблоне {template_name}")
            
            # Валидируем изменения
            changes = migration_manager.validate_changes(result['template'])
            
            if changes:
                # Создаем/обновляем базу данных
                if db_manager.create_database(result['template']):
                    # Сохраняем миграцию
                    migration_manager.create_migration(
                        result['template'], 
                        changes, 
                        result['action']
                    )
                    logging.info(f"База данных для {template_name} успешно настроена")
                else:
                    logging.error(f"Ошибка настройки БД для {template_name}")
            else:
                logging.warning(f"Изменения в шаблоне {template_name} не прошли валидацию")
        else:
            logging.info(f"Шаблон {template_name} без изменений")

def setup_ports() -> Dict[str, str]:
    """Настраивает порты и привязывает шаблоны"""
    port_manager = PortTemplateManager()
    available_ports = [port.device for port in serial.tools.list_ports.comports()]
    
    logging.info(f"Доступные порты: {available_ports}")
    
    port_templates = {}
    
    for port_name in available_ports:
        template_name = port_manager.auto_detect_port_template(port_name)
        if template_name:
            port_manager.assign_template_to_port(port_name, template_name)
            port_templates[port_name] = template_name
            logging.info(f"Порт {port_name} → Шаблон: {template_name}")
        else:
            logging.warning(f"Не удалось определить шаблон для порта {port_name}")
    
    return port_templates

async def process_port_data(port_name: str, template_name: str, 
                          data_manager: DataManager, 
                          template_manager: TemplateManager):
    """Обрабатывает данные с одного порта"""
    try:
        # Загружаем шаблон
        template = template_manager.load_template(template_name)
        logging.info(template)
        if not template:
            logging.error(f"Шаблон {template_name} не найден")
            return False
        
        # Читаем данные из порта
        raw_data = await async_read_with_handshake(port_name)
        if not raw_data:
            logging.debug(f"Нет данных с порта {port_name}")
            return False
        
        # Записываем в БД
        success = await data_manager.insert_sensor_data(template, port_name, raw_data)
        if success:
            logging.info(f"Данные с порта {port_name} записаны в БД: {raw_data}")
        else:
            logging.warning(f"Не удалось записать данные с порта {port_name}")
        
        return success
        
    except Exception as e:
        logging.error(f"Ошибка обработки порта {port_name}: {e}")
        return False

async def data_processing_loop(port_templates: Dict[str, str]):
    """Основной цикл обработки данных"""
    logging.info("Запуск цикла обработки данных...")
    
    data_manager = DataManager()
    template_manager = TemplateManager()
    
    while True:
        processed_count = 0
        error_count = 0
        
        for port_name, template_name in port_templates.items():
            try:
                success = await process_port_data(port_name, template_name, 
                                                data_manager, template_manager)
                if success:
                    processed_count += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                logging.error(f"Критическая ошибка обработки порта {port_name}: {e}")
                error_count += 1
        
        # Логируем статистику
        if processed_count > 0:
            logging.info(f"Обработано портов: {processed_count}, ошибок: {error_count}")
        else:
            logging.debug("Нет данных для обработки")
        
        # Пауза между циклами
        await asyncio.sleep(2)

def main():
    logger_init()
    logging.info("Запуск приложения")
    
    try:
        
        # 1. Настройка баз данных
        logging.info("Проверка шаблонов и настройка БД...")
        setup_databases()
        
        # 2. Настройка портов
        logging.info("Настройка COM-портов...")
        port_templates = setup_ports()

        logging.info('Доступные шаблоны:')
        temp_list = TemplateManager()
        logging.info(temp_list.list_templates)


        if not port_templates:
            logging.warning("Не найдено активных портов с шаблонами")
            return
        
        # 3. Запуск основного цикла
        logging.info("Запуск основного цикла обработки данных...")
        asyncio.run(data_processing_loop(port_templates))
        
    except KeyboardInterrupt:
        logging.info("Приложение остановлено пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
    finally:
        logging.info("Приложение завершено")

if __name__ == "__main__":
    main()