
def crc8(byte_array):
    crc = 0
    for byte in byte_array:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


# Пример данных для структуры SyncFrame
sync_frame = [4,4,6,7,8,9]

# Первый байт - это CRC8
received_crc = sync_frame[0]

# Остальные байты структуры
data_bytes = sync_frame[1:]

# Вычисляем CRC8 для оставшихся байт
calculated_crc = crc8(data_bytes)

# Проверяем совпадение
if calculated_crc == received_crc:
    print("CRC8 check passed.")
else:
    print(f"CRC8 check failed. Calculated: {calculated_crc}, Received: {received_crc}")
