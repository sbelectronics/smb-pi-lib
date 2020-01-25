"""
    MCP4821 Driver
    Scott M Baker, 2020
    http://www.smbaker.com/

    Raspberry pi driver for MCP4821 DAC. Also ought to work
    for MCP4921. Written and tested on 12-bit DAC. I put code
    in to support the 8-bit and 10-bit variants, but it's
    untested. Just spend a few cents and buy the 12-bit one.
"""

import spidev
import RPi.GPIO as GPIO
import sys

DEFAULT_CE=0
DEFAULT_GAIN=1
DEFAULT_LDAQ=22

class MCP4821:
    def __init__(self, spi, ce=DEFAULT_CE, ldaq=DEFAULT_LDAQ, gain=DEFAULT_GAIN):
        self.spi = spi
        self.ce = ce
        self.ldaq = ldaq
        self.vRef = 2048
        self.bits = 12
        self.resolution = 2**self.bits
        self.gain = gain

        spi.open(0, self.ce)
        spi.max_speed_hz = 4 * 1000000

        if self.ldaq is not None:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.ldaq, GPIO.OUT)
            GPIO.output(self.ldaq, GPIO.LOW)

    def setOutput(self, val):
        if self.gain == 2:
            gainBit = 0
        else:
            gainBit = 1

        if self.bits == 12:
            # lower 8 bits of data
            lowByte = val & 0xFF

            # highbyte has 0, 0, Gain, Shdn, D11, D10, D9, D8
            highByte = 0b0 << 7 | 0b0 << 6 | gainBit << 5 | 0b1 << 4 | ((val >> 8) & 0xff)
        elif self.bits == 10:
            # lower 8 bits of data
            lowByte = (val << 2) & 0xFF

            # highbyte has 0, 0, Gain, Shdn, D11, D10, D9, D8
            highByte = 0b0 << 7 | 0b0 << 6 | gainBit << 5 | 0b1 << 4 | ((val >> 6) & 0xff)
        elif self.bits == 8:
            # lower 8 bits of data
            lowByte = (val << 4) & 0xFF

            # highbyte has 0, 0, Gain, Shdn, D11, D10, D9, D8
            highByte = 0b0 << 7 | 0b0 << 6 | gainBit << 5 | 0b1 << 4 | ((val >> 4) & 0xff)

        self.last_highByte = highByte
        self.last_lowByte = lowByte
        self.last_value = val

        self.spi.xfer2([highByte, lowByte])

    def valueToVoltage(self, val):
        return float(val) * self.gain * self.vRef / self.resolution / 1000.0


def main():
    if len(sys.argv)<=1:
        print >> sys.stderr, "Please specify value as command-line arg"
        sys.exit(-1)

    v = int(sys.argv[1])

    spi = spidev.SpiDev()

    try:
        dac = MCP4821(spi)

        dac.setOutput(v)

        print "Voltage: %0.4f" % dac.valueToVoltage(v)
        print "Binary value : {0:12b} (12 bit)".format(v)
        print "Highbyte = {0:8b}".format(dac.last_highByte)
        print "Lowbyte =  {0:8b}".format(dac.last_lowByte)
    finally:
        spi.close()


if __name__ == '__main__':
    main()
