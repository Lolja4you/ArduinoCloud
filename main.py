import logging
import serial
from pathlib import Path
import asyncio
from typing import Dict
import os
import sys
import subprocess
import multiprocessing

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
        success = data_manager.insert_sensor_data(template, port_name, raw_data)
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

def start_data_processing():
    """
    Запускает процесс сбора и парсинга данных с COM-портов в БД
    """
    logger_init()
    logging.info("Запуск процесса обработки данных с COM-портов")
    
    try:
        # 1. Настройка баз данных
        logging.info("Проверка шаблонов и настройка БД...")
        setup_databases()
        
        # 2. Настройка портов
        logging.info("Настройка COM-портов...")
        port_templates = setup_ports()

        logging.info('Доступные шаблоны:')
        temp_list = TemplateManager()
        logging.info(temp_list.list_templates())

        if not port_templates:
            logging.warning("Не найдено активных портов с шаблонами")
            return
        
        # 3. Запуск основного цикла
        logging.info("Запуск основного цикла обработки данных...")
        asyncio.run(data_processing_loop(port_templates))
        
    except KeyboardInterrupt:
        logging.info("Процесс обработки данных остановлен пользователем")
    except Exception as e:
        logging.error(f"Критическая ошибка в процессе обработки данных: {e}")
    finally:
        logging.info("Процесс обработки данных завершен")

def start_starlette_server():
    """
    Запускает Starlette сервер
    """
    logger_init()
    logging.info("Запуск Starlette сервера")
    
    try:
        # Импортируем здесь чтобы избежать циклических импортов
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse
        import uvicorn
        
        from web.routers import routes
        
        app = Starlette(routes=routes)
        
        # Запускаем сервер
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        
    except KeyboardInterrupt:
        logging.info("Starlette сервер остановлен пользователем")
    except Exception as e:
        logging.error(f"Ошибка запуска Starlette сервера: {e}")
    finally:
        logging.info("Starlette сервер завершен")

def run_in_new_console(script_path, *args):
    """
    Запускает скрипт в новой консоли
    """
    if sys.platform == "win32":
        # Для Windows
        cmd = ['start', 'cmd', '/k', sys.executable, script_path] + list(args)
        subprocess.Popen(cmd, shell=True)
    else:...
        # Для Linux/Mac
        # cmd = ['xterm', '-e', sys.executable, script_path] + list(args)
        # subprocess.Popen(cmd)

def show_menu():
    """
    Показывает меню выбора
    """
    print("=" * 50)
    print("МЕНЮ УПРАВЛЕНИЯ СИСТЕМОЙ СБОРА ДАННЫХ")
    print("=" * 50)
    print("1. Запуск обработки данных с COM-портов")
    print("2. Запуск Starlette сервера")
    print("3. Запуск обоих процессов (в разных консолях)")
    print("4. Выход")
    print("=" * 50)
    
    while True:
        try:
            choice = input("Выберите опцию (1-4): ").strip()
            if choice in ['1', '2', '3', '4']:
                return choice
            else:
                print("Неверный выбор. Попробуйте снова.")
        except KeyboardInterrupt:
            print("\nВыход из меню")
            return '4'

def main():
    """
    Основная функция с меню выбора
    """
    logger_init()
    
    while True:
        choice = show_menu()
        
        if choice == '1':
            print("Запуск обработки данных...")
            start_data_processing()
            
        elif choice == '2':
            print("Запуск Starlette сервера...")
            start_starlette_server()
            
        elif choice == '3':
            print("Запуск обоих процессов в разных консолях...")
            
            # Получаем путь к текущему скрипту
            current_script = os.path.abspath(__file__)
            
            # Запускаем обработку данных в новой консоли
            run_in_new_console(current_script, "--mode", "data")
            
            # Запускаем сервер в новой консоли
            run_in_new_console(current_script, "--mode", "server")
            
            print("Оба процесса запущены в отдельных консолях")
            print("Нажмите Enter чтобы вернуться в меню...")
            input()
            
        elif choice == '4':
            print("Выход из программы")
            break

# Добавим поддержку аргументов командной строки
if __name__ == "__main__":
    import argparse
    
    # Если есть аргументы командной строки
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(description="Sensor Data Processing System")
        parser.add_argument('--mode', choices=['data', 'server', 'menu'], 
                           default='menu', help='Режим работы')
        
        args = parser.parse_args()
        
        if args.mode == 'data':
            start_data_processing()
        elif args.mode == 'server':
            start_starlette_server()
        else:
            main()
    else:
        # Запуск с меню по умолчанию
        main()