"""
    MotorPot Driver
    Scott Baker, http://www.smbaker.com/

    Interface with a motorized potentiomer using an L293 and ADS1015
"""

import sys
import time
from threading import Thread
from motor import Motor, L293_1, L293_2, L293_ENABLE, L293_3, L293_4, L293_ENABLE2
from ads1015 import ADS1015, MUX_AIN0, PGA_4V, MODE_CONT, DATA_1600, COMP_MODE_TRAD, COMP_POL_LOW, COMP_NON_LAT, COMP_QUE_DISABLE

# moved the L293 enable from gpio18 to gpio15 to prevent conflict with
# digi+ io card
STEREO_L293_ENABLE = 15

class MotorPot(Thread):
    def __init__(self, bus, adc_addr=0x48, motor_pin1=L293_1, motor_pin2=L293_2, motor_enable = STEREO_L293_ENABLE, dirmult=1, verbose=False):
        Thread.__init__(self)

        self.motor = Motor(pin1=motor_pin1, pin2=motor_pin2, enable = motor_enable)
        self.motor.set_speed(0)

        self.adc = ADS1015(bus, adc_addr)

        self.adc.write_config(MUX_AIN0 | PGA_4V | MODE_CONT | DATA_1600 | COMP_MODE_TRAD | COMP_POL_LOW | COMP_NON_LAT | COMP_QUE_DISABLE)

        self.dirmult = dirmult

        self.setPoint = None
        self.newSetPoint = False
        self.moving = False

        self.daemon = True
        self.verbose = verbose

        self.lastStopTime = time.time()

        self.start()

    def set(self, value):
        self.setPoint = value
        self.newSetPoint = True

    def check_for_request(self):
        pass

    def handle_value(self):
        pass

    def run(self):
        lastStallValue = -1
        stallStack = []
        setPoint = None
        while True:
            self.check_for_request()

            self.value = self.adc.read_conversion()

            self.handle_value()

            if self.newSetPoint:
                setPoint = self.setPoint
                self.newSetPoint=False
                settle = 0
                stallStack = []

            if setPoint is not None:
                if (self.value < setPoint):
                    dir = 1
                else:
                    dir = -1

                # the 'P' part of a PID controller...
                error = abs(self.value - setPoint)
                if (error <= 1):
                    speed = 0

                    # are we done yet?
                    settle=settle+1
                    if (settle>32):
                        setPoint = None
                else:
                    settle = 0
                    if (error < 10):
                        speed = 50
                    elif (error < 25):
                        speed = 55
                    elif (error < 50):
                        speed = 65
                    elif (error < 100):
                        speed = 75
                    else:
                        speed = 100

                stallStack.insert(0, self.value)
                stallStack = stallStack[:250]
                minv = min(stallStack)
                maxv = max(stallStack)
                if (len(stallStack)>=250) and ((maxv-minv) < 25):
                    print "stalled at", self.value, maxv, minv
                    speed = 0
                    setPoint = None

                if self.verbose:
                    print "moving", self.value, setPoint, dir, speed

                self.motor.set_dir(dir * self.dirmult)
                self.motor.set_speed(speed)

                self.moving = True

                time.sleep(0.001)
            else:
                if self.moving:
                    self.lastStopTime = time.time()

                self.moving = False

                if self.verbose:
                    print "monitor", self.value

                # course-grained if we're just reading it
                time.sleep(0.1)

def main():
    if len(sys.argv)<2:
        print "syntax: motorpot.py <value>"
        return

    print sys.argv

    import smbus
    bus = smbus.SMBus(1)

    #motorpot = MotorPot(bus, dirmult=-1, verbose=True)
    motorpot = MotorPot(bus, dirmult=1, verbose=True, motor_pin1=L293_3, motor_pin2=L293_4, motor_enable = L293_ENABLE2)

    if sys.argv[1]!="none":
        motorpot.set(int(sys.argv[1]))

    while True:
        time.sleep(1)


if __name__== "__main__":
    main()

