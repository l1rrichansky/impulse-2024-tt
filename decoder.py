import json


with open('input.json') as fd:
    a = json.load(fd)


def check_crc8(byte_array):
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


def get_message(data, message):
    print("\033[34m{}\033[0m".format(f"\t\t\tmessage: {message}"))

def messages_log(page):
    offset = 10
    while offset < 512:
        crc8 = page[offset]
        size = page[offset+1]
        stringAddress = page[offset+2:offset+6].copy()
        timeOffSet = page[offset+6:offset+10].copy()
        data = page[offset+10:offset+10+(size-10)].copy()
        print(f"\t\tMessage\n\t\t\tOFFSET: {offset}\n\t\t\tcrc8: {crc8}\n\t\t\tsize: {size}\n\t\t\tstringAddress: {stringAddress}\n\t\t\ttimeOffSet: "
              f"{timeOffSet}\n\t\t\tdata: {data}")
        index = 0
        for k, j in enumerate(stringAddress):
            index += j*256**k
        print(f"\t\t\tindex: {index}")
        try:
            message = a[str(index)]
        except KeyError:
            message = 'n/a'
        print("\033[36m{}\033[0m".format(f"\t\t\tmessage: {message}"))
        get_message(data,message)

        if size == 0:
            print("\033[33m{}\033[0m".format(f"\t\t\tsize = 0; remaining: {page[offset:]}"))
            break
        else:
            sync_frame = page[offset:offset+size].copy()
            received_crc = sync_frame[0]
            data_bytes = sync_frame[1:]
            calculated_crc = check_crc8(data_bytes)
            if calculated_crc == received_crc:
                print("\033[32m{}\033[0m".format("\t\t\tCRC8 check passed."))
            else:
                print("\033[31m{}\033[0m".format(f"\t\t\tCRC8 check failed. Calculated: {calculated_crc}, Received: {received_crc}"))
        offset += size


def page_log(page):
    sync_size = page[1]
    sync_stringAddr = page[2:6]
    sync_timestamp = page[6:10]
    print(f'SyncFrame\n\tcrc8: {page[0]}\n\tsize: {sync_size}\n\tsync_stringaddr: {sync_stringAddr}\n\tsync_timestamp: {sync_timestamp}')


with open('input.bin', 'rb') as f:
    c = [i for i in f.read()]
    for i in range(len(c)//512):
        page_log(c[512*i:512*(i+1)])
        messages_log(c[512 * i:512 * (i + 1)])


