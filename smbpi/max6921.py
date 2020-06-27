"""
    MAX6921 Driver, for use with IV-28B Russian VFD Tube
    Scott M Baker, 2020
    http://www.smbaker.com/

    Raspberry pi driver for MAX6921 VFD Controller.
    
    This implementation is specific to use with an IV-28 display.
    The BIT_ constants will explain which of the MAXX6921 outputs
    are connected to which anodes and grids on the IV-28. If you're
    using a different display or you've wired yours differently,
    then adjusting the BIT_ constants will be necessary.

    Requires pigpio in order to smoothly multiplex the display.

    Pigpio Installation notes:
        rm -f pigpio.zip
        sudo rm -rf pigpio-master
        wget https://github.com/joan2937/pigpio/archive/master.zip -O pigpio.zip
        unzip pigpio.zip
        cd pigpio-master
        make
        sudo make install

    Pigpio run notes:
        sudo pigpiod -s 2
"""

import time
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

def TO_BIT(x):
    return 1<<x


class Max6921:
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

        self.leaderTop = False
        self.leaderMid = False
        self.leaderBot = False

        self.flipped_ud = False
        self.flipped_lr = True

        self.dps = [False, False, False, False, False, False, False, False, False]

        self.pi.set_mode(self.load, pigpio.OUTPUT)
        self.pi.set_mode(self.blank, pigpio.OUTPUT)
        self.pi.set_mode(self.data, pigpio.OUTPUT)
        self.pi.set_mode(self.clk, pigpio.OUTPUT)

        self.pi.write(self.load, 0)  # not loaded
        self.pi.write(self.blank, 0)  # not blanked (outputs follow out)
        self.pi.write(self.clk, 1)  # clocks in on high->low transitions
        self.pi.write(self.data, 0)  # might as well default it to something

    def shiftIn(self, data, postDelay=10):
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
        pulses.append(pigpio.pulse(0, TO_BIT(self.load), postDelay))

        return pulses

    def setDP(self, number, value, exclusive = False):
        if exclusive:
            self.dps = [False, False, False, False, False, False, False, False, False]
        self.dps[number] = value

    def setLeader(self, top=False, mid=False, bot=False):
        # The "leader" is the special symbols before the leftmost digit of the
        # display. "top" and "bot" are both dots. "mid" is a dash and might be
        # useful as a minus sign
        self.leaderTop = top
        self.leaderMid = mid
        self.leaderBot = bot

    def generateDigit(self, digit, value, dp=False):
        if self.flipped_ud:
            segs = DIGITSI[value]
        else:
            segs = DIGITS[value]

        if self.flipped_lr:
            gate = GATESI[digit+1]
        else:
            gate = GATES[digit+1]

        if dp:
            segs = segs | BIT_DP

        return self.shiftIn(segs | gate)

    def generateLeader(self):
        segs = 0
        if self.leaderTop:
            segs = segs + BIT_F
        if self.leaderMid:
            segs = segs + BIT_G
        if self.leaderBot:
            segs = segs + BIT_DP

        if segs != 0:
            return self.shiftIn(segs | GATES[0]) + self.shiftIn(0, postDelay=0)
        else:
            return []

    def generateNumber(self, value, leadingZero=False):
        pulses = []
        for i in range(0, 8):
            pulses = pulses + self.generateDigit(i, value % 10, self.dps[i])
            value = value/10
            # blank the outputs to prevent ghosting between digits
            pulses = pulses + self.shiftIn(0, postDelay=0)

            if (not leadingZero) and (value == 0):
                return pulses
        return pulses

    def generateString(self, s):
        # gnerateString supports using spaces to leave digits blank
        pulses = []
        i = 7
        for c in s:
            if c.isdigit():
                pulses = pulses + self.generateDigit(i, ord(c)-ord("1")+1, self.dps[i])
                # blank the outputs to prevent ghosting between digits
                pulses = pulses + self.shiftIn(0, postDelay=0)
            i = i - 1
        pulses = pulses + self.generateLeader()
        self.shiftIn(DIGITS[8] + GATES[0] + BIT_DP)
        return pulses

    def displayWave(self, pulses):
        self.pi.wave_clear()
        self.pi.wave_add_generic(pulses)
        self.wave_display = self.pi.wave_create()
        self.pi.wave_send_repeat(self.wave_display)

    def displayNumber(self, n, leadingZero=False):
        self.displayWave(self.generateNumber(n, leadingZero=leadingZero))

    def displayString(self, s):
        self.displayWave(self.generateString(s))



def main():
    # Self-test demo, starts by displaying 12345678
    # then increments ten times per second.

    pi = pigpio.pi()

    vfd = Max6921(pi = pi)

    n = 12345678

    while True:
        #vfd.displayNumber(n)
        vfd.setLeader(mid=((n%10)<=5))
        vfd.setDP(n % 9, 1, True)
        vfd.displayString("%d" % n)

        time.sleep(0.1)

        n = n + 1


if __name__ == "__main__":
    main()