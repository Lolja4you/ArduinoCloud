import logging
from typing import Dict, Optional, List
import serial.tools.list_ports

from core.parser.template_manager import TemplateConfig
from core.parser.template_manager import TemplateManager
from core.serial.port_devices_functions import open_port, read_line_from_port, close_port
import time

class PortTemplateManager:
    def __init__(self):
        self.template_manager = TemplateManager()
        self.port_templates: Dict[str, str] = {}  # port -> template_name
    
    def auto_detect_port_template(self, port_name: str, read_timeout: int = 5) -> Optional[str]:
        """Автоматически определяет подходящий шаблон для порта"""
        try:
            ser = open_port(port_name, baudrate=115200, timeout=1)
            if not ser:
                return None
            
            logging.info(f"Анализируем данные с порта {port_name}...")
            
            # Читаем данные в течение timeout
            sample_data = []
            start_time = time.time()
            
            while time.time() - start_time < read_timeout:
                data, success = read_line_from_port(ser)
                if success:
                    try:
                        decoded_data = data.decode('utf-8', errors='ignore').strip()
                        if decoded_data and not decoded_data.startswith('HANDSHAKE'):
                            sample_data.append(decoded_data)
                            logging.debug(f"Получены данные: {decoded_data}")
                    except UnicodeDecodeError:
                        continue
                
                if len(sample_data) >= 3:  # Достаточно данных для анализа
                    break
            
            close_port(ser)
            
            if not sample_data:
                logging.warning(f"Не получено данных с порта {port_name}")
                return None
            
            # Ищем подходящий шаблон
            matching_template = self._find_matching_template(sample_data)
            
            if matching_template:
                logging.info(f"Порт {port_name} → Шаблон: {matching_template}")
            else:
                logging.warning(f"Не найден подходящий шаблон для порта {port_name}")
                
            return matching_template
            
        except Exception as e:
            logging.error(f"Ошибка детекта шаблона для {port_name}: {e}")
            return None
    
    def _find_matching_template(self, sample_data: List[str]) -> Optional[str]:
        """Ищет подходящий шаблон для данных"""
        best_match = None
        best_score = 0
        
        for template_name in self.template_manager.list_templates():
            template = self.template_manager.load_template(template_name)
            if template:
                score = self._calculate_match_score(sample_data, template)
                if score > best_score:
                    best_score = score
                    best_match = template_name
        
        # Минимальный порог совпадения - 30%
        return best_match if best_score >= 0.3 else None
    
    def _calculate_match_score(self, sample_data: List[str], template: TemplateConfig) -> float:
        """Вычисляет score совпадения данных с шаблоном"""
        if not sample_data:
            return 0.0
        
        # Собираем все expected поля из шаблона
        expected_fields = set()
        for sensor in template.sensors:
            for field in sensor.fields:
                expected_fields.add(field.source)
        
        if not expected_fields:
            return 0.0
        
        # Анализируем каждую строку данных
        total_score = 0.0
        lines_analyzed = 0
        
        for data_line in sample_data:
            if not data_line:
                continue
                
            line_score = 0.0
            found_fields = 0
            
            # Проверяем наличие expected полей в строке
            for field in expected_fields:
                if field in data_line:
                    found_fields += 1
            
            # Score для этой строки
            if expected_fields:
                line_score = found_fields / len(expected_fields)
            
            total_score += line_score
            lines_analyzed += 1
        
        return total_score / lines_analyzed if lines_analyzed > 0 else 0.0
    
    def assign_template_to_port(self, port_name: str, template_name: str) -> bool:
        """Привязывает шаблон к порту"""
        if template_name in self.template_manager.list_templates():
            self.port_templates[port_name] = template_name
            logging.info(f"Порт {port_name} привязан к шаблону {template_name}")
            return True
        return False