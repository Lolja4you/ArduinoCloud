import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging
from datetime import datetime

from core.parser.template_manager import TemplateManager, TemplateConfig

class MigrationManager:
    def __init__(self, migrations_dir: Path = Path("migrations")):
        self.migrations_dir = migrations_dir
        self.migrations_dir.mkdir(exist_ok=True)
        self.template_manager = TemplateManager()
    
    def calculate_template_hash(self, template_config: TemplateConfig) -> str:
        """Вычисляет хеш шаблона для отслеживания изменений"""
        template_str = json.dumps(template_config.dict(), sort_keys=True)
        return hashlib.md5(template_str.encode()).hexdigest()
    
    def get_last_migration_hash(self, template_name: str) -> Optional[str]:
        """Получает последний хеш миграции для шаблона"""
        migration_files = list(self.migrations_dir.glob(f"{template_name}_*.json"))
        if not migration_files:
            return None
        
        # Берем самую свежую миграцию
        latest_migration = max(migration_files, key=lambda x: x.stat().st_mtime)
        
        try:
            with open(latest_migration, 'r', encoding='utf-8') as f:
                migration_data = json.load(f)
                return migration_data.get('template_hash')
        except:
            return None
    
    def create_migration(self, template_config: TemplateConfig, 
                        changes: List[Dict], action: str) -> bool:
        """Создает файл миграции"""
        migration_data = {
            'timestamp': datetime.now().isoformat(),
            'template_name': template_config.template_name,
            'template_hash': self.calculate_template_hash(template_config),
            'action': action,
            'changes': changes,
            'template_version': template_config.template_version
        }
        
        migration_file = self.migrations_dir / f"{template_config.template_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(migration_file, 'w', encoding='utf-8') as f:
                json.dump(migration_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Ошибка создания миграции: {e}")
            return False
    
    def check_template_changes(self, template_name: str) -> Dict:
        """Проверяет изменения в шаблоне"""
        template = self.template_manager.load_template(template_name)
        if not template:
            return {'has_changes': False, 'error': 'Template not found'}
        
        current_hash = self.calculate_template_hash(template)
        last_hash = self.get_last_migration_hash(template_name)
        
        if last_hash is None:
            return {'has_changes': True, 'action': 'create', 'template': template}
        
        if current_hash != last_hash:
            return {'has_changes': True, 'action': 'update', 'template': template}
        
        return {'has_changes': False, 'template': template}
    
    def validate_changes(self, template: TemplateConfig, 
                        old_template: Optional[TemplateConfig] = None) -> List[Dict]:
        """Валидирует изменения шаблона"""
        changes = []
        
        if old_template is None:
            # Новая таблица
            changes.append({
                'type': 'create_table',
                'table_name': template.database.db_name,
                'sensors_count': len(template.sensors)
            })
        else:
            # TODO: Реализовать детект изменений
            changes.append({
                'type': 'update_table',
                'table_name': template.database.db_name,
                'changes': 'Template updated'
            })
        
        return changes