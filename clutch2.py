#!/usr/bin/python3.6
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import codecs
import random
import getpass
import pyperclip
import http.client
import urllib.error
import urllib.request
import multiprocessing
import multiprocessing.dummy

from pysnmp.hlapi import *
from abc import ABC
from html.parser import HTMLParser

try:
    import colorama
    colorama.init()

except ModuleNotFoundError:
    pass

PROGRAM_VERSION = '4.0.3 master'

symbol_good = "\x1b[92m[+]\x1b[0m"
symbol_bad = "\x1b[91m[!]\x1b[0m"
symbol_log = "\x1b[94m[>]\x1b[0m"
symbol_unknown = "\x1b[90m[~]\x1b[0m"
symbol_question = "\x1b[93m[?]\x1b[0m"
global_log_path = "/var/log/clutch/clutch.log"
local_log_path = "/home/%s/clutch.log" % getpass.getuser()

horizontal_dash_line = "-" * 92
horizontal_equal_line = "=" * 92
horizontal_help_line = symbol_question + " " + "\x1b[93m-\x1b[0m" * 84 + " " + symbol_question
plus_line_for_table = "-" * 9 + "+" + "-" * 7 + "+" + "-" * 5 + "+" + "-" * 18 + "+" + "-" * 49
plus_line_for_search = "-" * 9 + "+" + "-" * 5 + "+" + "-" * 17 + "+" + "-" * 58


def help_and_about():
    help_string = '''clutch [ФАЙЛ]... [ПАРАМЕТРЫ]... 

Параметры:
        clutch file.txt номер       быстрое подключение к устройству по его порядковому номеру в списке

    -f, --find                      поиск устройства по названию
        clutch [ФАЙЛ] -f            вывод таблицы и поиск
        clutch [ФАЙЛ] -f [ИМЯ/IP]   быстрый поиск без вывода таблицы

    -s, --ssh                       быстрое подключение SSH по выбранному номеру
        clutch [ФАЙЛ] -s [НОМЕР]    

    -t, --table                     показать таблицу с устройствами и выйти
        clutch [ФАЙЛ] -t

    -w, --write                     добавить новую запись в файл
        clutch [ФАЙЛ] -w            запись в существующий файл

    -F, --flush                     очистка файла от пустых строк
        clutch [ФАЙЛ] -F

    -h, --help                      показать эту справку и выйти
    -v, --version                   показать информацию о версии и выйти

При подключении логин и пароль будут копироваться в буфер обмена автоматически (модуль pyperclip).
Если подключение по ssh - для работы буфера обмена необходим проброс X11.

Пример быстрого поиска: \x1b[36mclutch2 cisco.txt -f my_cisco\x1b[0m

В таблице столбец с названием L P E означает наличие или отсутствие в файле соответственно:
    L   - логина
    P   - пароля
    E   - пароля в enable режим

Общая информация:
Для логгирования в общий файл необходимо создать папку в /var/log/clutch/ и выдать ей права 
на изменение всеми пользователями
Для проверки логина PPPoE в директории /usr/bin/clutch/ должен лежать файл llink с двумя
строками (начало и хвост ссылки для проверки на BRM)

Файл *.txt должен иметь содержание следующего характера (минимум одна строка): 
IP адрес | Название устройства | Логин | Пароль | Пароль для привилегированного режима (опционально)

Если необходимо создать подключение SSH, вместо пароля на enable указывается номер порта:
IP адрес | Название устройства | Логин | Пароль | port=[НОМЕР]

Файл должен иметь расширение .txt
В конце файла необходимо оставлять одну пустую строку
Рекомендуется после внесения изменений в файл использовать встроенное средство очистки (flush)
Каждый блок в файле должен начинаться с новой строки и разделяться вертикальной чертой (text | text)
Если файл отсутствует будет предложно создать новый файл-образец
'''

    version_string = '''
    MIT License

    Copyright (c) %s citizen0ne

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE. 

    Clutch2 (Linux Networking) %s
    ''' % (2019, PROGRAM_VERSION)

    help_string_for_cycle = '''%s
                         h : Вызвать справку (это сообщение)
                         v : Информация о версии программы
                         w : Добавить новую строку в файл
                        ls : Показать список файлов в директории с программой
                       log : Просмотр лога
                      flog : Просмотр лога в режиме мониторинга
                     flush : Очистка файла от пустых строк
                      exit : Выход
                            
                    [номер]       : Подключение Telnet
                  s [номер]       : Подключение SSH
                  p [номер]       : Ping устройства из таблицы
                  i [номер]       : Проверка snmp трапов inity
                  f [имя/IP]      : Быстрый поиск
                  l [логин/файл]  : Проверка абонентского логина (можно указать файл)
                  m [mac-address] : Поиск вендора по mac-адресу
                cat [файл]        : Просмотр содержимого файла
             telnet [адрес/имя]   : Ручной ввод ip адреса (если адреса нет в списке)
               ping [адрес/имя]   : Проверка доступности хоста
         traceroute [адрес/имя]   : Трассировка маршрута до узла
%s''' % (horizontal_help_line, horizontal_help_line)

    return [help_string, version_string, help_string_for_cycle]


