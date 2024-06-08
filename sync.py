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
    js = get_json(args.json_file)
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
            formated_message = get_message(data, stringAddress, timeOffSetValue, stv)
            if formated_message == 0:
                print(("Error: %010u.%06u " % (stv, timeOffSetValue))+f"message: n/a; StringAddressValue: "
                                                                      f"{count_bytes(stringAddress)} data: "
                                                                      f"{data}", file=sys.stderr)
                break  # move to the next page
            else:
                print(("%010u.%06u " % (stv, timeOffSetValue))+formated_message, file=sys.stdout)
        offset += size


def sync_log(page):
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
    args = parser.parse_args()
    bin_bytes = [int(i) for i in "21 10 0 0 0 0 86 177 69 102 86 23 0 0 52 1 131 123 4 0 4 0 52 1 4 0 52 1 65 65 65 65 65".split()]
    if len(bin_bytes) < 512:
        sync_log(bin_bytes)
    else:
        for i in range(len(bin_bytes) // 512):
            print(f"Page {i+1} reading...", file=sys.stdout)
            sync_log(bin_bytes[512 * i:512 * (i + 1)])
