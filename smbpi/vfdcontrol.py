"""
    vfdcontrol.py

    Driver for Scott's VFD + Encoder pcboard

    http://www.smbaker.com/
"""

import math
import threading
import time
from ioexpand import MCP23017

BIT_ENC_A = 0x01
BIT_ENC_B = 0x02
BIT_ENC_SW = 0x04
BIT_ENC_BL = 0x08
BIT_ENC_GR = 0x10
BIT_ENC_RD = 0x20
BIT_BUTTON1 = 0x40
BIT_BUTTON2 = 0x80

BIT_RS = 0x01
BIT_E = 0x02
BIT_DB4 = 0x04
BIT_DB5 = 0x08
BIT_DB6 = 0x10
BIT_DB7 = 0x20
BIT_WR = 0x40
BIT_BUTTON3 = 0x80

COLOR_NONE = 0
COLOR_RED = BIT_ENC_RD
COLOR_GREEN = BIT_ENC_GR
COLOR_BLUE = BIT_ENC_BL
COLOR_WHITE = BIT_ENC_RD | BIT_ENC_GR | BIT_ENC_BL
COLOR_YELLOW = BIT_ENC_RD | BIT_ENC_GR
COLOR_CYAN = BIT_ENC_BL | BIT_ENC_GR
COLOR_MAGENTA = BIT_ENC_BL | BIT_ENC_RD

# amount of time to hold E high or low. Seems like 0 works just fine, the display can be clocked as fast as we can
# clock it.
E_TICK = 0 # 0.00001

