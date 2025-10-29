import serial.tools.list_ports
import serial, time, math
from datetime import datetime, timedelta
import logging

# Импортируем наш логгер (путь может отличаться в зависимости от структуры)
from core.logger.logger import start as init_logger

# Инициализируем логгер (если еще не инициализирован)
# Это можно сделать здесь или в main.py
# init_logger()

class HandshakeStatus:
    SUCCESS = "success"
    PORT_NOT_OPEN = "port_not_open"
    NO_RESPONSE = "no_response"
    WRONG_RESPONSE = "wrong_response"
    TIMEOUT = "timeout"

def get_devices_port():
    """Возвращает первый найденный COM-порт или None если портов нет"""
    ports = list(serial.tools.list_ports.comports())
    if ports:
        logging.info(f"Найден порт: {ports[0].device}")
        return ports[0].device
    logging.warning("COM-порты не найдены")
    return None

def get_all_devices_ports():
    """Возвращает список всех доступных COM-портов"""
    ports = list(serial.tools.list_ports.comports())
    port_list = [p.device for p in ports]
    logging.debug(f"Доступные порты: {port_list}")
    return port_list

def close_port(port):
    """Закрывает порт и возвращает статус операции"""
    if port is None:
        logging.warning("Попытка закрыть несуществующий порт")
        return False    
    try:
        port.close()
        logging.info(f"Порт {port} успешно закрыт")
        return True
    except Exception as e:
        logging.error(f"Ошибка при закрытии порта {port}: {e}")
        return False

def get_port_status(port_name):
    """
    Полная проверка статуса COM-порта
    Возвращает: (exists, in_use, info)
    """
    # Проверяем существование порта
    ports = [port.device for port in serial.tools.list_ports.comports()]
    if port_name not in ports:
        return False, False, "Порт не существует"
    
    # Пытаемся открыть порт
    try:
        ser = serial.Serial(port_name)
        ser.close()
        return True, False, "Порт свободен"
    except serial.SerialException as e:
        error_msg = str(e)
        if "Access is denied" in error_msg or "PermissionError" in error_msg:
            return True, True, "Порт занят другим процессом"
        else:
            return True, False, f"Ошибка открытия: {error_msg}"


def perform_handshake(port, timeout=3):
    """
    Выполняет тройное рукопожатие с устройством на порту
    """
    if port is None or not port.is_open:
        logging.error("Порт не открыт для рукопожатия")
        return HandshakeStatus.PORT_NOT_OPEN
    
    try:
        # Очищаем буфер перед началом рукопожатия
        port.reset_input_buffer()
        time.sleep(0.1)
        
        # Шаг 1: Отправляем запрос рукопожатия
        handshake_request = "HANDSHAKE_REQ\n"
        port.write(handshake_request.encode('utf-8'))
        logging.debug("Отправлен запрос рукопожатия")
        
        # Шаг 2: Ждем ответ от устройства
        start_time = time.time()
        while time.time() - start_time < timeout:
            if port.in_waiting > 0:
                response = port.readline().decode('utf-8').strip()
                logging.debug(f"Получен ответ: {response}")
                
                if response == "HANDSHAKE_ACK":
                    # Шаг 3: Подтверждаем получение
                    ack_response = "HANDSHAKE_CONFIRM\n"
                    port.write(ack_response.encode('utf-8'))
                    logging.info("Рукопожатие успешно завершено")
                    return HandshakeStatus.SUCCESS
                elif response == "ARDUINO_READY":
                    # Устройство уже готово
                    logging.info("Устройство готово к работе")
                    return HandshakeStatus.SUCCESS
                elif response:
                    # Другой ответ - возможно устройство уже отправило данные
                    logging.debug(f"Получен неожиданный ответ: {response}")
                    # Продолжаем ждать HANDSHAKE_ACK
            
            time.sleep(0.1)
        
        logging.warning("Таймаут рукопожатия")
        return HandshakeStatus.TIMEOUT
        
    except Exception as e:
        logging.error(f"Ошибка рукопожатия: {e}")
        return HandshakeStatus.NO_RESPONSE

def open_port(port_name, baudrate=115200, timeout=1, handshake_timeout=3):
    """Открывает COM-порт, выполняет рукопожатие и возвращает объект порта"""
    logging.info(f"Пытаемся подключиться к {port_name}")

    port_status = get_port_status(port_name)
    if not port_status[0]:  # Порт не существует
        logging.error(f"Порт {port_name} не существует")
        return False
    if port_status[1]:  # Порт занят
        logging.error(f"Порт {port_name} занят другим процессом")
        return False
    
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=baudrate,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        logging.info(f"Порт {port_name} успешно открыт (baudrate: {baudrate}, timeout: {timeout}s)")
        
        # Даем устройству время на инициализацию
        time.sleep(2)
        
        # Выполняем рукопожатие
        handshake_result = perform_handshake(ser, handshake_timeout)
        
        if handshake_result == HandshakeStatus.SUCCESS:
            logging.info(f"Успешное рукопожатие с {port_name}")
            return ser
        else:
            logging.warning(f"Рукопожатие не удалось: {handshake_result}")
            ser.close()
            return False
            
    except serial.SerialException as e:
        logging.error(f"Ошибка открытия порта {port_name}: {e}")
        return False

