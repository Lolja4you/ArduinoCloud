import serial
import serial.tools.list_ports
import logging

def check_port_status(port_name):
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

# Пример использования
port = "COM5"
exists, in_use, info = check_port_status(port)
print(f"Порт {port}: {info}")