def dev_list(file_name):
    if os.path.exists(file_name):  # Если файл существует - открываем и читаем его
        with open(file_name, 'r') as file_read:
            file_line = file_read.read().splitlines()
        return file_line

    else:
        no_file = input("%s Файл %s перемещен или удален! Создать новый? [y/n]: " % (symbol_question, file_name))

        if no_file == 'y':
            with open(file_name, 'w+') as new_file:
                new_file.write('192.168.1.1 | test_1 | login \n'
                               '192.168.1.2 | test_2 | login | password \n'
                               '192.168.1.3 | test_3 | login | password | enable\n'
                               '192.168.1.4 | test_4_ssh | login | password | port=22\n\n')
            logging("Создание нового файла: \"%s\"" % file_name)

            return dev_list(file_name)  # Рекурсия для повторного чтения если файла не было в начале

        else:
            exit(0)


def ip_address_enum(file_name):
    for line in range(len(dev_list(file_name))):
        time.sleep(0.1)
        color = random.randint(31, 47)
        sys.stdout.write("\r\x1b[%sm[❤] %s\x1b[0m   " % (color, dev_list(file_name)[line].split(' | ')[0]))

    print("\r%s Be cool!         \n>>> " % symbol_good, end='')


def write_file(string_to_write, file_name):  # Добавление строки в файл
    try:
        with open(file_name, 'a') as w_file:
            w_file.write(string_to_write)
        flush(file_name)
        print("%s Запись успешно добавлена!" % symbol_good)

        logging("Запись в файл: \"%s\" -> \"%s\"" % (string_to_write, file_name))

    except PermissionError:
        print('%s Нет прав или файл защищен от записи!' % symbol_bad)
        logging("Нет прав на изменение файла: \"%s\" ->| \"%s\"" % (string_to_write, file_name))


def check_file_string(number, file_name):  # проверка правильности строки
    len_dev_list = dev_list(file_name)[number].split(' | ')

    ip = len_dev_list[0]
    name = len_dev_list[1]
    login = '-'
    password = '-'
    enable = '-'

    if len(len_dev_list) == 1:  # Если есть только ip адрес
        ip = len_dev_list[0]

    elif len(len_dev_list) == 2:  # ip адрес + имя
        ip = len_dev_list[0]
        name = len_dev_list[1]

    elif len(len_dev_list) == 3:  # ip, имя, логин и т.д
        login = len_dev_list[2]

    elif len(len_dev_list) == 4:
        login = len_dev_list[2]
        password = len_dev_list[3]

    elif len(len_dev_list) == 5:
        login = len_dev_list[2]
        password = len_dev_list[3]
        enable = len_dev_list[4]

    return [ip, name, login, password, enable]  # Возвращаем список


def flush(file_name):  # Очистка файла от пустых строк
    with open(file_name, 'r') as in_file:  # Открываем одновременно 2 файла: первый на чтение...
        with open('tmp.txt', 'w') as out_file:  # ...и второй, временный tmp.txt, на запись.
            line_in_file = in_file.read().splitlines()

            for i in range(len(line_in_file)):  # Читаем исходный файл...
                ip = line_in_file[i].split(' | ')[0].split('.')

                if len(ip) < 4:  # ...и если длинна ip адреса меньше положенной...
                    out_file.write('')  # ...записываем в новый файл пустую строку

                elif line_in_file[i] != '':  # И если в исходном файле строка не пустая...
                    out_file.write(line_in_file[i] + '\n')  # ...записываем её в новый файл.

    with open('tmp.txt', 'a') as last_line:  # Это для добавления одной пустой строки в конец файла
        last_line.write('\n')

    os.system('rm %s' % file_name)  # Чтобы не заморачиваться - удаляем исходный файл...
    os.system('mv tmp.txt %s' % file_name)  # ...и тут же переименовываем временный, присваивая название старого файла.


def table(file_name):  # Отрисовка таблицы
    ip_start = '\x1b[33m'
    ip_end = '\x1b[0m'
    blue_start = '\x1b[36m'
    blue_end = '\x1b[0m'

    print(horizontal_dash_line)
    print(" Номер   | L P E | SSH | \x1b[36mIP-адрес\x1b[0m         | \x1b[33mНазвание\x1b[0m")
    print(plus_line_for_table)

    for i in range(len(dev_list(file_name)) - 1):
        try:
            len_dev_list = dev_list(file_name)[i].split(' | ')  # Целая строка из файла
            spaces_1 = (4 - len(str(i + 1))) * ' '  # Пробелы после номера устройства
            spaces_2 = (15 - len(len_dev_list[0])) * ' '  # Пробелы после ip адреса

            # парсинг ip адреса для проверки на числа
            splitted_ip = dev_list(file_name)[i].split(' | ')[0].split('.')

            # Преобразование строки для красивого вывода
            ip = blue_start + check_file_string(i, file_name)[0] + blue_end
            name = ip_start + check_file_string(i, file_name)[1] + ip_end
            login = check_file_string(i, file_name)[2]
            password = check_file_string(i, file_name)[3]
            enable = check_file_string(i, file_name)[4]

            # Если перед enable в файле стоит 'port='
            ssh = enable[5:] if enable[0:5] == 'port=' else enable  # присваиваем номер порта ssh

            # Отображение наличия или отсутствия логина/пароля/enable
            login_check_t = '-' if login == '-' else '+'
            password_check = '-' if password == '-' else '+'
            enable_check = '-' if enable == '-' else '+'

            # проверка ssh или telnet, строку в кавычках после else можно заменить любые 3 символа
            if ssh.isdigit():
                ssh_check = '\x1b[32m + \x1b[0m'

            else:
                ssh_check = '\x1b[31m - \x1b[0m'

            # Проверка правильности ip адреса
            if splitted_ip[0].isdigit() \
                    and splitted_ip[1].isdigit() \
                    and splitted_ip[2].isdigit() \
                    and splitted_ip[3].isdigit() \
                    and len(splitted_ip) == 4:

                # Поднимаем флаг если ip адрес указан верно
                flag = True

            else:
                flag = False

            if flag is True:  # Если ip адрес верен - печатаем строку в нормальном виде
                print("  ", i + 1, spaces_1, "|", login_check_t, password_check, enable_check, "|",
                      ssh_check, "|", ip, spaces_2, "|", name)

            else:  # Если нет - ошибку адреса
                print()

        except IndexError:  # Если что-то пошло не так
            print()

    print(horizontal_dash_line)