def read_line_from_port(port, timeout=1):
    """
    Читает сырые данные из порта (без декодирования)
    """
    if port is None or not port:
        logging.warning("Попытка чтения из закрытого порта")
        return "Порт не открыт", False
    
    try:
        # Читаем сырые байты
        line = port.readline()
        if line:
            logging.info(f"Прочитаны сырые данные с порта {port.port}: {line}")
            return line, True
        else:
            logging.debug(f"Нет данных на порту {port.port}")
            return "Нет данных", False
            
    except serial.SerialException as e:
        logging.error(f"Ошибка чтения с порта {port.port}: {e}")
        return f"Ошибка чтения: {e}", False

def read_data_raw(port):
    """
    Читает строку данных из порта с использованием встроенного таймаута
    """
    if port is None or not port:
        logging.warning("Попытка чтения из закрытого порта")
        return "Порт не открыт", False
    
    try:
        # Используем readline() который ждет строку или таймаут
        data = port.readline()
        
        if data and len(data) > 0:
            logging.info(f"Прочитаны данные с порта {port.port}: {data}")
            return data, True
        else:
            logging.debug(f"Нет данных на порту {port.port}")
            return "Нет данных", False
            
    except serial.SerialException as e:
        logging.error(f"Ошибка чтения с порта {port.port}: {e}")
        return f"Ошибка чтения: {e}", False
    

def reconnect(port_name, baudrate=9600, timeout=1, max_duration_hours=1):
    """
    Попытка переподключения к COM-порту с экспоненциальной задержкой
    """
    max_duration = timedelta(hours=max_duration_hours)
    start_time = datetime.now()
    attempt = 1
    
    logging.info(f"Начало попыток переподключения к {port_name}")
    logging.info(f"Максимальное время попыток: {max_duration_hours} час(а)")
    
    while datetime.now() - start_time < max_duration:
        try:
            logging.info(f"Попытка {attempt}: подключение к {port_name}...")
            
            # Проверяем, доступен ли порт в системе
            available_ports = get_all_devices_ports()
            if port_name not in available_ports:
                logging.warning(f"Порт {port_name} не найден в системе. Доступные порты: {available_ports}")
                raise serial.SerialException(f"Порт {port_name} недоступен")
            
            # Пытаемся открыть порт
            ser = open_port(port_name, baudrate, timeout)
            
            # Проверяем, что порт действительно открылся
            if ser.is_open:
                logging.info(f"Успешное подключение к {port_name} на попытке {attempt}!")
                logging.info(f"Настройки порта: {baudrate} baud, timeout: {timeout}s")
                return ser, True, attempt
            
        except serial.SerialException as e:
            error_msg = str(e)
            logging.warning(f"Ошибка подключения (попытка {attempt}): {error_msg}")
            
            # Анализируем ошибку для лучшего сообщения
            if "Access is denied" in error_msg or "Permission denied" in error_msg:
                logging.warning("Порт занят другим приложением")
            elif "could not open port" in error_msg.lower():
                logging.warning("Порт недоступен или не существует")
            else:
                logging.warning("Общая ошибка подключения")
        
        except Exception as e:
            logging.error(f"Неожиданная ошибка (попытка {attempt}): {e}")
        
        # Вычисляем задержку до следующей попытки
        if attempt == 1:
            delay = 5  # Первая задержка - 5 секунд
        else:
            # Экспоненциальная задержка с ограничением в 1 час
            delay = min(5 * math.pow(2, attempt - 1), 3600)
        
        # Проверяем, не превысит ли задержка максимальное время
        time_elapsed = datetime.now() - start_time
        if time_elapsed + timedelta(seconds=delay) >= max_duration:
            remaining_time = max_duration - time_elapsed
            if remaining_time.total_seconds() > 0:
                delay = remaining_time.total_seconds()
                logging.info(f"Корректируем задержку до {delay:.1f} секунд из-за ограничения времени")
            else:
                break
        
        logging.info(f"Следующая попытка через {delay:.1f} секунд...")
        time.sleep(delay)
        attempt += 1
    
    logging.error(f"Превышено максимальное время попыток ({max_duration_hours} час)")
    logging.info(f"Всего попыток: {attempt-1}")
    return None, False, attempt-1

def reconnect_forever(port_name, baudrate=9600, timeout=1):
    """
    Бесконечное переподключение к порту с прогрессивной задержкой
    """
    attempt = 1
    max_delay = 3600  # Максимальная задержка - 1 час
    
    logging.info(f"Запуск бесконечного переподключения к {port_name}")
    
    while True:
        try:
            logging.info(f"Попытка {attempt}: подключение к {port_name}...")
            
            # Проверяем доступность порта
            available_ports = get_all_devices_ports()
            if port_name not in available_ports:
                logging.warning(f"Порт {port_name} не найден. Доступные порты: {available_ports}")
                raise serial.SerialException("Порт недоступен")
            
            # Открываем порт
            ser = open_port(port_name, baudrate, timeout)
            if ser.is_open:
                logging.info(f"Успешное подключение на попытке {attempt}!")
                return ser, True, attempt
            
        except Exception as e:
            logging.warning(f"Ошибка (попытка {attempt}): {e}")
        
        # Прогрессивная задержка
        delay = min(5 * math.pow(2, min(attempt, 12) - 1), max_delay)
        logging.info(f"Следующая попытка через {delay:.1f} секунд...")
        time.sleep(delay)
        attempt += 1