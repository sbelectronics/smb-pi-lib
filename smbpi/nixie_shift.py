"""
    Raspberry Pi Nixie Tubes from Shift Registers
    Scott M Baker, 2013
    http://www.smbaker.com/

    This was used in some of my early pi projects, notably a clock
    and a temperature/hudity display. The Nixie tubes are driven
    by 74HCT595 shift registers from three pins on the pi.
"""

import RPi.GPIO as GPIO
import time
import datetime
import os, sys, termios, tty, fcntl

PIN_DATA = 23
PIN_LATCH = 25 #24 breadboard
PIN_CLK = 24 #25 breadboard

PIN_DP6 = 14
PIN_DP7 = 15
PIN_POWCTL = 18
PIN_DP1 = 2
PIN_DP2 = 3

class NixieShift(object):
    def __init__(self, pin_data, pin_latch, pin_clk, digits, flipRows, blank=[], 
                 pin_dp6 = PIN_DP6, pin_dp7 = PIN_DP7,
                 pin_dp1 = PIN_DP1, pin_dp2 = PIN_DP2,
                 pin_powctl = PIN_POWCTL,
                 enable_rev2 = False):
        self.pin_data = pin_data
        self.pin_latch = pin_latch
        self.pin_clk = pin_clk
        self.digits = digits
        self.flipRows = flipRows
        self.blank = blank

        self.pin_dp6 = pin_dp6
        self.pin_dp7 = pin_dp7
        self.pin_dp1 = pin_dp1
        self.pin_dp2 = pin_dp2
        self.pin_powctl = pin_powctl
        self.enable_rev2 = enable_rev2

        self.state_dp6= 0
        self.state_dp7 = 0
        self.state_dp1 = 0
        self.state_dp2 = 0
        self.state_powctl = 0

        GPIO.setmode(GPIO.BCM)

        # Setup the GPIO pins as outputs
        GPIO.setup(self.pin_data, GPIO.OUT)
        GPIO.setup(self.pin_latch, GPIO.OUT)
        GPIO.setup(self.pin_clk, GPIO.OUT)

        # Set the initial state of our GPIO pins to 0
        GPIO.output(self.pin_data, False)
        GPIO.output(self.pin_latch, False)
        GPIO.output(self.pin_clk, False)

        if (enable_rev2):
            GPIO.setup(self.pin_dp6, GPIO.OUT)
            GPIO.setup(self.pin_dp7, GPIO.OUT)
            GPIO.setup(self.pin_dp1, GPIO.OUT)
            GPIO.setup(self.pin_dp2, GPIO.OUT)
            GPIO.setup(self.pin_powctl, GPIO.OUT)

            self.set_dp(1, 0)
            self.set_dp(2, 0)
            self.set_dp(6, 0)
            self.set_dp(7, 0)
            self.set_powctl(0)

    def delay(self):
        # We'll use a 10ms delay for our clock
        time.sleep(0.001)

    def transfer_latch(self):
        # Trigger the latch pin from 0->1. This causes the value that we've
        # been shifting into the register to be copied to the output.
        GPIO.output(self.pin_latch, True)
        self.delay()
        GPIO.output(self.pin_latch, False)
        self.delay()

    def tick_clock(self):
        # Tick the clock pin. This will cause the register to shift its
        # internal value left one position and the copy the state of the DATA
        # pin into the lowest bit.
        GPIO.output(self.pin_clk, True)
        self.delay()
        GPIO.output(self.pin_clk, False)
        self.delay()

    def shift_bit(self, value):
        # Shift one bit into the register.
        GPIO.output(self.pin_data, value)
        self.tick_clock()

    def shift_digit(self, value):
        # Shift a 4-bit BCD-encoded value into the register, MSB-first.
        self.shift_bit(value&0x08)
        value = value << 1
        self.shift_bit(value&0x08)
        value = value << 1
        self.shift_bit(value&0x08)
        value = value << 1
        self.shift_bit(value&0x08)

    def set_blank(self, blank):
        # Update the blanking digits
        # This won't cause a display refresh -- be sure to also call set_value()
        self.blank = blank

    def set_value(self, value):
        # Shift a decimal value into the register

        str = "%0*d" % (self.digits, value)

        if self.flipRows:
            str = str[4:] + str[:4]

        index = 1
        for digit in str:
            if (index in self.blank):
                self.shift_digit(12)
            else:
                self.shift_digit(int(digit))
            index = index + 1

        self.transfer_latch()

    def set_dp(self, n, v):
        if self.enable_rev2:
            vname = "pin_dp%d" % n
            GPIO.output(getattr(self,vname), v)

        vname = "state_dp%d" % n
        setattr(self,vname, v)

    def get_dp(self, n):
        vname = "state_dp%d" % n
        return getattr(self,vname)

    def set_powctl(self, v):
        if self.enable_rev2:
            GPIO.output(self.pin_powctl, v)
            
        self.state_powctl = v

    def get_powctl(self):
        return self.state_powctl


