#!/usr/bin/env python
# coding: utf-8

import os
import re
logdir=os.getcwd()
for file in os.listdir(logdir+"\\Error Folder\\"):
    f = open("Error Folder\\" + file, 'r')
    lines = f.readlines()