def search_device(searching_string, file_name):  # Поиск устройства
    list_of_devices_found = []

    for dev in range(len(dev_list(file_name))):
        try:
            dev_num = dev + 1
            ip_address = dev_list(file_name)[dev].split(' | ')[0]
            name = dev_list(file_name)[dev].split(' | ')[1]
            ssh_check = '  \x1b[31m-\x1b[0m  |'
            spaces_1 = (6 - len(str(dev_num))) * ' ' + '|'
            spaces_2 = (16 - len(ip_address)) * ' ' + '|'

            if searching_string.lower() in name.lower() or searching_string in ip_address:
                search_res = "\x1b[1;92m%s\x1b[0m" % searching_string.lower()

                new_name = name.lower().replace(searching_string.lower(), search_res)
                new_ip = ip_address.replace(searching_string.lower(), search_res)

                if len(dev_list(file_name)[dev].split(' | ')) == 5:
                    ssh_test = dev_list(file_name)[dev].split(' | ')[4][0:5]
                    ssh_test_num = dev_list(file_name)[dev].split(' | ')[4][5:]

                    if ssh_test == 'port=' and ssh_test_num.isdigit():
                        ssh_check = '  \x1b[32m+\x1b[0m  |'

                else:
                    ssh_check = '  \x1b[31m-\x1b[0m  |'  # Если нет ssh (порт не найден)

                coincidence = '   %s%s%s %s%s  %s' % (dev_num, spaces_1, ssh_check, new_ip, spaces_2, new_name)

                list_of_devices_found.append(coincidence)

            else:  # Если ничего не найдено
                pass

        except IndexError:
            continue

    if len(list_of_devices_found) != 0:
        os.system("clear")
        print("%s Поиск: \"%s\" в \"%s\":" % (symbol_good, searching_string, file_name))
        print(horizontal_dash_line)
        print(' Номер   | SSH | \x1b[36mIP-адрес\x1b[0m        |  \x1b[33mНазвание\x1b[0m\n' + plus_line_for_search)

        for i in list_of_devices_found:
            print(i)

        print(horizontal_dash_line)
        logging("Поиск: \"%s\" в \"%s\"" % (searching_string, file_name))

    else:
        print(horizontal_dash_line)
        print("%s [%s] отсутствует в списке!" % (symbol_bad, searching_string))
        print(horizontal_dash_line)
        logging("Поиск: \"%s\" в \"%s\"" % (searching_string, file_name))


