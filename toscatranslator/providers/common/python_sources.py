import re, logging
import sys

SCALAR_UNIT_DEFAULT = 'B'
SCALAR_UNIT_LIST_B = {'B': 1, 'KB': 2, 'K': 2, 'MB': 3, 'M': 3, 'GB': 4, 'G': 4, 'TB': 5, 'T': 5, 'PB': 6, 'P': 6,
                      'EB': 7, 'E': 7}
SCALAR_UNIT_LIST_IB = {'B': 1, 'KIB': 2, 'KI': 2, 'MIB': 3, 'MI': 3, 'GIB': 4, 'GI': 4, 'TIB': 5, 'TI': 5, 'PIB': 6,
                       'PI': 6, 'EIB': 7, 'EI': 7}
SCALAR_UNIT_LIST_ALL = {'B': 1,
                        'KB': 2, 'K': 2, 'KIB': 2, 'KI': 2,
                        'MB': 3, 'M': 3, 'MIB': 3, 'MI': 3,
                        'GB': 4, 'G': 4, 'GIB': 4, 'GI': 4,
                        'TB': 5, 'T': 5, 'TIB': 5, 'TI': 5,
                        'PB': 6, 'P': 6, 'PIB': 6, 'PI': 6,
                        'EB': 7, 'E': 7, 'EIB': 7, 'EI': 7}


def transform_units(source_value, target_unit=None, is_only_numb=False, is_without_b=False):
    regex = re.compile(r'([0-9.]+)\s*(\w+)')
    result = regex.match(str(source_value)).groups()
    source_value = result[0]
    source_unit = result[1].upper()
    target_value = ''
    if target_unit is not None:
        converted = get_unit_numb(source_value, source_unit, target_unit)
        target_value += str(converted)
    else:
        target_value += source_value
    if is_only_numb:
        return float(target_value)
    if is_without_b:
        target_unit = target_unit[:-1] if target_unit is not None else source_unit[:-1]
    return target_value + ' ' + target_unit


def get_unit_numb(source_value, source_unit, target_unit):
    target_unit_up = target_unit.upper()
    is_bibyte_source = source_unit in SCALAR_UNIT_LIST_IB
    is_bibyte_target = target_unit_up in SCALAR_UNIT_LIST_IB
    ratio = 1
    digit = 1000
    grade = SCALAR_UNIT_LIST_ALL.get(source_unit)
    target_grade = SCALAR_UNIT_LIST_ALL.get(target_unit_up)
    if (target_grade is None):
        logging.error("Unsupported unit \'%s\'" % target_unit)
        sys.exit(1)
        return
    if is_bibyte_source and is_bibyte_target:
        digit = 1024
    if is_bibyte_target and not is_bibyte_source:
        ratio = pow(1000, grade - 1) / pow(1024, grade - 1) if grade == target_grade else 0.9765625
        if grade < target_grade:
            digit = 1024
    elif is_bibyte_source and not is_bibyte_target:
        ratio = pow(1024, grade - 1) / pow(1000, grade - 1) if grade == target_grade else 1.024
        if grade >= target_grade:
            digit = 1024
    target_grade_abs = abs(grade - target_grade)
    if grade > target_grade:
        converted = (float(source_value)
                     * pow(digit, target_grade_abs)) * ratio
    else:
        converted = (float(source_value)
                     / pow(digit, target_grade_abs)) * ratio
    return converted
