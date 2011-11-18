#!/bin/env python
#-*- coding: utf-8 -*-

import flvlib
import argparse

parser = argparse.ArgumentParser(
        description='Concat flv files')
parser.add_argument('-o','--output', type=str,
        help='output file name for the flv file')
parser.add_argument('files', nargs='+', type=str,
        help='flv files to be concated by order')
args = parser.parse_args()

l = args.files

print l

if not args.output:
    exit(0)