def telnet_or_ssh_this(num_in, file_name, ssh=False):  # Для подключения к устройству
    print(horizontal_equal_line)
    try:
        num = int(num_in)  # Порядковый номер устройства в списке
        l_p_e = list()  # Список логин/пароль/enable

        ip_address = check_file_string(num - 1, file_name)[0]
        name_of_device = check_file_string(num - 1, file_name)[1]
        login = check_file_string(num - 1, file_name)[2]
        password = check_file_string(num - 1, file_name)[3]
        enable = check_file_string(num - 1, file_name)[4]

        green_string_start = '\x1b[32m'
        hidden_string_start = '\x1b[8m'
        string_end = '\x1b[0m'

        # Проверка наличия или отсутствия логина, пароля и enable:
        if 0 < num < len(dev_list(file_name)):
            if enable == '-':
                pass

            if enable == '-' and not ssh:  # Если нет enable:
                l_p_e.append(login)
                l_p_e.append(password)

                try:
                    # Копируем в буфер обмена логин и пароль
                    pyperclip.copy('%s\n%s\n' % (login, password))

                except pyperclip.PyperclipException:
                    print("%s Буфер обмена не задействован! " % symbol_bad, end='\r')
                    pass

                # Формируем блок вывода для подключения к устройству
                ready_string = green_string_start + 'Login/Password/Enable:\n' \
                               + '-' * 22 + '\n' + string_end + hidden_string_start \
                               + login + '\n' + password + '\n' + '\x1b[0m' \
                               + green_string_start + '-' * 22 + string_end

                print(ready_string)

            else:  # Если enable есть:
                if not ssh:  # Это для отказа от вывода строки коприрования при SSH подключении
                    l_p_e.append(login)
                    l_p_e.append(password)
                    l_p_e.append(enable)

                    try:
                        # Копируем в буфер обмена логин пароль и enable
                        pyperclip.copy('%s\n%s\nenable\n%s\n' % (login, password, enable))

                    except pyperclip.PyperclipException:
                        print('%s Буфер обмена не задействован!' % symbol_bad)
                        pass

                    # Формируем блок вывода для подключения к устройству
                    ready_string = '\n' + green_string_start \
                                   + 'Login/Password/Enable:\n' \
                                   + '-' * 22 + '\n' + string_end \
                                   + hidden_string_start + login \
                                   + '\n' + password + '\nenable\n' \
                                   + enable + '\n' + string_end \
                                   + green_string_start \
                                   + '-' * 22 + string_end
                    print(ready_string)

            if ssh:
                print(horizontal_equal_line)
                logging("Соединение SSH: \"%s %s\" ОТКРЫТО" % (ip_address, name_of_device))
                if len(dev_list(file_name)[num - 1].split(' | ')) == 5:
                    if ((dev_list(file_name)[num - 1].split(' | ')[4][5:]).isdigit()) \
                            and (dev_list(file_name)[num - 1].split(' | ')[4][0:5]) == 'port=':

                        ssh_port = dev_list(file_name)[num - 1].split(' | ')[4][5:]

                        if login != '-' and password != '-':
                            print(horizontal_equal_line)
                            print('%s ssh %s@%s -p %s\n' % (symbol_good, login, ip_address, ssh_port))
                            os.system('ssh %s@%s -p %s' % (login, ip_address, ssh_port))

                    elif not dev_list(file_name)[num - 1].split(' | ')[4][5:].isdigit():
                        pass
                logging("Соединение SSH: \"%s %s\" ЗАКРЫТО" % (ip_address, name_of_device))

            elif not ssh:  # Если Telnet
                print(horizontal_equal_line)
                logging("Соединение Telnet: \"%s %s\" ОТКРЫТО" % (ip_address, name_of_device))
                os.system('telnet %s' % ip_address)
                logging("Соединение Telnet: \"%s %s\" ЗАКРЫТО" % (ip_address, name_of_device))

        else:
            print('%s Номера \'%s\' нет в списке!' % (symbol_bad, num))

    except IndexError:
        print('%s Номера \'%s\' нет в списке!' % (symbol_bad, num_in))

    except ValueError:
        print('%s Номера \'%s\' нет в списке!' % (symbol_bad, num_in))
    print(horizontal_equal_line)


def date_to_num(day='', month='', year='', time_c=''):
    list_months = ["Jan", "Feb", "Mar",
                   "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep",
                   "Oct", "Nov", "Dec"]

    month_to_num = list_months.index(month) + 1
    new_day = "0" + day if len(str(day)) < 2 else day
    new_month = "0" + str(month_to_num) if len(str(month_to_num)) < 2 else month_to_num

    return "%s.%s.%s %s" % (new_day, new_month, year, time_c)


def max_num(connection_speeds):
    max_speed = 0
    k_m_speed = ''

    for sp in range(len(connection_speeds)):
        if connection_speeds[sp][:-1].isdigit() and int(connection_speeds[sp][:-1]) >= int(max_speed):
            max_speed = connection_speeds[sp][:-1]
            k_m_speed = connection_speeds[sp][-1]

    return "%s %sбит/с" % (max_speed, k_m_speed)


