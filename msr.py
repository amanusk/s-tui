#!/usr/bin/python2.7
# library and tool to access Intel MSRs (model specific registers)
# Author: Andi Kleen
import glob
import struct
import os

def writemsr(msr, val):
    n = glob.glob('/dev/cpu/[0-9]*/msr')
    for c in n:
        f = os.open(c, os.O_WRONLY)
        os.lseek(f, msr, os.SEEK_SET)
        os.write(f, struct.pack('Q', val))
        os.close(f)
    if not n:
        raise OSError("msr module not loaded (run modprobe msr)")
    
def readmsr(msr, cpu = 0):
    f = os.open('/dev/cpu/0/msr', os.O_RDONLY)
    os.lseek(f, 429, os.SEEK_SET)
    read_res = os.read(f,8)
    s_decoded = [ord(c) for c in read_res]
    print s_decoded
    #val = struct.unpack('Q', os.read(f, 8))[0]
    os.close(f)
    return 13

def changebit(msr, bit, val):
    n = glob.glob('/dev/cpu/[0-9]*/msr')
    for c in n:
        f = os.open(c, os.O_RDWR)
        os.lseek(f, msr, os.SEEK_SET)
        v = struct.unpack('Q', os.read(f, 8))[0]
        if val:
            v = v | (1 << bit)
        else:
            v = v & ~(1 << bit)
        os.lseek(f, msr, os.SEEK_SET)            
        os.write(f, struct.pack('Q', v))
        os.close(f)
    if not n:
        raise OSError("msr module not loaded (run modprobe msr)")

if __name__ == '__main__':
    import argparse, os

    def parse_hex(s):
        try:
            return int(s, 16)
        except ValueError:
            raise argparse.ArgumentError("Bad hex number %s" % (s))

    if not os.path.exists("/dev/cpu/0/msr"):
        os.system("/sbin/modprobe msr")

    p = argparse.ArgumentParser(description='Access x86 model specific registers.')
    p.add_argument('msr', type=parse_hex, help='number of the MSR to access')
    p.add_argument('value', nargs='?', type=parse_hex, help='value to write (if not specified read)')
    p.add_argument('--setbit', type=int, help='Bit number to set')
    p.add_argument('--clearbit', type=int, help='Bit number to clear')
    p.add_argument('--cpu', type=int, default=0, help='CPU to read on (writes always change all)')
    args = p.parse_args()
    if not args.value and not args.setbit and not args.clearbit:
        print "%x" % (readmsr(args.msr, args.cpu))
    elif args.setbit:
        changebit(args.msr, args.setbit, 1)
    elif args.clearbit:
        changebit(args.msr, args.clearbit, 0)
    else:
        writemsr(args.msr, args.value)
