import time
import RPi.GPIO as GPIO
import pigpio

PIN_VFD_LOAD = 17
PIN_VFD_CLK = 22
PIN_VFD_DATA = 27
PIN_VFD_BLANK = 16

BIT_A =        1
BIT_B =        2
BIT_C =        4
BIT_D =        8
BIT_E =     0x10
BIT_F =     0x20
BIT_G =     0x40
BIT_DP =    0x80
BIT_G1 =   0x100
BIT_G2 =   0x200
BIT_G3 =   0x400
BIT_G4 =   0x800
BIT_G5 =  0x1000
BIT_G6 =  0x2000
BIT_G7 =  0x4000
BIT_G8 =  0x8000
BIT_G9 = 0x10000

BITI_A = BIT_D
BITI_B = BIT_C
BITI_C = BIT_B
BITI_D = BIT_A
BITI_E = BIT_F
BITI_F = BIT_E
BITI_G = BIT_G
BITI_DP = BIT_DP
BITI_G1 = BIT_G1
BITI_G2 = BIT_G9
BITI_G3 = BIT_G8
BITI_G4 = BIT_G7
BITI_G5 = BIT_G6
BITI_G6 = BIT_G5
BITI_G7 = BIT_G4
BITI_G8 = BIT_G3
BITI_G9 = BIT_G2

ZERO = BIT_A | BIT_B | BIT_C | BIT_D | BIT_E | BIT_F 
ONE =   BIT_B | BIT_C
TWO =   BIT_A | BIT_B | BIT_D | BIT_E | BIT_G
THREE = BIT_A | BIT_B | BIT_C | BIT_D | BIT_G
FOUR =  BIT_B | BIT_C | BIT_F | BIT_G
FIVE =  BIT_A | BIT_C | BIT_D | BIT_F | BIT_G
SIX =   BIT_A | BIT_C | BIT_D | BIT_E | BIT_F | BIT_G
SEVEN = BIT_A | BIT_B | BIT_C
EIGHT = BIT_A | BIT_B | BIT_C | BIT_D | BIT_E | BIT_F | BIT_G
NINE =  BIT_A | BIT_B | BIT_C | BIT_F | BIT_G

ZEROI = BITI_A | BITI_B | BIT_C | BIT_D | BIT_E | BIT_F 
ONEI =   BITI_B | BITI_C
TWOI =   BITI_A | BITI_B | BITI_D | BITI_E | BITI_G
THREEI = BITI_A | BITI_B | BITI_C | BITI_D | BITI_G
FOURI =  BITI_B | BITI_C | BITI_F | BITI_G
FIVEI =  BITI_A | BITI_C | BITI_D | BITI_F | BITI_G
SIXI =   BITI_A | BITI_C | BITI_D | BITI_E | BITI_F | BITI_G
SEVENI = BITI_A | BITI_B | BITI_C
EIGHTI = BITI_A | BITI_B | BITI_C | BITI_D | BITI_E | BITI_F | BITI_G
NINEI =  BITI_A | BITI_B | BITI_C | BITI_F | BITI_G

DIGITS = [ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE]
GATES = [BIT_G1, BIT_G2, BIT_G3, BIT_G4, BIT_G5, BIT_G6, BIT_G7, BIT_G8, BIT_G9]

DIGITSI = [ZEROI, ONEI, TWOI, THREEI, FOURI, FIVEI, SIXI, SEVENI, EIGHTI, NINEI]
GATESI = [BITI_G1, BITI_G2, BITI_G3, BITI_G4, BITI_G5, BITI_G6, BITI_G7, BITI_G8, BITI_G9]