def login_check(login):
    ip_address = []  # ip адрес сессии
    nas_port_id = []  # Откуда выходит карточка (DSL, GPON, FTTx)
    list_of_auth = []  # Для парсинга попыток авторизации
    login_attemps = []  # Для вывода попыток авторизации
    session_states = []  # Состояние сессий
    connection_speed = []  # Скорость соединения
    file_with_link = "/usr/local/clutch/llink"  # Путь у файлу с ссылкой для проверки логина

    print("%s\n%s Проверяю логин \033[90m%s\x1b[0m, ждите..." %
          (horizontal_equal_line, symbol_unknown, login), end='\r')

    # Обе части ссылки для проверки логина берем из файла
    # Жесткая привязка к пути
    if os.path.isfile(file_with_link):
        with open(file_with_link, "r") as f:
            url_file = f.read().splitlines()

        # Делаем ссылку для проверки
        url = url_file[0] + str(login) + url_file[1]
        result = urllib.request.urlopen(url).read().decode("utf-8")
        html_split = str(result).split('\n')

        # Для удаления HTML тэгов
        class MyParser(HTMLParser, ABC):
            def handle_data(self, data):
                list_of_auth.append(data)

        parse_auth = MyParser()
        login_good_for_print = "\033[92m" + login + "\033[0m"
        login_unknown_for_print = "\033[90m" + login + "\033[0m"

        if "Session state : active" in result:
            print("%s Проверка логина     : %s" % (symbol_good, login_good_for_print) + " " * 10)
        else:
            print("%s Проверка логина     : %s" % (symbol_unknown, login_unknown_for_print) + " " * 10)

        # Парсинг данных
        for line in range(len(html_split)):
            if "SPEED" in html_split[line]:  # Скорость сессии
                connection_speed.append(html_split[line].split(" : ")[1])

            if "Session state" in html_split[line]:  # Активна сессия или нет
                session_states.append(html_split[line].split(" : ")[1])

            if "Auth: Login" in html_split[line]:  # Список попыток авторизации в чистом виде
                parse_auth.feed(html_split[line])

            if "Framed-IP-address :" in html_split[line]:  # Список IP адресов
                ip_address.append(html_split[line].split(" : ")[1])

            if "NAS-Port-Id" in html_split[line]:  # Откуда карточка вышла в интернет
                nas_port_id.append(html_split[line][12:].split("#")[1])

    else:
        print(horizontal_equal_line)
        print("%s Файл \"llink\" не найден! \"/usr/local/clutch/llink\"" % symbol_bad)

    # Проверка и вывод количества попыток авторизации и правильности введенного пароля
    for attempt in range(len(list_of_auth)):
        if "Login OK:" in list_of_auth[attempt] or "Login incorrect" in list_of_auth[attempt]:
            day = str(list_of_auth[attempt][:41]).split(" ")[3]
            month = str(list_of_auth[attempt][:41]).split(" ")[1]
            year = str(list_of_auth[attempt][:41]).split(" ")[5]
            clock = str(list_of_auth[attempt][:41]).split(" ")[4]
            port = str(list_of_auth[attempt]).split('port')[1][:-1]

            if "Login OK:" in list_of_auth[attempt]:
                login_attemps.append("%s %s : Авторизация : \x1b[92mPASS\x1b[0m [%+2s ] : Порт :\33[92m%s\33[0m" %
                                     (symbol_good,
                                      date_to_num(day, month, year, clock),
                                      attempt - 1, port))

            elif "Login incorrect" in list_of_auth[attempt]:
                login_attemps.append("%s %s : Авторизация : \x1b[91mFAIL\x1b[0m [%+2s ] : Порт :\33[91m%s\33[0m" %
                                     (symbol_bad,
                                      date_to_num(day, month, year, clock),
                                      attempt - 1, port))

    # Проверка и вывод статуса сессии
    if "active" in session_states and int(max_num(connection_speed)[:-6]) > 0:
        print("%s Статус сессии       :\x1b[32m Активна\x1b[0m" % symbol_good)
        session_flag = 1

    else:
        print("%s Статус сессии       :\x1b[90m Неактивна\x1b[0m" % symbol_unknown)
        session_flag = 0

    # Проверка и вывод абонентского порта (Добавить определение DSLAM и OLT)
    if len(nas_port_id) != 0 and nas_port_id[0] != '':
        print("%s Абонентский порт    : \x1b[32m%s\x1b[0m" % (symbol_good, nas_port_id[0]))

    else:
        print("%s Абонентский порт    : \x1b[90m~\x1b[0m" % symbol_unknown)

    # Проверка и вывод IP адреса
    if len(ip_address) != 0:
        print("%s Полученный IP-адрес : \x1b[32m%s\x1b[0m" % (symbol_good, ip_address[0]))
    else:
        print("%s Полученный IP-адрес : \x1b[90m~\x1b[0m" % symbol_unknown)

    # Проверка и вывод скорости соединения
    if int(max_num(connection_speed)[:-6]) != 0:
        print("%s Скорость соединения : \x1b[32m%s\x1b[0m" %
              (symbol_good, max_num(connection_speed)))

    else:
        print("%s Скорость соединения : \x1b[90m%s\x1b[0m" %
              (symbol_unknown, max_num(connection_speed)))

    # Количество попыток авторизации
    if len(login_attemps) > 0:
        print("%s Попытки авторизации : \x1b[32m%s\x1b[0m" %
              (symbol_good, len(login_attemps)))
        print(horizontal_dash_line)

        # Вывод всех попыток авторизации
        for attempt in range(len(login_attemps)):
            print(login_attemps[attempt])

        print(horizontal_equal_line)

    elif len(login_attemps) == 0 and session_flag:
        print("%s Попытки авторизации : \x1b[90m~\x1b[0m" % symbol_unknown)
        print(horizontal_equal_line)

    else:
        print("%s Попытки авторизации : \x1b[90m0\x1b[0m" % symbol_unknown)
        print(horizontal_equal_line)


def login_check_file_login(check_input):
    if str(check_input).isdigit() and len(str(check_input)) == 11:
        try:
            login_check(check_input)
            logging("Проверка логина PPPoE: %s" % check_input)

        except http.client.error:  # В основном эта проверка нужна для исключения ошибки с нулевым логином
            print("%s Логин введен некорректно!" % symbol_bad + ' ' * 20)
            print(horizontal_equal_line)

        except urllib.error.HTTPError:
            print("%s Логин введен некорректно!" % symbol_bad + ' ' * 20)
            print(horizontal_equal_line)

    elif str(check_input).isdigit() and (len(str(check_input)) > 11 or len(str(check_input)) <= 10):
        print("%s Логин должен состоять из 11 символов!" % symbol_bad)

    else:
        try:
            with open(check_input, "r") as file:
                logins_from_file = file.read().splitlines()

            for login in logins_from_file:
                if login != '':
                    login_check(login)
                    logging("Проверка логина PPPoE: %s" % login)
                    print()

                else:
                    print(horizontal_equal_line)
                    print("%s Логин [%s] отсутствует или введен некорректно!" % (symbol_bad, login))
                    print(horizontal_equal_line)
                    logging("Проверка логина PPPoE: %s" % login)
                    # continue

        except FileNotFoundError:
            logging("Файл \"%s\" с логинами PPPoE не найден!" % check_input)
            print(horizontal_equal_line)
            print("%s Файл \"%s\" не найден!" % (symbol_bad, check_input))


