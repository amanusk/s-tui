#!/usr/bin/python2.7

import os


def readmsr(msr, cpu = 0):
    if not os.path.exists("/dev/cpu/0/msr"):
        try:
            os.system("/sbin/modprobe msr")
        except:
            pass
        return None
    f = os.open('/dev/cpu/%d/msr' % (cpu,), os.O_RDONLY)
    os.lseek(f, msr, os.SEEK_SET)
    read_res = os.read(f, 8)
    s_decoded = [ord(c) for c in read_res]
    os.close(f)
    m = min(i for i in s_decoded if i > 0)
    return float(m * 100)