TEST_FIXED = "f"
TEST_DIGMOVE = "m"
TEST_COUNT = "c"
TEST_ALL = "a"
KEY_POWCTL = "p"

testmode = TEST_FIXED

def getKey():
   fd = sys.stdin.fileno()
   fl = fcntl.fcntl(fd, fcntl.F_GETFL)
   fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
   old = termios.tcgetattr(fd)
   new = termios.tcgetattr(fd)
   new[3] = new[3] & ~termios.ICANON & ~termios.ECHO
   new[6][termios.VMIN] = 1
   new[6][termios.VTIME] = 0
   termios.tcsetattr(fd, termios.TCSANOW, new)
   key = None
   try:
      key = os.read(fd, 3)
   except:
      return 0
   finally:
      termios.tcsetattr(fd, termios.TCSAFLUSH, old)
   return key

def testpatterns_8dig(nixie):
    global testmode
    val1=0
    val2=0

    while True:
        key = getKey()
        if (key in [TEST_FIXED, TEST_DIGMOVE, TEST_COUNT,TEST_ALL]):
            testmode = key

        if (key in ["1", "2", "6", "7"]):
            cur = nixie.get_dp(int(key))
            if cur == 0:
                cur = 1
            else:
                cur = 0
            nixie.set_dp(int(key), cur)

        if key == KEY_POWCTL:
            if nixie.get_powctl()!=0:
                nixie.set_powctl(0)
            else:
                nixie.set_powctl(1)

        if (testmode==TEST_FIXED):
            nixie.set_value(12345678)
        elif (testmode==TEST_DIGMOVE):
            val1 = val1 + 1
            if (val1>=8):
                val1 = 0
                val2 = val2 +1
            if (val2>=10) or (val2<=1):
                val2=1
            nixie.set_value(int( str(val2) + ("0" * val1)))
            time.sleep(0.01)
        elif (testmode==TEST_COUNT):
            val1=val1+1
            nixie.set_value(val1)
            time.sleep(0.001)
        elif (testmode==TEST_ALL):
            val1 = val1 + 1
            if (val1 >= 10):
                val1 = 0
            nixie.set_value(int( str(val1)*8 ))

def main():
    try:
        nixie = NixieShift(PIN_DATA, PIN_LATCH, PIN_CLK, 8, True, enable_rev2=True)

        # Uncomment for a simple test pattern
        # nixie.set_value(12345678)

        testpatterns_8dig(nixie)

        # Repeatedly get the current time of day and display it on the tubes.
        # (the time retrieved will be in UTC; you'll want to adjust for your
        # time zone)

        #while True:
        #    dt = datetime.datetime.now()
        #    nixie.set_value(dt.hour*100 + dt.minute)

    finally:
        # Cleanup GPIO on exit. Otherwise, you'll get a warning next time toy
        # configure the pins.
        GPIO.cleanup()

if __name__ == "__main__":
    main()