def mac_check(mac):
    # Поиск вендора через api
    print(horizontal_equal_line)
    try:
        url = "http://macvendors.co/api/"
        request = urllib.request.Request(url + mac, headers={'User-Agent': "API Browser"})
        response = urllib.request.urlopen(request)

        reader = codecs.getreader("utf-8")
        obj = json.load(reader(response))

        print("%s Производитель оборудования      : %s" % (symbol_good, obj['result']['company']))
        print("%s Юридический адрес производителя : %s" % (symbol_good, obj['result']['address']))
        print(horizontal_equal_line)

    except KeyError:
        print("%s MAC-адрес указан неверно!" % symbol_bad)

    except urllib.error.URLError:
        print("%s www.macvendors.co недоступен!" % symbol_bad)

    # print(horizontal_equal_line)
    logging("Проверка MAC-адреса: %s" % mac)


def logging(text='', read=False):
    # Логгирование действий в файл
    if not read:  # флаг на запись в файл
        log_string = "[%s] @%s: %s\n" % (time.strftime("%H:%M:%S %d-%m-%Y"), getpass.getuser(), text)
        try:
            log_file = open(global_log_path, "a+")
            # print("%s /var/log/clutch/clutch.log" % symbol_log)

        except PermissionError:  # если нет доступа к папке /var/log/clutch/
            log_file = open(local_log_path, "a+")
            # print("%s /home/%s/clutch.log" % (symbol_log, getpass.getuser()))

        log_file.writelines(log_string)
        log_file.close()

    elif read:
        if os.path.exists(global_log_path):
            # print("%s log: /var/log/clutch/clutch.log" % symbol_log)
            os.system("cat -n %s" % global_log_path)

        elif os.path.exists(local_log_path):
            # print(symbol_log + " log: " + os.getcwd() + "/clutch.log")
            os.system("cat -n %s" % local_log_path)

        else:
            print("%s Лог файл не найден!" % symbol_bad)


