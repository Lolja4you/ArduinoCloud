import sys, os
import logging
import colorlog
import yaml

class _Configs:
    _configs: dict = None
    _default_configs = {
        'logging': {
            'console': 2,  # По умолчанию и в файл и в консоль
            'file': 'logs/app.log',
            'level': 'INFO'
        }
    }

    @classmethod
    def _init_configs(cls) -> None:
        try:
            with open('configs.yaml', 'r', encoding="utf8") as f:
                cls._configs = yaml.load(f, Loader=yaml.FullLoader)
                logging.info("Конфигурация загружена из configs.yaml")
        except FileNotFoundError:
            # Создаем стандартный конфиг
            cls._configs = cls._default_configs
            logging.warning("Файл configs.yaml не найден. Используется стандартная конфигурация.")
            
            # Создаем файл конфига
            try:
                with open('configs.yaml', 'w', encoding="utf8") as f:
                    yaml.dump(cls._default_configs, f, default_flow_style=False, allow_unicode=True)
                logging.info("Создан стандартный файл конфигурации: configs.yaml")
            except Exception as e:
                logging.error(f"Ошибка при создании файла конфигурации: {e}")
        except Exception as e:
            # В случае других ошибок используем стандартный конфиг
            cls._configs = cls._default_configs
            logging.error(f"Ошибка при загрузке конфигурации: {e}. Используется стандартная конфигурация.")


class LoggerConfigs(_Configs):
    _config_name = 'logging'

    @classmethod
    def is_console(cls) -> int:
        if cls._configs is None:
            cls._init_configs()
        return cls._configs[cls._config_name]['console']

    @classmethod
    def file(cls) -> str:
        if cls._configs is None:
            cls._init_configs()
        return cls._configs[cls._config_name]['file']

    @classmethod
    def level(cls) -> str:
        if cls._configs is None:
            cls._init_configs()
        return cls._configs[cls._config_name]['level']


def start():
    # Сначала создаем временный консольный логгер для вывода служебных сообщений
    temp_logger = logging.getLogger()
    temp_handler = logging.StreamHandler(sys.stdout)
    temp_handler.setFormatter(logging.Formatter('%(message)s'))
    temp_logger.addHandler(temp_handler)
    temp_logger.setLevel(logging.INFO)
    
    # Проверяем и инициализируем конфигурацию
    if LoggerConfigs._configs is None:
        LoggerConfigs._init_configs()
    
    # Удаляем временный обработчик
    temp_logger.removeHandler(temp_handler)
    
    log_format = colorlog.ColoredFormatter(
        '[%(asctime)s] %(log_color)s%(levelname)s:%(reset)s %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        },
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger()
    
    # Очищаем все существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Преобразуем строковый уровень в числовой
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    log_level = level_mapping.get(LoggerConfigs.level(), logging.INFO)
    logger.setLevel(log_level)

    is_console = LoggerConfigs.is_console()
    handlers = []

    # Всегда добавляем файловый обработчик для записи в файл
    try:
        log_file_path = LoggerConfigs.file()
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    except Exception as e:
        print(f"Ошибка при создании файлового обработчика: {e}")

    # Добавляем консольный обработчик в зависимости от настроек
    if is_console in [1, 2]:  # 1 - только консоль, 2 - файл и консоль
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(log_format)
        handlers.append(stream_handler)

    if not handlers:
        raise ValueError('Unexpected value for log out')

    for handler in handlers:
        logger.addHandler(handler)
    
    # Теперь все сообщения будут идти через настроенный логгер
    logging.info("Логгер успешно инициализирован")
    logging.debug("Режим отладки активен")
    logging.warning("Это предупреждение")
    logging.error("Это ошибка\n")
    