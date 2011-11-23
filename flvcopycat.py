#!/bin/env python
#-*- coding: utf-8 -*-

#Code for Binary Data Read
import struct

class EndOfFile(Exception):
    pass

# UI32
def get_ui32(f):
    try:
        ret = struct.unpack(">I", f.read(4))[0]
    except struct.error:
        raise EndOfFile
    return ret

def make_ui32(num):
    return struct.pack(">I", num)

# SI32 extended
def get_si32_extended(f):
    # The last 8 bits are the high 8 bits of the whole number
    # That's how Adobe likes it. Go figure...
    low_high = f.read(4)
    if len(low_high) < 4:
        raise EndOfFile
    combined = low_high[3] + low_high[:3]
    return struct.unpack(">i", combined)[0]

def make_si32_extended(num):
    ret = struct.pack(">i", num)
    return ret[1:] + ret[0]

# UI24
def get_ui24(f):
    try:
        high, low = struct.unpack(">BH", f.read(3))
    except struct.error:
        raise EndOfFile
    ret = (high << 16) + low
    return ret

def make_ui24(num):
    ret = struct.pack(">I", num)
    return ret[1:]

# UI16
def get_ui16(f):
    try:
        ret = struct.unpack(">H", f.read(2))[0]
    except struct.error:
        raise EndOfFile
    return ret

def make_ui16(num):
    return struct.pack(">H", num)

# SI16
def get_si16(f):
    try:
        ret = struct.unpack(">h", f.read(2))[0]
    except struct.error:
        raise EndOfFile
    return ret

def make_si16(num):
    return struct.pack(">h", num)

# UI8
def get_ui8(f):
    try:
        ret = struct.unpack("B", f.read(1))[0]
    except struct.error:
        raise EndOfFile
    return ret

def make_ui8(num):
    return struct.pack("B", num)

# DOUBLE
def get_double(f):
    data = f.read(8)
    try:
        ret = struct.unpack(">d", data)[0]
    except struct.error:
        raise EndOfFile
    return ret

def make_double(num):
    return struct.pack(">d", num)

#ScriptDataString
def get_sd_string(f):
    size = get_ui16(f)
    return f.read(size)

def make_sd_string(string):
    data = make_ui16(len(string))
    data += string.encode()
    return data

def get_sd_long_string(f):
    size = get_ui32(f)
    return f.read(size)

def make_sd_long_string(string):
    data = make_ui32(len(string))
    data += string.encode()
    return data

#ScriptDataDate
from datetime import datetime
import time

def get_sd_date(f):
    date = get_double(f)
    f.read(2)
    return datetime.fromtimestamp(date)

def make_sd_date(date):
    data = make_double(time.mktime(date.timetuple()))
    data += mk_ui16(8)
    return data

#Code for analyse and join flv file 
import argparse, os
import pprint
import struct
import sys

parser = argparse.ArgumentParser(
        description='Concat flv files')
parser.add_argument('output', type=str,
        help='output file name for the flv file')
parser.add_argument('inputs', nargs='+', type=str,
        help='flv files to be concated by order')
args = parser.parse_args()

output = args.output + ".tmp"
if os.path.exists(output):
    os.remove(output)

#Open output file
fo = open(output, 'wb')

l = args.inputs

fs = []

#Open Input Files & Check File Headers

def get_header(f):
    sign = f.read(3)
    if not str(sign) == 'FLV':
        return {'error':'Unrecognized FLV Header'}
    if get_ui8(f) != 1:
        return {'error':'Unsupported File Version'}
    flags = get_ui8(f)
    if not flags in [5,4,1]:
        return {'error':'Neither Video Nor Audio stream flag is set'}
    return {'signature':sign,
            'offset':get_ui32(f),
            'flags':flags,
            'error':None
            }

header = None
metadata = None

print "Header Check =>",

for i in l:
    fs.append(open(i, 'rb'))
    h = get_header(fs[len(fs)-1])
    #print h
    if not header:
        header = h
    if h['error'] != None:
        print h['error']
        exit(-1)
    if h != header:
        print '%s : video type vary from others' % i
        exit(-1)
    
print "OK!"

#Build FLV Header For Output File
fo.write(header['signature'])
fo.write(make_ui8(1))
fo.write(make_ui8(header['flags']))
fo.write(make_ui32(header['offset']))
#PreviousTagSize 0
fo.write(make_ui32(0))

