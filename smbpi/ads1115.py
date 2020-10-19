"""
    ADS1115 driver
    Scott Baker, http://www.smbaker.com/

    Interface with ADS1115 chip.
"""

import time

REG_CONV = 0
REG_CONFIG = 1
REG_LO_THRESH = 2
REG_HI_THRESH = 3

OS = 1 << 15

MUX_AIN0_AIN1 = 0b000 << 12
MUX_AIN0_AIN3 = 0b001 << 12
MUX_AIN1_AIN3 = 0b010 << 12
MUX_AIN2_AIN3 = 0b011 << 12
MUX_AIN0 = 0b100 << 12
MUX_AIN1 = 0b101 << 12
MUX_AIN2 = 0b110 << 12
MUX_AIN3 = 0b111 << 12

PGA_6V = 0b000 << 9
PGA_4V = 0b001 << 9
PGA_2V = 0b010 << 9
PGA_1V = 0b011 << 9
PGA_05V = 0b100 << 9
PGA_02V = 0b101 << 9

MODE_CONT = 0
MODE_SINGLE = 1 << 8

DATA_8 = 0b000 << 5
DATA_16 = 0b001 << 5
DATA_32 = 0b010 << 5
DATA_64 = 0b011 << 5
DATA_128 = 0b100 << 5
DATA_250 = 0b101 << 5
DATA_475 = 0b110 << 5
DATA_860 = 0b111 << 5

COMP_MODE_TRAD = 0
COMP_MODE_WINDOW = 1 << 4

COMP_POL_LOW = 0
COMP_POL_HIGH = 1 << 3

COMP_NON_LAT = 0
COMP_LAT = 1 << 2

COMP_QUE_ONE = 0
COMP_QUE_TWO = 1
COMP_QUE_THREE = 2
COMP_QUE_DISABLE = 3

# default = MUX_AIN0_AIN1 | PGA_2V | MODE_SINGLE | DATA_128 | COMP_MODE_TRAD | COMP_POL_LOW | COMP_NON_LAT | COMP_QUE_DISBALE


class ADS1115:
    def __init__(self, bus, addr):
        self.addr = addr
        self.bus = bus
        self.lastConfig = None

    def write_config(self, bits):
        self.lastConfig = bits
        bytes = [(bits >> 8) & 0xFF, bits & 0xFF]
        self.bus.write_i2c_block_data(self.addr, REG_CONFIG, bytes)

    def get_data_rate(self):
        dr = self.lastConfig & (0b110 << 5)
        if (dr == DATA_8):
            return 8
        elif (dr == DATA_16):
            return 16
        elif (dr == DATA_32):
            return 32
        elif (dr == DATA_64):
            return 64
        elif (dr == DATA_128):
            return 128
        elif (dr == DATA_250):
            return 250
        elif (dr == DATA_475):
            return 475
        else:
            return 860

    def wait_samp(self):
        # note that this isn't enough -- I had to wait an additional 8ms at
        # DATA_128 and an addition 32ms at DATA_32. This was while using
        # MUX_AIN0_AIN3 and MUX_AIN1_AIN3, so maybe it takes twice as long
        # to do a relative conversion.
        # TODO: investigate
        time.sleep(1.0/self.get_data_rate()+0.0001)

    def read_conversion(self):
        result = self.bus.read_i2c_block_data(self.addr, REG_CONV, 2)
        val = (result[0] << 8) | (result[1] & 0xFF)

        # if the result >= 0x8000 then it's a negative number
        if (val >= 0x8000):
            val = -((~val & 0xFFFF) + 1)

        return val


def main():
    import smbus
    import time
    bus = smbus.SMBus(1)
    adc = ADS1115(bus, 0x48)
    adc.write_config(MUX_AIN0 | PGA_4V | MODE_CONT | DATA_128 | COMP_MODE_TRAD | COMP_POL_LOW | COMP_NON_LAT | COMP_QUE_DISABLE)
    adc.wait_samp()
    while True:
        print "%d        \r" % adc.read_conversion()
        time.sleep(0.1)


if __name__ == "__main__":
    main()
