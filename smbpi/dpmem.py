import string
import sys
import time
import RPi.GPIO as IO

from dpmem_common import *

class DualPortMemoryGPIO:
  def __init__(self):
      IO.setmode(IO.BCM)
      for addrpin in DP_ADDRPINS:
          IO.setup(addrpin, IO.OUT)
  
      for datapin in DP_DATAPINS:
          IO.setup(datapin, IO.IN)

      for controlpin in DP_CONTROLPINS:
          IO.setup(controlpin, IO.OUT)

      IO.setup(DP_INTR, IO.IN, pull_up_down=IO.PUD_UP)

      IO.output(DP_W, 1)
      IO.output(DP_R, 1)
      IO.output(DP_CE, 1)

  def read(self, addr):
      try:
          for pin in DP_DATAPINS:
              IO.setup(pin, IO.IN)

          for pin in DP_ADDRPINS:
              IO.output(pin, addr & 1)
              addr = addr >> 1

          IO.output(DP_CE, 0)
          IO.output(DP_R, 0)

          val=0
          for pin in reversed(DP_DATAPINS):
              val=val<<1
              val = val | IO.input(pin)
      finally:
          IO.output(DP_R, 1)
          IO.output(DP_CE, 1)

      return val

  def write(self, addr, val):
      try:
          for pin in DP_DATAPINS:
              IO.setup(pin, IO.OUT)

          for pin in DP_ADDRPINS:
              IO.output(pin, addr & 1)
              addr = addr >> 1

          IO.output(DP_CE, 0)
          IO.output(DP_W, 0)

          for pin in DP_DATAPINS:
              IO.output(pin, val & 1)
              val = val >> 1
      finally:
          IO.output(DP_W, 1)
          IO.output(DP_CE, 1)

      return val

  def write_blcok(self, addr, data, count):
      for i in range(0, count):
          self.mem.write(addr+i, ord(data[i]))

  def read_block(self, addr, count):
      bytes=[]
      for i in range(0, count):
          bytes = bytes + chr(self.mem.read(addr+i))
      return bytes

  def get_interrupt(self):
      return IO.input(DP_INTR) == 0

  def clear_interrupt(self):
      self.read(0x3FF)

def str_to_int(val):
    if "x" in val:
        val = string.atoi(val, 16)
    else:
        val = string.atoi(val)
    return val

def help():
    print "read <addr>"
    print "write <addr> <val>"
    print "waitint"

def main():
    mem = DualPortMemory()

    if sys.argv[1] == "read":
        addr = str_to_int(sys.argv[2])
        print "addr %04x = %02X" % (addr, mem.read(addr))

    elif sys.argv[1] == "write":
        addr = str_to_int(sys.argv[2])
        val = str_to_int(sys.argv[3])
        mem.write(addr, val)

    elif sys.argv[1] == "waitint":
        while not mem.get_interrupt():
            time.sleep(0.0001)
        mem.clear_interrupt()

    else:
        help()



if __name__ == "__main__":
    main()
