import crc8
import time
import traceback

class I2CError(Exception):
    pass

class ReceiveCRCError(Exception):
    pass

class ReceiveSizeError(Exception):
    pass

class ReceiveUninitializedError(Exception):
    pass

class CRCError(Exception):
    pass

class NoMoreRetriesError(Exception):
    pass

class UPS:
    def __init__(self, bus=None, addr=0x4, pi=None, sdaPin=2, sclPin=3):
        self.bus = bus
        self.addr = addr
        self.r1 = 10000
        self.r2 = 2200
        self.pi = pi
        self.sdaPin = sdaPin
        self.sclPin = sclPin

        self.errorIO = 0
        self.errorCRC = 0
        self.errorReceiveCRC = 0
        self.errorReceiveUninitialized = 0
        self.errorReceiveSize = 0
        self.errorSuccess = 0

        if (self.pi):
            try:
                self.pi.bb_i2c_close(self.sdaPin)
            except:
                pass
            # pigpiod
            self.pi.bb_i2c_open(self.sdaPin, self.sclPin, 100000)

        self.states = {0: "DISABLED",
                       1: "WAIT_OFF",
                       2: "WAIT_ON",
                       3: "ON",
                       4: "RUNNING",
                       5: "FAIL_SHUTDOWN",
                       6: "FAIL_SHUTDOWN_DELAY",
                       7: "CYCLE_DELAY"}

    @property
    def errorCount(self):
        return self.errorIO + self.errorReceiveCRC + self.errorReceiveUninitialized + self.errorReceiveSize + self.errorCRC

    def readreg_once(self, reg):
        if self.bus:
            hash = crc8.crc8()
            hash.update(chr(reg))
            crc = hash.digest()
            self.bus.write_i2c_block_data(self.addr, reg, [ord(crc)])

            data = self.bus.read_byte(self.addr)
            crc = self.bus.read_byte(self.addr)
        else:
            hash = crc8.crc8()
            hash.update(chr(reg))
            crc = hash.digest()
            (count, i2cdata) = self.pi.bb_i2c_zip(self.sdaPin, 
                (4, self.addr,      # set addr to self.addr
                2, 7, 2, reg, crc,  # start, write two byte (reg, crc)
                2, 6, 1,            # (re)start, read one byte
                2, 6, 1,            # (re)start, read one byte
                3,                  # stop
                0))                 # end 
            if count<0:
                raise I2CError("i2c error")
            if count!=2:
                raise I2CError("i2c wrong byte count")

            data = i2cdata[0]
            crc = i2cdata[1]

        if (data == 0xFF) and (crc == 0xFF):
            raise ReceiveCRCError("receive crc error")
        if (data == 0xFF) and (crc == 0xFE):
            raise ReceiveSizeError("receive size error")
        if (data == 0xFF) and (crc == 0xFD):
            raise ReceiveUninitializedError("receive uninitialized error")

        hash = crc8.crc8()
        hash.update(chr(data))
        if crc != ord(hash.digest()):
            raise CRCError("crc error, data=%2X, crc=%2X, localCrc=%X" % (data, crc, ord(hash.digest())))

        return data

    def writereg_once(self, reg, v):
        if self.bus:
            hash = crc8.crc8()
            hash.update(chr(reg))
            hash.update(chr(v))
            crc = hash.digest()
            self.bus.write_i2c_block_data(self.addr, reg, [v, ord(crc)])

            readBack = self.bus.read_byte(self.addr)
            crc = self.bus.read_byte(self.addr)
        else:
            hash = crc8.crc8()
            hash.update(chr(reg))
            hash.update(chr(v))
            crc = hash.digest()
            (count, i2cdata) = self.pi.bb_i2c_zip(self.sdaPin, 
                (4, self.addr,         # set addr to self.addr
                2, 7, 3, reg, v, crc,  # start, write three bytes (reg, v, crc)
                2, 6, 1,            # (re)start, read one byte
                2, 6, 1,            # (re)start, read one byte
                3,                  # stop
                0))                 # end 
            if count<0:
                raise I2CError("i2c error")
            if count!=2:
                raise I2CError("i2c wrong byte count")

            readBack = i2cdata[0]
            crc = i2cdata[1]

        # note that readBack will actually return the next register. But,
        # that's alright, we don't care -- we just want to check to make
        # sure we didn't get an error back.

        if (readBack == 0xFF) and (crc == 0xFF):
            raise ReceiveCRCError("receive crc error")
        if (readBack == 0xFF) and (crc == 0xFE):
            raise ReceiveSizeError("receive size error")
        if (readBack == 0xFF) and (crc == 0xFD):
            raise ReceiveUninitializedError("receive uninitialized error")

        hash = crc8.crc8()
        hash.update(chr(readBack))
        if crc != ord(hash.digest()):
            raise CRCError("crc error, readBack=%2X, crc=%2X, localCrc=%X" % (readBack, crc, ord(hash.digest())))

    def readreg(self, reg):
        for i in range(0, 10):
            try:
                v = self.readreg_once(reg)
                self.errorSuccess += 1
                return v
            except I2CError:
                self.errorIO += 1
            except IOError:
                self.errorIO += 1
            except ReceiveCRCError:
                self.errorReceiveCRC += 1
            except ReceiveSizeError:
                self.errorReceiveSize += 1
            except ReceiveUninitializedError:
                self.errorReceivedUninitialized += 1
            except CRCError:
                self.errorCRC += 1
        raise NoMoreRetriesError()

    def writereg(self, reg, v):
        for i in range(0, 10):
            try:
                self.writereg_once(reg, v)
                self.errorSuccess += 1
                return
            except I2CError:
                self.errorIO += 1
            except IOError:
                self.errorIO += 1
            except ReceiveCRCError:
                self.errorReceiveCRC += 1
            except ReceiveSizeError:
                self.errorReceiveSize += 1
            except ReceiveUninitializedError:
                self.errorReceivedUninitialized += 1
            except CRCError:
                self.errorCRC += 1
            except TypeError:
                pass
        raise NoMoreRetriesError()

    def vConv(self, x):
        return float(x)*2.56*(self.r1+self.r2)/self.r2/256.0

    def setCountdown(self, ms):
        if (ms is not None) and (ms>0) and (ms<100):
            # the minimum is 100ms
            ms=100
        return self.writereg(9, ms/100)

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
