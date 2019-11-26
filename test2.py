#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

from telnetlib import Telnet


def telnet_this(ip):
    print("telnet", ip)


if __name__ == '__main__':
    telnet_this("192.168.86.84")
    tel_open = Telnet("192.168.86.")