import pandas as pd
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, MetaData, Table, select, inspect
import os

# Создаем подключение к базе данных
DB_PATH = os.path.join(os.path.dirname(__file__), 'databases', 'weather_station.db')
engine = create_engine(f'sqlite:///{DB_PATH}')
metadata = MetaData()

def generate_test_data():
    """Генерация тестовых данных для outdoor_sensor"""
    
    # Параметры генерации
    num_records = 68
    base_temp = 15.0  # Базовая температура
    base_pressure = 1013.25  # Базовое давление
    
    data = []
    current_time = datetime.now() - timedelta(hours=24)  # Начинаем с 24 часов назад
    
    for i in range(num_records):
        # Генерируем реалистичные данные
        temperature = base_temp + random.uniform(-5, 5)  # Температура от 10 до 20
        pressure = base_pressure + random.uniform(-10, 10)  # Давление от 1003 до 1023
        
        record = {
            'id': i + 1,
            'timestamp': current_time,
            'sensor_id': 'outdoor_01',
            'temperature': round(temperature, 2),
            'pressure': round(pressure, 2)
        }
        
        data.append(record)
        current_time += timedelta(minutes=21)  # Каждые 21 минуту новая запись
    
    # Создаем DataFrame
    df = pd.DataFrame(data)
    
    # Записываем в базу данных
    df.to_sql('outdoor_sensor', engine, if_exists='replace', index=False)
    
    print(f"Сгенерировано {len(df)} записей в таблицу outdoor_sensor")
    print("Первые 5 записей:")
    print(df.head())
    
    return df

# Альтернативный вариант с более реалистичными данными (дневной цикл)
def generate_realistic_data():
    """Генерация более реалистичных данных с дневным циклом"""
    
    num_records = 68
    data = []
    current_time = datetime.now() - timedelta(hours=24)
    
    for i in range(num_records):
        # Дневной цикл температуры (холоднее ночью, теплее днем)
        hour = current_time.hour
        time_factor = -5 * math.cos(2 * math.pi * (hour - 14) / 24)  # Пик в 14:00
        
        # Случайные колебания
        temp_variation = random.uniform(-2, 2)
        pressure_variation = random.uniform(-5, 5)
        
        temperature = 15.0 + time_factor + temp_variation
        pressure = 1013.25 + pressure_variation
        
        record = {
            'id': i + 1,
            'timestamp': current_time,
            'sensor_id': '0x76',
            'temperature': round(temperature, 2),
            'pressure': round(pressure, 2)
        }
        
        data.append(record)
        current_time += timedelta(minutes=21)
    
    df = pd.DataFrame(data)
    df.to_sql('indoor_sensor', engine, if_exists='replace', index=False)
    
    print(f"Сгенерировано {len(df)} реалистичных записей")
    print(df.head())
    return df

# Быстрая генерация простых данных
def quick_generate():
    """Быстрая генерация тестовых данных"""
    
    import math
    
    data = []
    current_time = datetime.now() - timedelta(hours=24)
    
    for i in range(68):
        # Простая синусоида для температуры
        temp = 10 + 1 * math.sin(i * 0.1)
        pressure = 1000 + 10 * math.cos(i * 0.05)
        
        record = {
            'id': i + 1,
            'timestamp': current_time,
            'sensor_id': '0x77',
            'temperature': round(temp, 2),
            'pressure': round(pressure, 2)
        }
        
        data.append(record)
        current_time += timedelta(minutes=21)
    
    df = pd.DataFrame(data)
    df.to_sql('outdoor_sensor', engine, if_exists='replace', index=False)
    
    print("✅ Тестовые данные сгенерированы!")
    print(f"📊 Записей: {len(df)}")
    print(f"🌡️  Температура: {df['temperature'].min():.1f}°C - {df['temperature'].max():.1f}°C")
    print(f"📈 Давление: {df['pressure'].min():.1f} hPa - {df['pressure'].max():.1f} hPa")
    
    return df

# Запуск генерации
if __name__ == "__main__":
    df = quick_generate()