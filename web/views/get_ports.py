from starlette.responses import JSONResponse
import serial

def get_all_devices_ports():
    """Возвращает список всех доступных COM-портов"""
    ports = list(serial.tools.list_ports.comports())
    port_list = [p.device for p in ports]
    # logging.debug(f"Доступные порты: {port_list}")
    return port_list


def create_get_ports(PortTemplateManager): 
    async def get_ports(request):
        return JSONResponse({"ports": get_all_devices_ports()})
    return get_ports