def main():
    help_me = help_and_about()[0]
    version = help_and_about()[1]
    help_cycle = help_and_about()[2]

    while True:
        if len(sys.argv) == 1:  # если аргумент 1
            print("Usage: clutch [FILE]")
            print("Usage: clutch [FILE] [-f find] [-s SSH] [-t table] [-w write] [-F flush]")
            print('\n-h, --help  справка')
            print('-v, --version  версия\n')
            break

        elif len(sys.argv) == 2:  # если аргументов 2 (понеслась жара)
            if sys.argv[1] == '-h' or sys.argv[1] == '--help':
                print(help_me)
                break

            elif sys.argv[1] == '-v' or sys.argv[1] == '--version':
                print(version)
                break

            else:
                if str(sys.argv[1]).split('.')[1] == 'txt':
                    os.system('clear')
                    table(sys.argv[1])
                    find_some = ''
                    my_device = ''

                    try:
                        my_device = input('>>> ')
                        find_some = my_device

                    except UnicodeDecodeError:
                        logging("UnicodeDecodeError")

                    # Интерактивное управление в теле программы
                    if find_some == 'exit':  # Выход из программы
                        break

                    elif find_some == 'h':  # Вызов справки
                        print(help_cycle)

                    elif find_some == 'v':  # Версия
                        print(version)

                    # Очистка файла
                    elif find_some == 'flush':
                        are_you_sure = input('%s Удалить пустые и некорректные строк? [y/n]: ' % symbol_question)
                        if are_you_sure == 'y':
                            flush(sys.argv[1])
                            print('%s Файл очищен!' % symbol_good)
                            logging("Удаление пустых и некорректных строк из файла: \"%s/%s\""
                                    % (os.getcwd(), sys.argv[1]))

                    # Запись новой строки в файл
                    elif find_some == 'w':
                        print(horizontal_equal_line)
                        print("%s Введи строку для сохранения в файл, (разделитель пайп \"|\") в формате"
                              % symbol_question)

                        print("%s IP-адрес | название | логин | пароль | пароль enable или номер порта ssh (port=22)"
                              % symbol_question)

                        write_string = input("\x1b[93m>>> \x1b[0m")

                        if write_string != '' and ' | ' in write_string:
                            write_file(write_string, sys.argv[1])

                        else:
                            print("%s Пустые или ошибочные записи не добавляются!" % symbol_bad)
                            logging("Попытка добавить некорректную строку: \"%s\" -> \"%s\""
                                    % (write_string, sys.argv[1]))

                        print(horizontal_equal_line)

                    elif len(find_some.split(' ')) == 2 and find_some.split(' ')[0] == 'cat':
                        print(horizontal_equal_line)
                        logging("Просмотр файла: \"%s\"" % find_some.split(' ')[1])
                        os.system("cat -n %s" % find_some.split(' ')[1])

                    # SSH
                    elif find_some.split(' ')[0] == 's':
                        try:
                            num_of_device = find_some.split(' ')[1]
                            telnet_or_ssh_this(num_of_device, sys.argv[1], True)
                            continue

                        except IndexError:
                            print(help_cycle)

                    # Проверка SNMP трапов для inity
                    elif find_some.split(' ')[0] == 'i':
                        try:
                            num_of_device = int(find_some.split(' ')[1]) - 1
                            ip_address = check_file_string(num_of_device, sys.argv[1])[0]
                            name_of_device = check_file_string(num_of_device, sys.argv[1])[1]

                            print('%s snmpwalk -v 2c -c inity2016 %s' % (symbol_good, ip_address))
                            logging("Проверка SNMP: \"%s %s\"" % (ip_address, name_of_device))

                            os.system('snmpwalk -v 2c -c inity2016 %s' % ip_address)
                            continue

                        except IndexError:
                            print(help_cycle)

                        except ValueError:
                            print(help_cycle)

                    # Проверка ping
                    elif find_some.split(' ')[0] == 'p':
                        try:
                            num_of_device = int(find_some.split(' ')[1]) - 1
                            ip_address = check_file_string(num_of_device, sys.argv[1])[0]
                            name_of_device = check_file_string(num_of_device, sys.argv[1])[1]

                            logging("Проверка ping устройства: \"%s %s\"" % (ip_address, name_of_device))
                            print(horizontal_equal_line)
                            print('%s ping %s' % (symbol_good, ip_address))
                            os.system('ping %s -i 0.2 | grep time=' % ip_address)

                        except IndexError:
                            print(help_cycle)

                        except ValueError:
                            print(help_cycle)

                    # Если ввели цифру - телнетимся по этому номеру
                    elif find_some.isdigit():
                        telnet_or_ssh_this(my_device, sys.argv[1])
                        continue

                    # Пингуем адрес (ошибки обрабатываются системой)
                    elif find_some.split(' ')[0] == 'ping':
                        logging("Команда ping: \"%s\"" % find_some)
                        print(horizontal_equal_line)
                        os.system(find_some)

                    # Трассировка маршрута
                    elif find_some.split(' ')[0] == 'traceroute':
                        logging("Команда traceroute: \"%s\"" % find_some)
                        print()
                        os.system(find_some)

                    # Быстрый поиск + SSH
                    elif find_some.split(' ')[0] == 'f' and len(find_some) > 2:
                        if len(find_some.split(' ')) >= 2:
                            search_device(find_some.split(' ')[1], sys.argv[1])
                            my_device = input('>>> ')

                            if len(my_device) > 2 and my_device[0] == 's':  # Для SSH
                                try:
                                    num_of_device = my_device.split(' ')[1]
                                    telnet_or_ssh_this(num_of_device, sys.argv[1], True)
                                    continue

                                except IndexError:
                                    print(help_cycle)

                            elif my_device.isdigit():
                                telnet_or_ssh_this(my_device, sys.argv[1])
                                continue

                            else:
                                continue

                        else:
                            print(help_cycle)

                    # Ручной телнет
                    elif find_some.split(' ')[0] == 'telnet':
                        print()
                        os.system(find_some)

                    elif find_some.split(' ')[0] == 'enum':
                        cool = input('%s IP enumerate?: ' % symbol_question)

                        if cool == 'yes':
                            logging("enum")
                            ip_address_enum(sys.argv[1])
                            continue

                        else:
                            print('%s :(' % symbol_bad)

                    # Показать лог
                    elif find_some.split(' ')[0] == 'log':
                        logging(read=True)
                        logging("Просмотр лога")

                    elif find_some.split(' ')[0] == 'flog':
                        logging("Просмотр лога в режиме мониторинга")
                        os.system("tail -f -n 1 %s | nl" % global_log_path)
                        continue

                    # посмотреть содержимое текущей директории
                    elif find_some.split(' ')[0] == 'ls':
                        print(horizontal_equal_line)
                        os.system("ls -alh --color=auto")
                        logging("Просмотр содержимого директории с программой")

                    # Проверка логина
                    elif find_some.split(' ')[0] == 'l' and len(find_some.split(' ')) == 2:
                        login_check_file_login(find_some.split(' ')[1])

                    # Поиск вендора по mac-адресу
                    elif find_some.split(' ')[0] == 'm' and len(find_some.split(' ')) == 2:
                        try:
                            mac = find_some.split(' ')[1]
                            mac_check(mac)

                        except IndexError:
                            print(help_cycle)

                    else:
                        print(help_cycle)

                else:
                    print(help_me)
                    break

        elif len(sys.argv) == 3:  # Если аргументов 3
            if sys.argv[2] == '-f' or sys.argv[2] == '--find':  # Запуск программы в режиме поиска
                os.system('clear')
                name_of_file = sys.argv[1]
                table(name_of_file)

                request = input('%s Поиск: ' % symbol_question)
                if request != '':
                    search_device(request, name_of_file)
                    my_device = input('>>> ')

                    # SSH
                    if my_device != '':
                        if my_device[0] == 's':  # Проверяем, если в начале s - коннектимся по SSH
                            num_of_dev = my_device.split(' ')[1]
                            telnet_or_ssh_this(num_of_dev, name_of_file, True)

                        elif my_device.isdigit():
                            telnet_or_ssh_this(my_device, name_of_file)

                    elif my_device == '':
                        continue

                else:
                    print(help_cycle)

            # Построить таблицу и выйти
            elif sys.argv[2] == '-t' or sys.argv[2] == '--table':
                table(sys.argv[1])
                break

            # Добавить строку в файл и выйти
            elif sys.argv[2] == '-w' or sys.argv[2] == '--write':
                name_of_file = sys.argv[1]

                table(name_of_file)
                print(horizontal_equal_line)
                print("%s Введи строку для сохранения в файл, (разделитель пайп \"|\") в формате"
                      % symbol_question)

                print("%s IP-адрес | название | логин | пароль | пароль enable или номер порта ssh (port=22)"
                      % symbol_question)

                write_string = input('\x1b[93m>>> \x1b[0m')

                # Запись в файл
                if write_string != '' and ' | ' in write_string:
                    write_file(write_string, name_of_file)
                    os.system("clear")
                    table(name_of_file)
                    print("%s Запись успешно добавлена в файл \"%s\"" % (symbol_good, name_of_file))
                    logging("Добавление новой строки в файл: \"%s\"" % name_of_file)
                    break

                else:
                    print("%s Пустые или ошибочные записи не добавляются!\n%s"
                          % (symbol_bad, horizontal_equal_line))
                    break

            elif sys.argv[2] == '-F' or sys.argv[2] == '--flush':
                table(sys.argv[1])

                are_you_sure = input('%s Очистить файл от пустых строк? [y/n]: ' % symbol_question)

                if are_you_sure == 'y' and str(sys.argv[1]).split('.')[1] == 'txt':
                    os.system("clear")
                    flush(sys.argv[1])
                    table(sys.argv[1])
                    print("%s Файл очищен!" % symbol_good)
                    logging("Удаление пустых и некорректных строк из файла \"%s/%s\"" % (os.getcwd(), sys.argv[1]))
                    break

                else:
                    print(help_me)
                    break

            elif sys.argv[1] == '-v' or sys.argv[1] == '--version':
                print(version)
                break

            # Быстрое подключение telnet по номеру в списке
            elif str(sys.argv[1]).split('.')[1] == 'txt':
                try:
                    os.system("clear")
                    number_of_device = int(sys.argv[2])
                    name_of_file = sys.argv[1]
                    telnet_or_ssh_this(number_of_device, name_of_file)
                    break

                except ValueError:
                    print('%s %s нет в списке!' % (symbol_bad, sys.argv[2]))
                    break

            else:
                print(help_me)
                break

        elif len(sys.argv) == 4:  # Если аргументов 4
            name_of_file = sys.argv[1]

            if sys.argv[2] == '-f' or sys.argv[2] == '--find':
                os.system('clear')
                request = sys.argv[3]
                search_device(request, name_of_file)

                my_device = input('>>> ')

                if my_device != '':  # SSH
                    if my_device[0] == 's':  # Проверяем, если в начале s - делаем SSH
                        try:
                            num_of_dev = my_device.split(' ')[1]
                            telnet_or_ssh_this(num_of_dev, name_of_file, True)

                        except IndexError:
                            print(help_cycle)

                    elif my_device == 'exit' or my_device == 'x':
                        break

                    elif my_device.isdigit():  # Telnet
                        telnet_or_ssh_this(my_device, name_of_file)
                        pass

                else:
                    print(help_cycle)

            elif sys.argv[1] == '-v' or sys.argv[1] == '--version':
                print(version)
                break

            # Быстрый SSH
            elif sys.argv[2] == '-s' or sys.argv[2] == '--ssh':
                try:
                    num_of_dev = sys.argv[3]
                    telnet_or_ssh_this(num_of_dev, name_of_file, True)
                    break

                except IndexError:
                    print(help_cycle)

            else:
                print(help_me)
                break

        elif len(sys.argv) > 4:  # Использование не более 4-х аргументов
            print(help_me)
            break

        # print(horizontal_equal_line, end='\r')
        print(symbol_good, end='\r')
        input()


