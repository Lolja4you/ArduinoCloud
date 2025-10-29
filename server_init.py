import serial
import numpy as np
import soundfile as sf
import sys

def main():
    # Настройки подключения
    port = input("Введите COM порт (например COM3 или /dev/ttyUSB0): ")
    baudrate = 115200
    
    try:
        # Подключаемся к Arduino
        ser = serial.Serial(port, baudrate, timeout=1)
        print(f"✅ Подключено к {port}")
        print("Ожидание данных...")
        
        # Ждем стабилизации связи
        time.sleep(2)
        
        audio_data = []
        print("🎤 Запись начата! Нажмите Ctrl+C для остановки")
        
        try:
            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode().strip()
                    if line:  # Если строка не пустая
                        try:
                            sample = int(line)
                            audio_data.append(sample)
                            print(f"📊 Сэмпл: {sample}", end='\r')
                        except ValueError:
                            continue
                            
        except KeyboardInterrupt:
            print("\n⏹️ Остановка записи...")
            
        # Сохраняем аудио файл
        if audio_data:
            # Конвертируем в правильный формат
            audio_array = np.array(audio_data, dtype=np.float32)
            audio_array = (audio_array - 512) / 512.0  # Центрируем вокруг 0
            
            # Сохраняем как WAV файл
            sf.write("audio_from_arduino.wav", audio_array, 8000)
            print(f"💾 Файл сохранен: audio_from_arduino.wav")
            print(f"📈 Записано сэмплов: {len(audio_data)}")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"❌ Ошибка подключения: {e}")
        print("Проверьте порт и подключение Arduino")

main()