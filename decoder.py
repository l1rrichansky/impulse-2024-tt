import argparse
import json
import re
import sys


def count_bytes(bytes_array):
    value = 0
    for k, j1 in enumerate(bytes_array):
        value += j1 * 256 ** k
    return value


def message_search(value):
    if str(value) in js:
        return js[str(value)]
    else:
        return False


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


def get_message(data, stringaddress, tos, tsv):
    stringaddress_value = count_bytes(stringaddress)
    message = message_search(stringaddress_value)
    variables = {
        '%c': 1, '%s': 4, '%d': 4, '%u': 4, '%x': 4, '%X': 4, '%lld': 8, '%llu': 8
    }
    if not message:
        return 0
    else:
        specifiers, def_specifiers = extract_specifiers(message)
        ofs = 0
        values = []
        for j in specifiers:
            if j in variables:
                try:
                    sliced = data[ofs:ofs + variables[j]]
                    if sliced:
                        if j == '%s':
                            if sliced:
                                value = count_bytes(sliced)
                                word = message_search(value)
                                if word:
                                    values.append(word)
                                else:
                                    values.append('[n/a]')
                        elif j == '%c':
                            values.append(chr(data[ofs]))
                        else:
                            value = count_bytes(data[ofs:ofs + variables[j]])
                            values.append(value)
                        ofs += variables[j]
                    else:
                        break
                except IndexError:
                    break

        if len(values) < len(specifiers):
            print("%010u.%06u Warning: Not enough values in data" % (tsv, tos), file=sys.stderr)
            formatted_output = format_with_defaults(message, tuple(values))
        elif data[ofs:]:
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


def messages_log(page, stv):
    offset = 10
    while offset < 512:
        size = page[offset + 1]
        if size == 0:
            break
        else:
            stringAddress = page[offset + 2:offset + 6]
            timeOffSet = page[offset + 6:offset + 10]
            timeOffSetValue = count_bytes(timeOffSet)
            data = page[offset + 10:offset + 10 + (size - 10)]
            if count_bytes(stringAddress) != 0:
                formated_message = get_message(data, stringAddress, timeOffSetValue, stv)
                if not check_crc8(page[offset:offset+size]):
                    print(("Error: CRC8 check failed. Invalid structure. %010u.%06u " % (stv, timeOffSetValue))+f"message: [n/a]; StringAddressValue: "
                                                                          f"{count_bytes(stringAddress)} data: "
                                                                          f"{data}", file=sys.stderr)
                    if args.breakloop == 1:
                        break  # move to the next page
                    else:
                        pass
                else:
                    print(("%010u.%06u " % (stv, timeOffSetValue))+formated_message, file=sys.stderr)
            else:
                stv = timeOffSetValue  # if SyncFrame structure is found then changing TimeStampValue
                pass
        offset += size


def first_sync_log(page):
    sync_timestamp = page[6:10]
    sync_timestamp_value = count_bytes(sync_timestamp)
    messages_log(page, sync_timestamp_value)


def get_json(name):
    with open(name) as jsf:
        return json.load(jsf)


def get_bin(name):
    with open(name, 'rb') as bf:
        return bf.read()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('binary_file', type=str, help='Path to the binary file')
    parser.add_argument('-m', '--json_file', type=str, required=True, help='Path to the JSON file')
    parser.add_argument('-brl', '--breakloop', type=int, default=1, help='Skip to the next page if error occurred')
    args = parser.parse_args()
    bin_bytes = [i for i in get_bin(args.binary_file)]
    js = get_json(args.json_file)
    for i in range(len(bin_bytes) // 512):
        print(f"Page {i+1} reading...", file=sys.stdout)
        first_sync_log(bin_bytes[512 * i:512 * (i + 1)])
