import argparse
import json
import re
import sys


def tc(value):
    value -= 1
    abs_rev_bin_value = bin(value)[3:]
    abs_bin_value = ''
    for i in abs_rev_bin_value:  # ну вот такой не самый эффективный перевод из дополнительного кода в прямой
        if i == '0':
            abs_bin_value += '1'
        else:
            abs_bin_value += '0'
    value = -int(abs_bin_value, 2)
    return value


def count_bytes(bytes_array, check=''):
    value = 0
    for k, j1 in enumerate(bytes_array):  # идет по байтам и считает сумму в little endian порядке
        value += j1 * 256 ** k
    bin_value = bin(value)[2:]
    # если первый бит будет 1, то длина по любому будет равна максимальному значению
    if (check == '%d' and len(bin_value) == 32) or (check == '%lld' and len(bin_value) == 64):
        if args.twoscompl == 1:
            value = tc(value)  # считывание дополнительного кода
        else:
            value = -int(bin_value[1:], 2)  # считывание прямого кода
    return value


def message_search(value):
    if str(value) in js:
        return js[str(value)]
    else:
        return False


def format_with_defaults(format_string, specs):
    specifier_pattern = re.compile(r"%[0-9]*[csdupxX]|%[0-9]*lld|%[0-9]*llu")
    specs_iter = iter(specs)

    def replace_specifier(match):
        try:
            return str(next(specs_iter))
        except StopIteration:
            return match.group(0)  # замена недостающих значений спецификаторов на сами спецификаторы
    formatted_string = specifier_pattern.sub(replace_specifier, format_string)
    return formatted_string


def extract_specifiers(msg):  # получение списка всех спецификаторов в msg и списка форматированных спецификаторов
    specifier_pattern = re.compile(r"%[0-9]*[csdupxX]|%[0-9]*lld|%[0-9]*llu")
    specifiers = specifier_pattern.findall(msg)
    cleaned_specifiers = [re.sub(r'\d', '', specifier) for specifier in specifiers]
    return cleaned_specifiers, specifiers


def get_message(data, stringaddress, tos, tsv):
    stringaddress_value = count_bytes(stringaddress)  # считаем побайтово значение StringAddress
    message = message_search(stringaddress_value)  # ищем само сообщение в js
    variables = {  # общий список спецификаторов с количеством байт для каждого
        '%c': 1, '%s': 4, '%d': 4, '%u': 4, '%x': 4, '%X': 4, '%lld': 8, '%llu': 8
    }
    if not message:
        return 0
    else:  # если сообщение найдено
        specifiers, def_specifiers = extract_specifiers(message)  # получаем 2 списка: с форматированными(%04X) и
        # неформатированными(%X) спецификаторами в сообщении
        offset = 0
        values = []  # итоговый список значения который будет в строке output
        for k, specifier in enumerate(specifiers):
            if specifier in variables:  # если спецификатор из сообщения есть в общем списке, то читаем столько байт
                # (variables[j]) из данных Message (data), сколько требует спецификатор
                sliced = data[offset:offset + variables[specifier]]
                if sliced:  # если данные в data есть
                    if specifier == '%s':
                        value = count_bytes(sliced)  # если %s, то считаем адрес по байтам и находим в js то, что нужно
                        word = message_search(value)
                        if word:
                            values.append(word)
                        else:
                            values.append('[n/a]')  # если слово не найдено
                    elif specifier == '%c':
                        values.append(chr(data[offset]))
                    else:
                        value = count_bytes(sliced, def_specifiers[k])
                        values.append(value)
                    offset += variables[specifier]
                else:
                    break
        if len(values) < len(specifiers):  # если в data слишком мало данных, то дополняем список
            print("%010u.%06u Warning: Not enough values in data" % (tsv, tos), file=sys.stderr)
            formatted_output = format_with_defaults(message, tuple(values))
        elif data[offset:]:  # если в data[offset:] остались непрочитанные данные, значит их слишком много для сообщения
            print("%010u.%06u Warning: Too much values in data" % (tsv, tos), file=sys.stderr)
            formatted_output = (message % tuple(values))
        else:
            formatted_output = (message % tuple(values))
        return formatted_output


def check_crc8(sync_frame):
    byte_array = sync_frame[1:]
    crc = 0
    for byte in byte_array:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x07
            else:
                crc <<= 1
            crc &= 0xFF
    if crc == sync_frame[0]:
        return True
    else:
        return False


def messages_log(page, syncTimeStampValue):
    offset = 10  # чтение начинается с 10 позиции, сразу после структуры SyncFrame
    while offset < 512:  # перебор всех байтов до конца страницы
        size = page[offset + 1]  # size структуры
        if size == 0:  # если размер равен нулю то структура считается invalid
            if args.breakloop == 1:
                break  # move to the next page
        else:
            stringAddress = page[offset + 2:offset + 6]
            timeOffSet = page[offset + 6:offset + 10]  # чтение значений структуры
            timeOffSetValue = count_bytes(timeOffSet)
            data = page[offset + 10:offset + size]
            if count_bytes(stringAddress) == 0:     # если StringAddress равен 0, значит это не Message, а SyncFrame
                syncTimeStampValue = timeOffSetValue  # if SyncFrame structure is found then changing TimeStampValue
            else:
                formated_message = get_message(data, stringAddress, timeOffSetValue, syncTimeStampValue)
                if not check_crc8(page[offset:offset + size]):  # проверка на целостность данных
                    print(("Error: CRC8 check failed. Invalid structure. %010u.%06u " % (syncTimeStampValue, timeOffSetValue)) +
                          f"message: {formated_message}; StringAddressValue: "
                          f"{count_bytes(stringAddress)} data: "
                          f"{data}", file=sys.stderr)
                    if args.breakloop == 1:
                        break  # move to the next page
                else:
                    # вывод сообщения
                    print(("%010u.%06u " % (syncTimeStampValue, timeOffSetValue)) + formated_message, file=sys.stdout)
        offset += size


def first_sync_log(page):
    sync_timestamp = page[6:10]  # чтение TimeStamp байтов
    sync_timestamp_value = count_bytes(sync_timestamp)  # перевод всех байтов в одно число
    messages_log(page, sync_timestamp_value)


def get_json(name):
    with open(name) as jsf:
        return json.load(jsf)


def get_bin(name):
    with open(name, 'rb') as bf:
        return bf.read()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()  # парсер входных аргументов
    parser.add_argument('binary_file', type=str, help='Path to the binary file')
    parser.add_argument('-m', '--json_file', type=str, required=True, help='Path to the JSON file')
    parser.add_argument('-brl', '--breakloop', type=int, default=1, help='Skip to the next page if error occurred. 0 = no, 1 = yes. Default 1')
    #  если данные значений %d %lld записаны не в дополнительном коде, а в прямом, то для учета этого добавил -tc
    parser.add_argument('-tc', '--twoscompl', type=int, default=1, help='Numbers in twos-complement number system. 0 = no, 1 = yes. Default 1')
    args = parser.parse_args()
    bin_bytes = [i for i in get_bin(args.binary_file)]  # чтение файла в массив байтов bin_bytes
    js = get_json(args.json_file)  # чтение json файла в словарь js
    for i in range(len(bin_bytes) // 512):  # перебор всех страниц (учитывается что в каждой странице ровно 512 байт
        # и как минимум одна точно есть)
        print(f"Page {i+1} reading...", file=sys.stdout)
        first_sync_log(bin_bytes[512 * i:512 * (i + 1)])
