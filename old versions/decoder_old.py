import json, re

with open('../input.json') as fd:
    a = json.load(fd)


def count_bytes(bytes_array):
    value = 0
    for k, j1 in enumerate(bytes_array):
        value += j1 * 256 ** k
    return value


def message_search(value):
    if str(value) in a:
        return a[str(value)]
    else:
        return False


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
        print("\033[32m{}\033[0m".format("\t\t\tCRC8 check passed."))
    else:
        print("\033[31m{}\033[0m".format(
            f"\t\t\tCRC8 check failed. Calculated: {crc}, Received: {sync_frame[0]}"))
    return 0


def format_with_defaults(format_string, args):
    specifier_pattern = re.compile(r"%[0-9]*[csdupxX]|%[0-9]*lld|%[0-9]*llu")
    args_iter = iter(args)

    def replace_specifier(match):
        try:
            return str(next(args_iter))
        except StopIteration:
            return match.group(0)

    formatted_string = specifier_pattern.sub(replace_specifier, format_string)
    return formatted_string


def extract_specifiers(c_format):
    specifier_pattern = re.compile(r"%[0-9]*[csdupxX]|%[0-9]*lld|%[0-9]*llu")
    specifiers = specifier_pattern.findall(c_format)
    cleaned_specifiers = [re.sub(r'\d', '', specifier) for specifier in specifiers]
    return cleaned_specifiers, specifiers


def get_message(data, stringaddress):
    stringaddress_value = count_bytes(stringaddress)
    message = message_search(stringaddress_value)
    variables = {
        '%c': 2, '%s': 4, '%d': 4, '%u': 4, '%x': 4, '%X': 4, '%lld': 8, '%llu': 8
    }
    if not message:
        print("\033[33m{}\033[0m".format(f"\t\t\tmessage: n/a; stringaddress_value: {stringaddress_value}"))
    else:
        specifiers, def_specifiers = extract_specifiers(message)
        ofs = 0
        values = []
        for j in specifiers:
            if j in variables:
                try:
                    if j == '%s':
                        value = count_bytes(data[ofs:ofs + variables[j]])
                        word = message_search(value)
                        values.append(word)
                    elif j == '%c':
                        values.append(chr(data[ofs]))
                    else:
                        value = count_bytes(data[ofs:ofs + variables[j]])
                        values.append(value)
                    ofs += variables[j]
                except IndexError:
                    break
        if len(values) < len(specifiers):
            formatted_output = format_with_defaults(message, tuple(values))
        else:
            formatted_output = ("\t\t\t" + message % tuple(values))
        print("\033[34m{}\033[0m".format(formatted_output))
        # stdout stdin stderr
        ###
        # знак плюса минуса


def messages_log(page):
    offset = 10
    while offset < 512:
        crc8 = page[offset]
        size = page[offset + 1]
        if size == 0:
            print("\033[33m{}\033[0m".format(f"\t\t\tsize = 0; remaining: {page[offset:]}"))
            break
        else:
            stringAddress = page[offset + 2:offset + 6]
            timeOffSet = page[offset + 6:offset + 10]
            timeOffSetValue = count_bytes(timeOffSet)
            data = page[offset + 10:offset + 10 + (size - 10)]
            print(
                f"\t\tMessage\n\t\t\tOFFSET: {offset}\n\t\t\tcrc8: {crc8}\n\t\t\tsize: {size}\n\t\t\tstringAddress: {stringAddress}\n\t\t\ttimeOffSet: "
                f"{timeOffSet}\n\t\t\tdata: {data}"+("\n\t\t\ttimeOffSetValue: %06u" % timeOffSetValue))
            get_message(data, stringAddress)
            check_crc8(page[offset:offset + size])
        offset += size


def sync_log(page):
    sync_size = page[1]
    sync_stringAddr = page[2:6]
    sync_timestamp = page[6:10]
    sync_timestam_value = count_bytes(sync_timestamp)
    print(
        f'SyncFrame\n\tcrc8: {page[0]}\n\tsize: {sync_size}\n\tsync_stringaddr: {sync_stringAddr}\n\tsync_timestamp: {sync_timestamp}'
    + ("\n\tsync_timestam_value: %010u" % sync_timestam_value))
    check_crc8(page[:10])


with open('../input.bin', 'rb') as f:
    c = [i for i in f.read()]
    for i in range(len(c) // 512):
        sync_log(c[512 * i:512 * (i + 1)])
        messages_log(c[512 * i:512 * (i + 1)])