class VFDController(object):

    def __init__(self, io):
        self.io = io

        self.lock = threading.Lock()

        self.io.set_iodir(0, BIT_ENC_A | BIT_ENC_B | BIT_ENC_SW | BIT_BUTTON1 | BIT_BUTTON2)
        self.io.set_iodir(1, BIT_BUTTON3)

        self.io.set_pullup(0, BIT_ENC_A | BIT_ENC_B | BIT_ENC_SW | BIT_BUTTON1 | BIT_BUTTON2)
        self.io.set_pullup(1, BIT_BUTTON3)

        self.io.set_gpio(1,0)

        # encoder init
        self.poll_input()
        self.last_delta = 0
        self.r_seq = self.rotation_sequence()
        self.steps_per_cycle = 4    # 4 steps between detents
        self.remainder = 0

        self.reset()

        self.poller = InputPoller(self)
        self.poller.start()

    def writeNibble(self, data, rs=0):
        self.io.set_gpio(1, rs | (data << 2) | BIT_E)    # raise E to write
        if (E_TICK): time.sleep(E_TICK)
        self.io.set_gpio(1, rs | (data << 2))            # clear E
        if (E_TICK): time.sleep(E_TICK)

    def readNibble(self, rs=0):
        self.io.set_gpio(1, rs | BIT_WR | BIT_E)
        if (E_TICK): time.sleep(E_TICK)
        v = (self.io.get_gpio(1) >> 2) & 0x0F
        self.io.set_gpio(1, rs | BIT_WR)
        if (E_TICK): time.sleep(E_TICK)
        return v

    def waitNotBusy(self):
        with self.lock:
            self.io.set_iodir(1, BIT_DB4 | BIT_DB5 | BIT_DB6 | BIT_DB7 | BIT_BUTTON3)
            self.io.set_gpio(1, BIT_WR)
            while True:
                v = self.readNibble(rs=0) << 4
                v = v + self.readNibble(rs=0)
                if (v & 0x80) == 0:
                    break
            self.io.set_gpio(1, 0)
            self.io.set_iodir(1, BIT_BUTTON3)


    def writeCmd(self, c):
        with self.lock:
            self.writeNibble(c>>4, rs=0)
            self.writeNibble(c&0x0F, rs=0)
        self.waitNotBusy()

    def writeData(self, c):
        with self.lock:
            self.writeNibble(c>>4, rs=1)
            self.writeNibble(c&0x0F, rs=1)
        #self.waitNotBusy()

    def writeStr(self, s):
        for c in s:
            self.writeData(ord(c))

    def reset(self):
        self.writeNibble(0x3, rs=0)
        time.sleep(0.02)
        self.writeNibble(0x3, rs=0)
        time.sleep(0.01)
        self.writeNibble(0x3, rs=0)
        time.sleep(0.001)

        self.writeNibble(0x2, rs=0)
        self.waitNotBusy()
        self.writeCmd(0x28)    # DL, 4-bit / 2-line
        self.setDisplay(display=True, cursor=True, blink=False)

    def cls(self):
        self.writeCmd(0x01)
        time.sleep(0.005)

    def setPosition(self, x, y):
        self.writeCmd(0x80 | (0x40*y + x))
        time.sleep(0.005)

    def setDirection(self, leftToRight, autoScroll):
        cmd = 4
        if leftToRight:
            cmd = cmd | 2
        if autoScroll:
            cmd = cmd | 1

        self.writeCmd(cmd)

    def setDisplay(self, display, cursor, blink):
        cmd = 8
        if display:
            cmd = cmd | 4
        if cursor:
            cmd = cmd | 2
        if blink:
            cmd = cmd | 1

        self.writeCmd(cmd)

    # -----------------------------------------------------------------------------------------------------------------
    # encoder stuff
    # -----------------------------------------------------------------------------------------------------------------

    def set_color(self, color):
        color = ~color & (BIT_ENC_RD | BIT_ENC_GR | BIT_ENC_BL)
        with self.lock:
            self.io.set_gpio(0, color)

    def poll_input(self):
        with self.lock:
            bits = self.io.get_gpio(0)
            bits1 = self.io.get_gpio(1)

        self.a_state = (bits & BIT_ENC_A) != 0
        self.b_state = (bits & BIT_ENC_B) != 0
        self.button_enc_state = (bits & BIT_ENC_SW) != 0
        self.button1_state = (bits & BIT_BUTTON1) != 0
        self.button2_state = (bits & BIT_BUTTON2) != 0
        self.button3_state = (bits1 & BIT_BUTTON3) != 0

    def rotation_sequence(self):
        r_seq = (self.a_state ^ self.b_state) | self.b_state << 1
        return r_seq

    # Returns offset values of -2,-1,0,1,2
    def get_delta(self):
        delta = 0
        r_seq = self.rotation_sequence()
        if r_seq != self.r_seq:
            delta = (r_seq - self.r_seq) % 4
            if delta==3:
                delta = -1
            elif delta==2:
                delta = int(math.copysign(delta, self.last_delta))  # same direction as previous, 2 steps

            self.last_delta = delta
            self.r_seq = r_seq

        return delta

    def get_cycles(self):
        self.remainder += self.get_delta()
        cycles = self.remainder // self.steps_per_cycle
        self.remainder %= self.steps_per_cycle # remainder always remains positive
        return cycles

    def get_switchstate(self):
        # BasicEncoder doesn't have a switch
        return 0

class Debouncer(object):
    # see http://www.embedded.com/electronics-blogs/break-points/4024981/My-favorite-software-debouncers
    #
    # I had some issues implementing the debouncer in this article, namely the step
    #     debounced_state = debounced_state ^j
    # This just oscillated for me, so I computed result=debounced_state^j and then set debounced_state to j
    # instead.

    def __init__(self):
        self.index = 0
        self.max_checks = 10
        self.state = []
        self.debounced_state = 0xFF
        for i in range(0, self.max_checks):
            self.state.append(0xFF)

    def debounce(self, in_state):
        # Computes new self.debounced_state, and returns a bitmask where a bit is true if that button went from 0
        # to 1.
        self.state[self.index] = in_state
        self.index += 1
        j = 0xFF
        for i in range(0, self.max_checks):
            j = j & self.state[i]
        res = (self.debounced_state ^ j) & j
        self.debounced_state = j
        if (self.index >= self.max_checks):
            self.index = 0
        return res

    def debounce_list(self, l):
        in_state = 0
        for x in l:
            in_state = in_state << 1
            if x:
                in_state = in_state | 1

        debounced_state = self.debounce(in_state)

        debounce_l = []
        for x in l:
            if (debounced_state & 1) != 0:
                debounce_l.append(True)
            else:
                debounce_l.append(False)
            debounced_state = debounced_state >> 1

        debounce_l.reverse()
        return debounce_l

