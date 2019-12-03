#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

from telnetlib import Telnet
import requests

def telnet_this(ip):
    print("telnet", ip)

def weather_forecast():
    s_city = "Petersburg,RU"
    city_id = 0
    appid = "буквенно-цифровой APPID"
    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/find",
                           params={'q': s_city, 'type': 'like', 'units': 'metric', 'APPID': appid})
        data = res.json()
        cities = ["{} ({})".format(d['name'], d['sys']['country'])
                  for d in data['list']]
        print("city:", cities)
        city_id = data['list'][0]['id']
        print('city_id=', city_id)
    except Exception as e:
        print("Exception (find):", e)
        pass

    try:
        res = requests.get("http://api.openweathermap.org/data/2.5/weather",
                           params={'id': city_id, 'units': 'metric', 'lang': 'ru', 'APPID': appid})
        data = res.json()
        print("conditions:", data['weather'][0]['description'])
        print("temp:", data['main']['temp'])
        print("temp_min:", data['main']['temp_min'])
        print("temp_max:", data['main']['temp_max'])
    except Exception as e:
        print("Exception (weather):", e)
        pass


if __name__ == '__main__':
    # telnet_this("192.168.86.84")
    # tel_open = Telnet("192.168.86.")
    weather_forecast()