class Max6921:
    def __init__(self, 
                 load=PIN_VFD_LOAD,
                 clk=PIN_VFD_CLK,
                 data=PIN_VFD_DATA,
                 blank=PIN_VFD_BLANK):
        self.load = load
        self.clk = clk
        self.data = data
        self.blank = blank

        self.flipped_ud = False
        self.flipped_lr = True

        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.load, GPIO.OUT)
        GPIO.setup(self.blank, GPIO.OUT)
        GPIO.setup(self.data, GPIO.OUT)
        GPIO.setup(self.clk, GPIO.OUT)

        GPIO.output(self.load, GPIO.LOW)  # not loaded
        GPIO.output(self.blank, GPIO.LOW)  # not blanked (outputs follow out)
        GPIO.output(self.clk, GPIO.HIGH)  # clocks in on high->low transitions
        GPIO.output(self.data, GPIO.LOW)  # might as well default it to something

    def clkDelay(self):
        pass # time.sleep(0.0001)

    def shiftIn(self, data):
        for i in range(0, 20):
            if (data & 0x80000) != 0:
                GPIO.output(self.data, 1)
            else:
                GPIO.output(self.data, 0)
            GPIO.output(self.clk, 0)
            self.clkDelay()
            GPIO.output(self.clk, 1)
            self.clkDelay()
            data = data << 1

        GPIO.output(self.load, 1)
        self.clkDelay()
        GPIO.output(self.load, 0)

    def displayDigit(self, digit, value):
        if self.flipped_ud:
            segs = DIGITSI[value]
        else:
            segs = DIGITS[value]
        if self.flipped_lr:
            gate = GATESI[digit+1]
        else:
            gate = GATES[digit+1]
        self.shiftIn(segs | gate)

    def displayNumber(self, value):
        for i in range(0,8):
            self.displayDigit(i, value % 10)
            value = value/10
        self.shiftIn(0)

def TO_BIT(x):
    return 1<<x

class Max6921_Wave:
    def __init__(self,
                 pi=None,
                 load=PIN_VFD_LOAD,
                 clk=PIN_VFD_CLK,
                 data=PIN_VFD_DATA,
                 blank=PIN_VFD_BLANK):
        self.pi = pi
        self.load = load
        self.clk = clk
        self.data = data
        self.blank = blank

        self.flipped_ud = False
        self.flipped_lr = True

        self.pi.set_mode(self.load, pigpio.OUTPUT)
        self.pi.set_mode(self.blank, pigpio.OUTPUT)
        self.pi.set_mode(self.data, pigpio.OUTPUT)
        self.pi.set_mode(self.clk, pigpio.OUTPUT)

        self.pi.write(self.load, 0)  # not loaded
        self.pi.write(self.blank, 0)  # not blanked (outputs follow out)
        self.pi.write(self.clk, 1)  # clocks in on high->low transitions
        self.pi.write(self.data, 0)  # might as well default it to something

    def shiftIn(self, data):
        pulses = []
        for i in range(0, 20):
            if (data & 0x80000) != 0:
                pulses.append(pigpio.pulse(TO_BIT(self.data), 0, 1))
            else:
                pulses.append(pigpio.pulse(0, TO_BIT(self.data), 1))
            pulses.append(pigpio.pulse(0, TO_BIT(self.clk), 1))
            pulses.append(pigpio.pulse(TO_BIT(self.clk), 0, 1))
            data = data << 1

        pulses.append(pigpio.pulse(TO_BIT(self.load), 0, 1))
        pulses.append(pigpio.pulse(0, TO_BIT(self.load), 10))

        return pulses

    def generateDigit(self, digit, value):
        if self.flipped_ud:
            segs = DIGITSI[value]
        else:
            segs = DIGITS[value]
        if self.flipped_lr:
            gate = GATESI[digit+1]
        else:
            gate = GATES[digit+1]
        return self.shiftIn(segs | gate)

    def generateNumber(self, value):
        pulses = []
        for i in range(0,8):
            pulses = pulses + self.generateDigit(i, value % 10)
            value = value/10
        self.shiftIn(0)
        return pulses

    def displayWave(self, pulses):
        self.pi.wave_clear()
        self.pi.wave_add_generic(pulses)
        self.wave_display = self.pi.wave_create()
        self.pi.wave_send_repeat(self.wave_display)



def main():
    pi = pigpio.pi()

    vfd = Max6921_Wave(pi = pi)
    pulses = vfd.generateNumber(12345678)
    vfd.displayWave(pulses)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()