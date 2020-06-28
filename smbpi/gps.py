import pigpio
import sys

DEFAULT_PIN_TX = 23
DEFAULT_PIN_RX = 24

class GPS:
    def __init__(self, pi, tx=DEFAULT_PIN_TX, rx=DEFAULT_PIN_RX):
        self.pi = pi
        self.tx = tx
        self.rx = rx

        self.hours = 0
        self.minutes = 0
        self.seconds = 0
        self.hundredths = 0
        self.day = 0
        self.year = 0
        self.month = 0

        self.pi.set_mode(self.tx, pigpio.INPUT)

        try:
            self.pi.bb_serial_read_close(self.tx)
        except:
            pass

        self.pi.bb_serial_read_open(self.tx, 9600, 8)

    # $GPRMC,041841.00,A,4401.29549,N,12308.03025,W,0.415,,280620,,,A*6A

    def parseGPRMC(self, line):
        line = line[7:]
        if len(line)<9:
            return

        parts = line.split(",")

        timeStr = parts[0]
        if len(timeStr) < 6:
            return

        self.hours = int(timeStr[0:2])
        self.minutes = int(timeStr[2:4])
        self.seconds = int(timeStr[4:6])

        if timeStr[6] == ".":
            self.hundredths = int(timeStr[7:9])
        else:
            self.hundredths = 0

        # parts[8] is the date
        if len(parts)>=9:
            dateStr = parts[8]
            self.day = int(dateStr[0:2])
            self.month = int(dateStr[2:4])
            self.year = 2000 + int(dateStr[4:6])

        print "%02d:%02d:%02d.%02d %02d-%02d-%02d" % \
            (self.hours, self.minutes, self.seconds, self.hundredths,
             self.month, self.day, self.year)

    def parseLine(self, line):
        if line.startswith("$GPRMC"):
            self.parseGPRMC(line)

    def readInput(self):
        buf=""
        while True:
            (count, data) = self.pi.bb_serial_read(self.tx)
            if count>0:
                for d in data:
                    d = chr(d)
                    if d=="\r":
                        pass
                    elif d=="\n":
                        self.parseLine(buf)
                        buf=""
                    else:
                        buf = buf + d

    def streamToConsole(self):
        while True:
            (count, data) = self.pi.bb_serial_read(self.tx)
            if count>0:
                for d in data:
                    sys.stdout.write(chr(d))


def main():
    pi = pigpio.pi()
    g = GPS(pi)
    g.readInput()


if __name__ == "__main__":
    main()


