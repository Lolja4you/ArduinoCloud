import logging
from typing import Optional
import asyncio
from .port_devices_functions import open_port, read_line_from_port, close_port

async def async_read_with_handshake(port_name: str, baudrate: int = 115200,
                                  timeout: int = 1, handshake_timeout: int = 3) -> Optional[str]:
    """Читает данные с выполнением рукопожатия и ожиданием реальных данных"""
    try:
        # Открываем порт с рукопожатием
        ser = open_port(port_name, baudrate, timeout, handshake_timeout)
        if not ser:
            return None
        
        # Даем время Arduino отправить данные после handshake
        await asyncio.sleep(1)
        
        # Читаем несколько строк, пропуская handshake сообщения
        max_attempts = 5
        for attempt in range(max_attempts):
            data, success = read_line_from_port(ser)
            
            if success:
                try:
                    decoded_data = data.decode('utf-8', errors='ignore').strip()
                    if decoded_data and not any(x in decoded_data for x in ['HANDSHAKE', 'ARDUINO_READY']):
                        close_port(ser)
                        return decoded_data
                    else:
                        logging.debug(f"Пропускаем служебное сообщение: {decoded_data}")
                except UnicodeDecodeError:
                    pass
            
            await asyncio.sleep(0.5)
        
        close_port(ser)
        return None
        
    except Exception as e:
        logging.error(f"Ошибка чтения с рукопожатием из порта {port_name}: {e}")
        try:
            close_port(ser)
        except:
            pass
        return None

async def async_read_after_handshake(port_name: str, baudrate: int = 115200,
                                   timeout: int = 1) -> Optional[str]:
    """Читает данные после уже выполненного handshake"""
    try:
        ser = open_port(port_name, baudrate, timeout)
        if not ser:
            return None
        
        # Читаем несколько строк, пропуская handshake сообщения
        max_attempts = 3
        for attempt in range(max_attempts):
            data, success = read_line_from_port(ser)
            
            if success:
                try:
                    decoded_data = data.decode('utf-8', errors='ignore').strip()
                    if decoded_data and not any(x in decoded_data for x in ['HANDSHAKE', 'ARDUINO_READY']):
                        close_port(ser)
                        return decoded_data
                except UnicodeDecodeError:
                    pass
            
            await asyncio.sleep(0.5)
        
        close_port(ser)
        return None
        
    except Exception as e:
        logging.error(f"Ошибка чтения из порта {port_name}: {e}")
        try:
            close_port(ser)
        except:
            pass
        return None