check = '%d'
value = 4294967295
bin_value = bin(value)[2:]
if check == '%d' and len(bin_value) == 32:
    value -= 1
    abs_rev_bin_value = bin(value)[3:]
    abs_bin_value = ''
    print(abs_rev_bin_value)

    print(abs_rev_bin_value)
    for i in abs_rev_bin_value:
        if i == '0':
            abs_bin_value += '1'
        else:
            abs_bin_value += '0'
    value = -int(abs_bin_value, 2)





