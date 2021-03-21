from __future__ import print_function
import sys
import time

# MSR is CS=FDC, A0=0
# DATA is CS=FDC, A0=1
# DOR is CS=DOR
# DCR is CS=DCR

import wd37c65_direct_ext

FDM144 = 1
FDM360 = 2

FRC_OK = 0
FRC_NOTIMPL = 1
FRC_CMDERR = 2
FRC_ERROR = 3
FRC_ABORT = 4
FRC_BUFMAX = 5
FRC_ABTERM = 8
FRC_INVCMD = 9
FRC_DSKCHG = 0x0A
FRC_ENDCYL = 0x0B
FRC_DATAERR = 0x0C
FRC_OVERRUN = 0x0D
FRC_NODATA = 0x0E
FRC_NOTWRIT = 0x0F
FRC_MISADR = 0x10
FRC_TOFDRRDY = 0x11
FRC_TOSNDCMD = 0x12
FRC_TOGETRES = 0x13
FRC_TOEXEC = 0x14
FRC_TOSEEKWT = 0x15
FRC_OVER_DRAIN = 0x16
FRC_OVER_CMDRES = 0x17
FRC_TO_READRES = 0x18
FRC_READ_ERROR = 0x19

CFD_READ	 =	0B00000110	# CMD,HDS/DS,C,H,R,N,EOT,GPL,DTL --> ST0,ST1,ST2,C,H,R,N
CFD_READDEL	 =	0B00001100	# CMD,HDS/DS,C,H,R,N,EOT,GPL,DTL --> ST0,ST1,ST2,C,H,R,N
CFD_WRITE	 =	0B00000101	# CMD,HDS/DS,C,H,R,N,EOT,GPL,DTL --> ST0,ST1,ST2,C,H,R,N
CFD_WRITEDEL =	0B00001001	# CMD,HDS/DS,C,H,R,N,EOT,GPL,DTL --> ST0,ST1,ST2,C,H,R,N
CFD_READTRK	 =	0B00000010	# CMD,HDS/DS,C,H,R,N,EOT,GPL,DTL --> ST0,ST1,ST2,C,H,R,N
CFD_READID	 =	0B00001010	# CMD,HDS/DS --> ST0,ST1,ST2,C,H,R,N
CFD_FMTTRK	 =	0B00001101  # CMD,HDS/DS,N,SC,GPL,D --> ST0,ST1,ST2,C,H,R,N
CFD_SCANEQ	 =	0B00010001	# CMD,HDS/DS,C,H,R,N,EOT,GPL,STP --> ST0,ST1,ST2,C,H,R,N
CFD_SCANLOEQ =	0B00011001	# CMD,HDS/DS,C,H,R,N,EOT,GPL,STP --> ST0,ST1,ST2,C,H,R,N
CFD_SCANHIEQ =	0B00011101	# CMD,HDS/DS,C,H,R,N,EOT,GPL,STP --> ST0,ST1,ST2,C,H,R,N
CFD_RECAL	 =  0B00000111	# CMD,DS --> <EMPTY>
CFD_SENSEINT =  0B00001000	# CMD --> ST0,PCN
CFD_SPECIFY	 =  0B00000011	# CMD,SRT/HUT,HLT/ND --> <EMPTY>
CFD_DRVSTAT	 =  0B00000100	# CMD,HDS/DS --> ST3
CFD_SEEK	 =  0B00001111	# CMD,HDS/DS --> <EMPTY>
CFD_VERSION	 =  0B00010000	# CMD --> ST0

class FDCException(Exception):
    def __init__(self, fstRC, msg=None):
        if not msg:
            msg="FDC Exception %2X" % fstRC
        Exception.__init__(self, msg)
        self.fstRC = fstRC

