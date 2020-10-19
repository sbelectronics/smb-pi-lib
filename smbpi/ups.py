import crc8
import time
import traceback

from ic2_with_crc import I2CWithCrc, I2CError, ReceiveCRCError, ReceiveSizeError, ReceiveUninitializedError, CRCError, NoMoreRetriesError

class UPS(I2CWithCrc):
    def __init__(self, bus=None, addr=0x4, pi=None, sdaPin=2, sclPin=3):
        I2CWithCrc.__init__(self, bus, addr, pi, sdaPin, sclPin)

        try:
            self.r1 = self.readR1()
            self.r2 = self.readR2()
            print "XXX", self.r1, self.r2
        except:
            print "WARNING: Failed to read R1 and R2"
            traceback.print_exc()

        self.states = {0: "DISABLED",
                       1: "WAIT_OFF",
                       2: "WAIT_ON",
                       3: "POWERUP",
                       4: "RUNNING",
                       5: "FAIL_SHUTDOWN",
                       6: "FAIL_SHUTDOWN_DELAY",
                       7: "CYCLE_DELAY"}

    def vConv(self, x):
        return float(x)*2.56*(self.r1+self.r2)/self.r2/256.0

    def setCountdown(self, ms):
        if (ms is not None) and (ms>0) and (ms<100):
            # the minimum is 100ms
            ms=100
        return self.writereg(9, ms/100)

    def readR1(self):
        return self.readreg(16)

    def readR2(self):
        return self.readreg(17)

    def readCountdown(self):
        return self.readreg(9)

    def readVIN(self):
        return self.vConv(self.readreg(3))

    def readVUPS(self):
        return self.vConv(self.readreg(5))

    def readOnThresh(self):
        return self.vConv(self.readreg(7))

    def readOffThresh(self):
        return self.vConv(self.readreg(8))

    def readPowerUpThresh(self):
        return self.vConv(self.readreg(14))        

    def readShutdownThresh(self):
        return self.vConv(self.readreg(15))

    def readMosfet(self):
        return self.readreg(6)

    def setMosfet(self, v):
        self.writeReg(6, v)

    def readState(self):
        return self.readreg(10)

    def readRunCounter(self):
        return self.readreg(13)

    def readStateStr(self):
        state = self.readState()
        return self.states.get(state, str(state))

    def testWrite(self, x):
        self.writereg(0, x)

def diags(ups):
    print ups.readreg(0), ups.readreg(2), ups.readreg(4), ups.readreg(6), ups.readreg(7), ups.readreg(8)
    print "onThresh=%0.2f, offThresh=%0.2f" % (ups.readOnThresh(), ups.readOffThresh())

    lastVUPS = None
    lastVIN = None
    lastState = None
    lastCountdown = None
    lastErrorCount = 0
    count = 0
    while True:
        try:
            VUPS = ups.readVUPS()
            VIN = ups.readVIN()
            state = ups.readStateStr()
            runCounter = ups.readRunCounter()
            countdown = ups.readCountdown()
        except NoMoreRetriesError:
            continue

        try:
            ups.testWrite(count % 256)
        except NoMoreRetriesError:
            pass

        if (VUPS != lastVUPS) or (VIN != lastVIN) or (state != lastState) or (countdown != lastCountdown):
            print "%-20s, vin=%0.2f, vups=%0.2f rc=%d cd=%d" % (state, VIN, VUPS, runCounter, countdown)
            lastVUPS = VUPS
            lastVIN = VIN
            state = lastState

        errorCount = ups.errorCount
        if errorCount != lastErrorCount:
            print "ERR: success=%d, io=%d, crc=%d, rcv_crc=%d, rcv_size=%d, rcv_uninit=%d" % (ups.errorSuccess, ups.errorIO, ups.errorCRC, ups.errorReceiveCRC, ups.errorReceiveSize, ups.errorReceiveUninitialized)
            lastErrorCount = errorCount

        time.sleep(0.01)

def main():
    #import smbus
    #bus = smbus.SMBus(1)
    #ups = UPS(bus=bus)

    import pigpio
    pi = pigpio.pi()
    ups = UPS(pi=pi)

    diags(ups)


if __name__ == "__main__":
    main()