#Load Metadata From files
import io

class ScriptObject(object):
    def __init__(self, f, size):
        self.data = f.read(size)
        #Parse the metaData
        script = io.BytesIO(self.data)
        if script.read(1) != '\2':
            return
        self.name = get_sd_string(script)
        #print self.name
        if(self.name != r"onMetaData"):
            return
        self.valuetype = get_ui8(script)
        if(self.valuetype != 8):
            return
        string = str(self.data)
        #Metadata the script can be recognized
        self.metadata = {
                'creator'               : None, #Static
                'metadatacreator'       : None, #Static
                'hasKeyframes'          : None, #Static
                'hasVideo'              : None, #Static
                'hasAudio'              : None, #Static
                'hasMetadata'           : None, #Static
                'canSeekToEnd'          : None, #Static
                'duration'              : None, #Sum_Up
                'videosize'             : None, #Sum_Up
                'framerate'             : None, #Static
                'videodatarate'         : None, #Static
                'videocodecid'          : None, #Static
                'width'                 : None, #Static
                'height'                : None, #Static
                'audiosize'             : None, #Sum_Up
                'audiodatarate'         : None, #Static
                'audiocodecid'          : None, #Static
                'audiosamplerate'       : None, #Static
                'audiosamplesize'       : None, #Static
                'stereo'                : None, #Static
                'filesize'              : None, #Final Check
                'datasize'              : None, #Accumulation
                'lasttimestamp'         : None, #Accumulation
                'lastkeyframetimestamp' : None, #Accumulation
                'lastkeyframelocation'  : None  #Accumulation
                }
        funcs = {
                0 : get_double,
                1 : get_ui8,
                2 : get_sd_string,
                3 : None,
                4 : get_sd_string,
                7 : get_ui16,
                8 : None,
                10: None,
                11: get_sd_date,
                12: get_sd_long_string
                }
        for i in self.metadata.keys():
            position = string.find(i)
            if position == -1:
                continue
            position += len(i)
            script.seek(position)
            fieldtype = get_ui8(script)
            func = funcs[fieldtype]
            if callable(func):
                self.metadata[i] = (fieldtype, func(script))
        
        self.metadata['metadatacreator'] = \
            (2,r"FLV CopyCat - by Hanenoshino".encode())

    def generate(self):
        funcs = {
                0 : make_double,
                1 : make_ui8,
                2 : make_sd_string,
                3 : None,
                4 : make_sd_string,
                7 : make_ui16,
                8 : None,
                10: None,
                11: make_sd_date,
                12: make_sd_long_string
                }
        out = io.BytesIO()
        out.write(make_ui8(2)) #Object Type: String
        out.write(make_sd_string("onMetaData")) 
        out.write(make_ui8(8)) #Object Type: ECMA Array
        out.write(make_ui32(len(self.metadata))) #Array Size
        for k,v in self.metadata.items():
            #print k,v[0],v[1]
            out.write(make_sd_string(k))
            out.write(make_ui8(v[0]))
            out.write(funcs[v[0]](v[1]))
        out.write(make_ui24(9)) #End flag for ECMAArray
        out.write(make_ui24(9)) #End flag for DataObject
        out.seek(0)
        self.data = out.read()
        out.close()
        #pprint.PrettyPrinter().pprint(self.metadata)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, so):
        chklst = [
                'hasKeyframes',
                'hasVideo',
                'hasAudio',
                'hasMetadata',
                'canSeekToEnd',
                'framerate',
                'videodatarate',
                'videocodecid',
                'width',
                'height',
                'audiodatarate',
                'audiocodecid',
                'audiosamplerate',
                'audiosamplesize',
                'stereo'
                ]
        for i in chklst:
            if self.metadata[i] != so.metadata[i]:
                print ">>>>>>>%s mismatch.\n%s\n-------\n%s" % \
                        (i,self.metadata[i],so.metadata[i])
                return False
        return True

    def __add__(self, so):
        acculst = {
                'duration'  : 0,
                'videosize' : 0,
                'audiosize' : 0,
                'datasize' : 0,
                }
        for i in acculst:
            self.metadata[i] = (self.metadata[i][0],so.metadata[i][1] + self.metadata[i][1])
        return self

    def write(self, f):
        #Do not write the script object to file
        #Use generate then write
        f.write(self.data)

