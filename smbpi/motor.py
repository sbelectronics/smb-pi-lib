"""
    L293 Motor Driver
    Scott Baker, http://www.smbaker.com/

    Use L293 chip to control a motor.
"""

import RPi.GPIO as IO

L293_1 = 24   # 22 for the original prototype
L293_2 = 23   # 23 for the original prototype
L293_ENABLE = 18

# current prototype using these
L293_3 = 27
L293_4 = 22
L293_ENABLE2 = 17

class Motor:
    def __init__(self, pin1=L293_1, pin2=L293_2, enable=L293_ENABLE):
        self.pin1 = pin1
        self.pin2 = pin2
        self.enable = enable

        print "pin1=",pin1, "pin2=",pin2, "enable=", enable

        IO.setmode(IO.BCM)
        IO.setup(self.enable, IO.OUT)
        IO.setup(self.pin1, IO.OUT)
        IO.setup(self.pin2, IO.OUT)

        IO.output(self.pin1, True)
        IO.output(self.pin2, False)
        IO.output(self.enable, False)

        self.pwm = IO.PWM(self.enable,100)
        self.pwm.start(0)

    def set_dir(self, dir):
        if (dir > 0):
            IO.output(self.pin1, True)
            IO.output(self.pin2, False)
        else:
            IO.output(self.pin1, False)
            IO.output(self.pin2, True)

    def set_speed(self, speed):
        self.pwm.ChangeDutyCycle(100*speed/100)

