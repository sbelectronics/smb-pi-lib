"""
    IO Expanders
    Scott Baker, http://www.smbaker.com/

    Various I2C IO Expanders
"""

IODIR = 0x00
IPOL = 0x02
GPINTEN = 0x04
DEFVAL = 0x06
INTCON = 0x08
IOCON = 0x0A
GPPU = 0x0C
INTF = 0x0E
MCP23017_GPIO = 0x12
OLAT = 0x14

IOCON_BANK = 0x80
IOCON_MIRROR = 0x40
IOCON_SEQOP = 0x20
IOCON_DISSLW = 0x10
IOCON_HAEN = 0x80
IOCON_ODR = 0x40
IOCON_INTPOL = 0x20

class MCP23017:
   def __init__(self, bus, addr):
       self.addr = addr
       self.bus = bus
       self.banks = 2
       self.gpio_bits = [0, 0]
       self.dir_bits = [0, 0]

   def writereg(self, reg, bits):
       self.bus.write_byte_data(self.addr, reg, bits)

   def readreg(self, reg):
       return self.bus.read_byte_data(self.addr, reg)

   def set_iodir(self, bank, bits):
       self.writereg(bank + IODIR, bits)
       self.dir_bits = bits

   def set_polarity(self, bank, bits):
       self.writereg(bank + IPOL, bits)

   def set_interrupt(self, bank, bits):
       self.writereg(bank + GPINTEN, bits)

   def set_intdef(self, bank, bits):
       self.writereg(bank + DEFVAL, bits)

   def set_intcon(self, bank, bits):
       self.writereg(bank + INTCON, bits)

   def set_config(self, bits):
       self.writereg(IOCON, bits)

   def set_pullup(self, bank, bits):
       self.writereg(bank + GPPU, bits)

   def set_gpio(self, bank, bits):
       self.writereg(bank + MCP23017_GPIO, bits)
       self.gpio_bits[bank] = bits

   def set_latch(self, bank, bits):
       self.writereg(bank + OLAT, bits)

   def get_gpio(self, bank):
       return self.readreg(bank + MCP23017_GPIO)

   def get_intf(self, bank):
       return self.readreg(bank + INTF)

   def configure_as_keypad(self):
       self.set_pullup(0, 0xFF)
       self.set_pullup(1, 0xFF)

   def configure_as_display(self):
       self.set_iodir(0, 0x00)
       self.set_iodir(1, 0x00)

   def configure_as_led_keypad(self):
       # bank 0 is inputs
       # bank 1 is outputs
       self.set_pullup(0, 0xFF)
       self.set_iodir(1, 0x00)

   def or_gpio(self, bank, bits):
        self.set_gpio(bank, self.gpio_bits[bank] | bits)

   def not_gpio(self, bank, bits):
        bits = ((~bits) & 0xFF)
        self.set_gpio(bank, self.gpio_bits[bank] & bits)

class PCF8574:
    def __init__(self, bus, addr):
        self.addr = addr
        self.bus = bus
        self.banks = 1
        self.gpio_bits = 0xFF

    def get_gpio(self, bank):
        return self.bus.read_byte(self.addr)

    def set_gpio(self, bank, value):
        self.bus.write_byte(self.addr, value)
        self.gpio_bits = value

    def configure_as_keypad(self):
        self.bus.write_byte(self.addr,0xFF)

    def or_gpio(self, bank, bits):
        self.set_gpio(bank, self.gpio_bits | bits)

    def not_gpio(self, bank, bits):
        bits = ((~bits) & 0xFF)
        self.set_gpio(bank, self.gpio_bits & bits)