class InputPoller(threading.Thread):
    def __init__(self, encoder):
        threading.Thread.__init__(self)
        self.lock = threading.Lock()
        self.stopping = False
        self.encoder = encoder
        self.daemon = True
        self.delta = 0
        self.delay = 0.001
        self.debouncer = Debouncer()

        self.button1_event = False
        self.button2_event = False
        self.button3_event = False
        self.button_enc_event = False

    def run(self):
        self.lastSwitchState = self.encoder.get_switchstate()
        while not self.stopping:
            self.encoder.poll_input()
            delta = self.encoder.get_cycles()
            with self.lock:
                self.delta += delta

                [button1_db, button2_db, button3_db, button_enc_db] = \
                    self.debouncer.debounce_list([self.encoder.button1_state,self.encoder.button2_state,
                                                 self.encoder.button3_state,self.encoder.button_enc_state])

                self.button1_event = self.button1_event or button1_db
                self.button2_event = self.button2_event or button2_db
                self.button3_event = self.button3_event or button3_db
                self.button_enc_event = self.button_enc_event or button_enc_db
            time.sleep(self.delay)

    # get_delta, get_upEvent, and get_downEvent return events that occurred on
    # the encoder. As a side effect, the corresponding event will be reset.

    def get_delta(self):
        with self.lock:
            delta = self.delta
            self.delta = 0
        return delta

    def get_button1_event(self):
        with self.lock:
            res = self.button1_event
            self.button1_event = False
        return res

    def get_button2_event(self):
        with self.lock:
            res = self.button2_event
            self.button2_event = False
        return res

    def get_button3_event(self):
        with self.lock:
            res = self.button3_event
            self.button3_event = False
        return res

    def get_button_enc_event(self):
        with self.lock:
            res = self.button_enc_event
            self.button_enc_event = False
        return res

    def set_color(self, color, v):
        self.encoder.set_color(color, v)

"""
    BufferedDisplay

    The start of a buffered display object, to only send the diff to the VFD. Needs work.
"""
class BufferedDisplay(object):
    def __init__(self, display):
        self.display = display

        self.width = 16
        self.height = 2

        self.buf_lines = [" " * self.width, " " * self.width]
        self.buf_last = [" " * self.width, " " * self.width]

    def bufSetPosition(self, x, y):
        buf_x = x
        buf_y = y

    def scroll(self):
        for i in range(0, self.height - 1):
            self.buf_lines[i] = self.buf_lines[i + 1]

    def bufWrite(self, str):
        for ch in str:
            self.buf_lines[self.buf_y][self.buf_x] = ch
            self.buf_x = self.buf_x + 1
            if (self.buf_x >= self.width):
                self.buf_x = 0
                self.buf_y = self.buf_y + 1
                if (self.buf_y >= self.height):
                    self.scroll()
                    self.buf_y = self.height-1
                    self.buf_lines[self.buf_y] = " " * self.width

    def bufUpdate(self):
        pass
        # implement this...

def trimpad(x, l):
    if len(x) < l:
        x = x + " " * (l-len(x))
    return x[:l]

""" 
    main: A simple datetime demo.
"""

def main():
    import smbus
    from datetime import datetime

    bus = smbus.SMBus(1)
    display = VFDController(MCP23017(bus, 0x20))

    display.setDisplay(True, False, False)
    display.cls()

    while True:
        (dates, times) = str(datetime.now()).split(" ")
        display.setPosition(0,0)
        display.writeStr(trimpad(dates,16))
        display.setPosition(0,1)
        display.writeStr(trimpad(times, 16))

        if display.poller.get_button1_event():
            print "button1"

        if display.poller.get_button2_event():
            print "button2"

        if display.poller.get_button3_event():
            print "button3"

        delta = display.poller.get_delta()
        if delta!=0:
            print delta

        time.sleep(0.01)


if __name__ == "__main__":
    main()