class FDC:
    def __init__(self):
        self.DOR_INIT = 0B00001100
        self.DOR_BR250 = self.DOR_INIT
        self.DOR_BR500 = self.DOR_INIT
        self.DCR_BR250 = 1
        self.DCR_BR500 = 0

        # dynamic
        self.ds = 0
        self.cyl = 0
        self.head = 0
        self.record = 0
        self.fillByte = 0xE5
        self.dop = 0
        self.idleCount = 0
        self.to = 0
        self.fdcReady = False

        # unit data
        self.track = 0xFF

        self.dor = 0

        self.set144()

    def set360(self):
        self.numCyl = 0x28
        self.numHead = 2
        self.numSec = 9
        self.sot = 1
        self.secCount = 9
        self.secSize = 0x200
        self.gapLengthRW = 2
        self.gapLengthFormat = 0x50
        self.stepRate = (13 << 4) | 0  # srtHut
        self.headLoadTimeNonDma = (4 << 1) | 1  # hltNd
        self.DOR = self.DOR_BR250
        self.DCR = self.DCR_BR250
        self.media = FDM360

    def set144(self):
        self.numCyl = 0x50
        self.numHead = 2
        self.numSec = 0x12
        self.sot = 1
        self.secCount = 0x12
        self.secSize = 0x200
        self.gapLengthRW = 0x1B
        self.gapLengthFormat = 0x6C
        self.stepRate = (13 << 4) | 0  # srtHut
        self.headLoadTimeNonDma = (8 << 1) | 1  # hltNd
        self.DOR = self.DOR_BR500
        self.DCR = self.DCR_BR500
        self.media = FDM144

    def log(self,x):
        print(x)

    # ------------ chip funcs -----------------

    def readDataBlock(self, count):
        self.log(">>> readdatablock")
        status, blk = wd37c65_direct_ext.read_block(count)
        self.log(">>> readdatablock status %02X, len %d" % (status, len(blk)))
        if status not in [FRC_OK, FRC_READ_ERROR]:
            raise FDCException(status)

        self.dskBuf = blk

    def writeDataBlock(self, count):
        status = wd37c65_direct_ext.write_block(self.dskBuf, count)
        if status != 0:
            raise FDCException(status)

    def writeData(self, d):
        wd37c65_direct_ext.write_data(d)

    def drain(self):
        status = wd37c65_direct_ext.drain()
        if status != 0:
            raise FDCException(status)

    def wait_msr(self, mask, val):
        status = wd37c65_direct_ext.wait_msr(mask, val)
        if status != 0:
            raise FDCException(status)

    def readResult(self):
        self.log("readResult enter")
        status, blk = wd37c65_direct_ext.read_result()
        if status != 0:
            raise FDCException(status)

        self.frb = blk
        self.frbLen = len(self.frb)

        self.log("readResult done")

    def resetFDC(self):
        wd37c65_direct_ext.reset(self.dor)

    def initFDC(self):
        wd37c65_direct_ext.init()

    def writeDOR(self, dor):
        wd37c65_direct_ext.write_dor(dor)
        self.dor = dor

    def writeDCR(self, dcr):
        wd37c65_direct_ext.write_dcr(dcr)
        self.dcr = dcr
    
    # -----------------------------------------

    def init(self):
        self.fcpBuf = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.idleCount = 0
        self.dor = self.DOR_INIT
        self.initFDC()
        self.resetFDC()
        #self.writeDOR(0x1C)

        #self._setupIO(CFD_READ | 0B11100000)
        #return self._fop()

        #raise Exception()
        self._clearDiskChange()
        self.fdcReady = True

    def _reset():
        self.resetFDC()
        self._clearDiskChange()
        self.track = 0xFF  # mark needing recal

    def read(self, cyl=None, head=None, record=None):
        if cyl:
            self.cyl = cyl
        if head:
            self.head = head
        if record:
            self.record = record

        self._start()
        if (self.fstRC != FRC_OK):
            return self.fstRC

        self._setupIO(CFD_READ | 0B11100000)
        return self._fop()

    def write(self, cyl=None, head=None, record=None):
        if cyl:
            self.cyl = cyl
        if head:
            self.head = head
        if record:
            self.record = record

        self._start()
        if (self.fstRC != FRC_OK):
            return self.fstRC

        self._setupIO(CFD_WRITE | 0B11000000)
        return self._fop()

    def readID(self):
        self._setupCommand(CFD_READID | 0B01000000)
        return self._fop()

    def _recal(self):
        self._setupCommand(CFD_RECAL)
        return self._fop()

    def _senseInt(self):
        self._setupCommand(CFD_SENSEINT)
        self.fcpLen = 1
        return self._fop()       

    def _specify(self, stepRate=None, headLoadTimeNonDma=None):
        if stepRate:
            self.stepRate = stepRate
        if headLoadTimeNonDma:
            self.headLoadTimeNonDma = headLoadTimeNonDma
        self._setupSpecify()
        return self._fop()

    def _seek(self):
        self._setupSeek()
        return self._fop()

    def _start(self):
        if not self.fdcReady:
            self.log(">>> start:reset")
            self._reset()
            if self.fstRC != FRC_OK:
                return self.fstRC

        self._motorOn()

        if self.track == 0xFF:
            self.log(">>> start:driveReset")
            self._driveReset()
            if self.fstRC != FRC_OK:
                return self.fstRC

        if self.track != self.cyl:
            self.log(">>> start:seek (%d,%d)" % (self.track, self.cyl))
            self._seek()
            if self.fstRC != FRC_OK:
                return self.fstRC
            self._waitSeek()
            if self.fstRC != FRC_OK:
                return self.fstRC
            self.track = self.cyl            


        self.fstRC = FRC_OK
        return self.fstRC

    def _driveReset(self):
        self.log(">>> driveReset:specify")
        self._specify()
        if self.fstRC != FRC_OK:
            return self.fstRC

        self.log(">>> driveReset:recal")
        self._recal()
        if self.fstRC != FRC_OK:
            return self.fstRC

        self.log(">>> driveReset:waitseek1")
        self._waitSeek()
        if (self.fstRC == FRC_OK):
            # succeeded!
            return self.fstRC

        # try once more
        self.log(">>> driveReset:waitseek2")
        self._waitSeek()   
        return self.fstRC

    def _motorOn(self):
        # DOR bit 0 is DS, either 0 or 1
        # DOR bit 4 is motor enable for ds0
        # DOR bit 5 is motor enable for ds1
        motorMask = (1 << (self.ds+4))
        self.writeDOR(self.dor & 0B11111100 | self.ds | motorMask)
        self.writeDCR(self.DCR)

        if (self.dor & motorMask)==0:
            self.log(">>> motor delay")
            # motor delay
            time.sleep(1)


    def _clearDiskChange(self):
        for i in range(0, 5):
            self._senseInt()
            if (self.fstRC & FRC_DSKCHG) == 0:
                return
        # I think we can just ignore the remaining ones

    def _setupCommand(self, cmd):
        self.fcpBuf[0] = cmd & 0x5F
        self.fcpCmd = (cmd & 0x5F) & 0B00011111
        self.fcpBuf[1] = ((self.head & 0x1)<<2) | (self.ds & 0x3)
        self.fcpLen = 2

    def _setupSeek(self):
        self._setupCommand(CFD_SEEK)
        self.fcpBuf[2] = self.cyl
        self.fcpLen = 3

    def _setupSpecify(self):
        self._setupCommand(CFD_SPECIFY)
        self.fcpBuf[1] = self.stepRate
        self.fcpBuf[2] = self.headLoadTimeNonDma
        self.fcpLen = 3

    def _setupIO(self, cmd):
        self._setupCommand(cmd)
        self.fcpBuf[2] = self.cyl
        self.fcpBuf[3] = self.head
        self.fcpBuf[4] = self.record
        self.fcpBuf[5] = 2 # sector size, 512 bytes
        self.fcpBuf[6] = self.sot
        self.fcpBuf[7] = self.gapLengthRW
        self.fcpBuf[8] = self.gapLengthFormat
        self.fcpLen = 9

    def _fop(self):
        try:
            fcpBytes = []
            for i in range(0, self.fcpLen):
                fcpBytes.append("%02X" % self.fcpBuf[i])

            self.log("FOP %s ->" % (" ".join(fcpBytes)))

            result = self._fop_internal()

            frbBytes = []
            for i in range(0, self.frbLen):
                frbBytes.append("%02X" % ord(self.frb[i]))
            self.log("      -> %s" % (" ".join(frbBytes)))

            print("_fop result: %02X" % result)
            return result
        except FDCException, e:
            print("Exception in _Fop %s, code %2X" % (e, e.fstRC), file=sys.stderr)
            self.fstRC = e.fstRC
            return self.fstRC

    def _fop_internal(self):
        self.frbLen = 0
        self.fstRC = FRC_OK

        self.drain()

        self.log("FOP sending command")

        for i in range(0, self.fcpLen):
            # DIO=0 and RQM=1 indicate byte is ready to write
            self.wait_msr(0xC0, 0x80)
            self.writeData(self.fcpBuf[i])

        #fcpStr = ""
        #for i in range(0, self.fcpLen):
        #    fcpStr = fcpStr + chr(self.fcpBuf[i])
        #wd37c65_direct_ext.write_command(fcpStr, self.fcpLen)

        self.log("FOP sent command")

        if (self.fcpCmd == CFD_READ):
            self.readDataBlock(self.secSize)
        elif (self.fcpCmd == CFD_WRITE):
            self.writeDataBlock(self.secSize)
        elif (self.fcpCmd == CFD_READID):
            self.waitMSR(0xE0, 0xC0)
        else:
            pass  # null

        self.frb = ""
        self.readResult()

        if (self.fcpCmd == CFD_DRVSTAT):
            # driveState has nothing to evaluate
            return self.fstRC
        elif (self.frbLen == 0):
            # if there's no st0, then nothing to evaluate
            return self.fstRC

        st0 = ord(self.frb[0])
        if (st0 & 0B11000000) == 0B01000000:
            # ABTERM
            if (self.fcpCmd == CFD_SENSEINT) or (self.frbLen == 1):
                # Senseint doesn't use ST1
                self.fstRC = FRC_ABTERM
                return self.fstRC

            # evalst1
            st1 = ord(self.frb[1])
            if (st1 & 80) == 0x80:
                self.fstRC = FRC_ENDCYL
            elif (st1 & 0x20) == 0x20:
                self.fstRC = FRC_DATAERR
            elif (st1 & 0x10) == 0x10:
                self.fstRC = FRC_OVERRUN
            elif (st1 & 0x04) == 0x08:
                self.fstRC = FRC_NODATA
            elif (st1 & 0x02) == 0x04:
                self.fstRC = FRC_NOWRIT
            elif (st1 & 0x01) == 0x01:
                self.fstRC = FRC_MISADR
            
            return self.fstRC
        elif (st0 & 0B11000000) == 0B10000000:
            # INVCMD
            self.fstRC = FRC_INVCMD
            return self.fstRC
        elif (st0 & 0B11000000) == 0B11000000:
            # DSKCHG
            self.fstRC = FRC_DSKCHG
            return self.fstRC

        print("YYY %d" % self.fstRC)

        # no error bits are set

        return self.fstRC

    def _waitSeek(self):
        loopCount = 0x1000
        while (loopCount>0):
            self._senseInt()
            if self.fstRC == FRC_ABTERM:
                # seek error
                return self.fstRC
            elif self.fstRC == FRC_OK:
                return self.fstRC
            loopCount -= 1

        self.fstRC = FRC_TOSEEKWT
        return self.fstRC

