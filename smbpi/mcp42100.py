"""
    MCP42100 driver
    Scott Baker, http://www.smbaker.com/

    Interface with MCP42100 chip.
"""


DEFAULT_CS = 0


class MCP42100:
    def __init__(self, spi, bus=0, cs=DEFAULT_CS):
        self.spi = spi
        self.bus = bus
        self.cs = cs
        self.spi.open(self.bus, self.cs)

    def SetValue(self, potNum, val):
        self.spi.xfer2([0x11+potNum, val])


def main():
    import spidev
    import sys
    if len(sys.argv)<=2:
        print >> sys.stderr, "Please specify pot and value as command-line arg"
        sys.exit(-1)

    p = int(sys.argv[1])
    v = int(sys.argv[2])

    spi = spidev.SpiDev()
    try:
        pot = MCP42100(spi)

        pot.SetValue(p, v)
    finally:
        spi.close()


if __name__ == "__main__":
    main()