#####################################################################################################
def ping_test(ip):
    ping_result = os.system("ping -w 1 -c 4 -i 0.2 %s > /dev/null" % ip)
    if ping_result == 0:
        print("[\x1b[32m  OK  \x1b[0m] %s   " % ip, end='\r')
        return ip
    else:
        print("[\x1b[31m FAIL \x1b[0m] %s   " % ip, end='\r')
        return None
    # return ip if ping_result == 0 else None  # После отладки восстановить


def multi_process_ping(network="192.168.86", ip_start=1, ip_end=100):
    # В 3.5 раза быстрее обычного пинга
    ip_list_for_ping = []

    for octet in range(ip_start, ip_end):
        ip_list_for_ping.append(network + '.' + str(octet))

    ping_process = multiprocessing.dummy.Pool()
    result = ping_process.map(ping_test, ip_list_for_ping)
    ping_process.close()
    ping_process.join()

    list_of_accessible_ip = [ip for ip in result if ip is not None]

    print("Доступные хосты из диапазона: %s.%s->%s" % (network, ip_start, ip_end))  # Для отладки
    return list_of_accessible_ip  # Возврат списока доступных хостов


# Функции для получения хостнейма в тестовом режиме
def snmp_getcmd(community, ip, port, oid):
    snmp_string = next(getCmd(SnmpEngine(),
                   CommunityData(community),
                   UdpTransportTarget((ip, port)),
                   ContextData(),
                   ObjectType(ObjectIdentity(oid))))
    return snmp_string


def snmp_get_next(community, ip, port, oid):
    errorIndication, errorStatus, errorIndex, varBinds = next(snmp_getcmd(community, ip, port, oid))
    for name, val in varBinds:
        return (val.prettyPrint())
#####################################################################################################


if __name__ == '__main__':
    try:
        main()

    except IndexError:
        print(help_and_about()[0])

    except KeyboardInterrupt:
        print(' ' * 50)

    except EOFError:
        print(' ' * 50)