class VideoTag(object):
    def __init__(self, f, size):
        self.data = f.read(size)
        self.frametype = struct.unpack("B",self.data[0])[0] >> 4 
    def write(self, f):
        f.write(self.data)

class AudioTag(object):
    def __init__(self, f, size):
        self.data = f.read(size)
    def write(self, f):
        f.write(self.data)

class FLVTag(object):
    def __init__(self, f):
        #Read but not use this value
        self.pts = get_ui32(f)
        self.tagtype = get_ui8(f)
        self.datasize = get_ui24(f)
        self.timestamp = get_si32_extended(f)
        self.streamid = get_ui24(f)
        if self.tagtype == 18:
            #Script Type Tag
            self.data = ScriptObject(f, self.datasize)
            self.data.generate()
            #Recalc the datasize
            self.datasize = len(self.data.data)
        elif self.tagtype == 9:
            #Video Type Tag
            self.data = VideoTag(f, self.datasize)
        elif self.tagtype == 8:
            #Audio Type Tag
            self.data = AudioTag(f, self.datasize)
        self.tagsize = self.datasize + 14

    def write(self, f):
        #ignore previous tag size but write current size to file
        #f.write(make_ui32(self.pts))
        f.write(make_ui8(self.tagtype))
        f.write(make_ui24(self.datasize))
        f.write(make_si32_extended(self.timestamp))
        f.write(make_ui24(self.streamid))
        self.data.write(f)
        f.write(make_ui32(self.tagsize))

metadata = None
metaposition = 13 #Default metadata position
for f in fs:
    print "========================================="
    print "%s :" % f.name
    tag = FLVTag(f)
    if type(metadata) != FLVTag and type(tag.data) == ScriptObject:
        metadata = tag
        if metaposition != fo.tell():
            metaposition = fo.tell()
            print ("Warning: Metadata position %d in file is not default "+\
                   "position") % metaposition
        metadata.write(fo)
    elif type(tag.data) == ScriptObject:
        if tag.data != metadata.data:
            print "<<<<<<<Media type mismatch"
            print tag.data.metadata
            exit(-1)
        metadata.data += tag.data
    print "-----------------------------------------"
    pprint.PrettyPrinter().pprint(metadata.data.metadata)
print "========================================="
print "Check Metadata => OK"

datasize = float(metadata.datasize)
lasttimestamp = float(0.0)
lastkeyframetimestamp = float(0.0)
lastkeyframelocation = float(0.0)
timestampbase = float(0.0)

for f in fs:
    try:
        while True:
            tag = FLVTag(f)
            datasize += tag.datasize
            tag.timestamp += timestampbase 
            if lasttimestamp < tag.timestamp:
                lasttimestamp = tag.timestamp
            if type(tag.data) == VideoTag:
                if tag.data.frametype == 5:
                    continue
                if tag.data.frametype == 1 or tag.data.frametype == 4:
                    #Is Keyframe
                    if lastkeyframetimestamp < tag.timestamp:
                        lastkeyframetimestamp = tag.timestamp
                        lastkeyframelocation = float(fo.tell() + 1)
            tag.write(fo)
    except Exception,e:
        print >>sys.stderr,datasize,"/",metadata.data.metadata['datasize'][1],"\r",
        pass
    finally:
        f.close()
    timestampbase = lasttimestamp

fo.flush()
#Finally Update the metadata
if type(metadata) == FLVTag:

    #Update values accumulate while iterate files
    metadata.data.metadata['datasize'] = \
            (0, datasize)
    metadata.data.metadata['lasttimestamp'] = \
            (0, lasttimestamp)
    metadata.data.metadata['lastkeyframetimestamp'] = \
            (0, lastkeyframetimestamp)
    metadata.data.metadata['lastkeyframelocation'] = \
            (0, lastkeyframelocation)
    #Finally check the `filesize' field
    #Total file size minus the size of one additional prevTagSz field
    metadata.data.metadata['filesize'] = \
            (0, float(os.path.getsize(fo.name) - 4))
    fo.seek(metaposition)
    metadata.data.generate()
    metadata.write(fo)

for f in fs:
    f.close()

fo.close()

#Open use ffmpeg fix a problem of original output
os.system(
    'ffmpeg -f flv -i "%s" -f flv -acodec copy -vcodec copy "%s" && rm "%s"' % \
        (output,args.output,output))

exit(0)

#End the statics
