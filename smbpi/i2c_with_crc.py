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

class I2CWithCrc:
    def __init__(self, bus=None, addr=0x4, pi=None, sdaPin=2, sclPin=3):
        self.bus = bus
        self.addr = addr
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

    # different capitalization
    def readReg(self, reg):
        return self.readreg(reg)

    # different capitalization
    def writeReg(self, reg, v):
        self.writereg(reg, v)