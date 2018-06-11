"""
    TLC59116 Driver
    Scott Baker, http://www.smbaker.com/

    This program includes a main() function and can be run from the command
    line, for example:
       python tlc59116.py led 0 pwm 128

    It can also be included as a library. Just import the module, and create
    a TLC59116 object. See the main() function for an example how that's
    done.
"""

import sys
import time

REG_MODE1 = 0
REG_MODE2 = 1
REG_GRPPWM = 0x12
REG_GRPFREQ = 0x13
REG_LEDOUT0 = 0x14

MODE1_OSC_OFF = 16
MODE1_ALL_CALL = 1

MODE2_DMBLNK = 0x20

STATE_OFF = 0
STATE_ON = 1
STATE_PWM = 2
STATE_GRP = 3

class TLC59116(object):
    def __init__(self, bus, addr):
        self.addr = addr
        self.bus = bus
        self.mode1 = self.read_reg(REG_MODE1) #default: MODE1_OSC_OFF | MODE1_ALL_CALL
        self.mode2 = self.read_reg(REG_MODE2) #detault: 0

    def read_reg(self, reg):
        return self.bus.read_byte_data(self.addr, reg)

    def write_reg(self, reg, bits):
        self.bus.write_byte_data(self.addr, reg, bits)

    def set_oscillator(self, enable):
        if enable:
            self.mode1 = self.mode1 & (~MODE1_OSC_OFF)
        else:
            self.mode1 = self.mode1 | MODE1_OSC_OFF
        self.write_reg(REG_MODE1, self.mode1)

    def set_led_state(self, led, state):
        reg = (led / 4) + REG_LEDOUT0
        shift = (led % 4) * 2
        v = self.read_reg(reg)
        v = v & (~(3 << shift)) | (state << shift)
        # print "write mode reg %x %x" % (reg, v)
        self.write_reg(reg, v)

    def set_led_pwm(self, led, brightness):
        self.write_reg(led+2, brightness)

    def set_blink(self, blink):
        if blink:
            self.mode2 = self.mode2 | MODE2_DMBLNK
        else:
            self.mode2 = self.mode2 & (~MODE2_DMBLNK)
        self.write_reg(REG_MODE2, self.mode2)

    def set_grpfreq(self, freq):
        self.write_reg(REG_GRPFREQ, freq)

    def set_grppwm(self, freq):
        self.write_reg(REG_GRPPWM, freq)

def help():
    print "tcl59116.py <command> <args>"
    print
    print "commands:"
    print "    led <num> [off|on|pwm|grp] <pwmval>"
    print "    blink <rate>"
    print "    noblink"
    print "    grppwm <pwmval>"
    print "    cylon"
    print "    oscoff"

def main():
    import smbus

    bus = smbus.SMBus(1)
    leds = TLC59116(bus, 0x60)

    if (len(sys.argv) <= 1):
        help()
        sys.exit(0)

    if (sys.argv[1] == "led"):
        if (sys.argv[2]=="all"):
            led = "all"
        else:
            led = int(sys.argv[2])

        mode = sys.argv[3]

        if (mode=="off"):
            mode = STATE_OFF
        elif (mode=="on"):
            mode = STATE_ON
        elif (mode=="pwm"):
            mode = STATE_PWM
        elif (mode=="grp"):
            mode = STATE_GRP
        else:
            raise Exception("unknown mode")

        if (mode in [STATE_PWM, STATE_GRP]):
            pwm = int(sys.argv[4])
        else:
            pwm = None

        leds.set_oscillator(True)

        if (led=="all"):
            for i in range(0,15):
                leds.set_led_state(i, mode)
                if pwm:
                    leds.set_led_pwm(i, pwm)
        else:
            leds.set_led_state(led, mode)
            if pwm:
                leds.set_led_pwm(led, pwm)
    elif (sys.argv[1] == "blink"):
        leds.set_blink(True)
        leds.set_grppwm(128)
        leds.set_grpfreq(int(sys.argv[2]))
    elif (sys.argv[1] == "noblink"):
        leds.set_blink(False)
        leds.set_grppwm(255)
    elif (sys.argv[1] == "grppwm"):
        leds.set_blink(False)
        leds.set_grppwm(int(sys.argv[2]))
    elif (sys.argv[1] == "cylon"):
        leds.set_oscillator(True)
        for i in range(0,16):
            leds.set_led_state(i, STATE_GRP)
        while True:
            for i in range(0,16):
                leds.set_led_pwm(i, 255)
                time.sleep(0.1)
                leds.set_led_pwm(i, 0)
            for i in range(1, 15):
                leds.set_led_pwm(15-i, 255)
                time.sleep(0.1)
                leds.set_led_pwm(15-i, 0)
    elif (sys.argv[1] == "noosc"):
        leds.set_oscillator(False)
    else:
        help()


if __name__ == "__main__":
    main()
