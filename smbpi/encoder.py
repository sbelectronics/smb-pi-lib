import math
import threading
import time
import traceback
import RPi.GPIO as GPIO

# pin numbers from scott's e-paper project

PIN_ENC_A = 20
PIN_ENC_B = 21

PIN_ENC_A2 = 12
PIN_ENC_B2 = 16

class EncoderHandler(object):

    def __init__(self, pin_a=PIN_ENC_A, pin_b=PIN_ENC_B, pin_button=None, pud=GPIO.PUD_OFF, button_pud=None, min_pos=None, max_pos=None, invert=False, num=0, thread=None):
        self.num = num
        self.thread = thread
        self.pin_enc_a = pin_a
        self.pin_enc_b = pin_b
        self.pin_button = pin_button
        self.min_position = min_pos
        self.max_position = max_pos
        self.invert = invert
        GPIO.setup(self.pin_enc_a, GPIO.IN, pull_up_down=pud)
        GPIO.setup(self.pin_enc_b, GPIO.IN, pull_up_down=pud)

        if not button_pud:
            button_pud = pud
            
        if self.pin_button:
            GPIO.setup(self.pin_button, GPIO.IN, pull_up_down=button_pud)

        self.a_state = 0
        self.b_state = 0
        self.button_state = 1

        self.position = 0
        self.delta = 0

        # button history
        self.last_button_poll_state = self.button_state
        self.button_up_event = False
        self.button_down_event = False

        # encoder init
        self.poll_input()
        self.last_delta = 0
        self.r_seq = self.rotation_sequence()
        self.steps_per_cycle = 4    # 4 steps between detents
        self.remainder = 0

    def poll_input(self):
        self.a_state = GPIO.input(self.pin_enc_a)
        self.b_state = GPIO.input(self.pin_enc_b)
        if self.pin_button:
            self.button_state = GPIO.input(self.pin_button)

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
        if self.invert:
            cycles = -cycles
        return cycles

    def update(self):
        delta = self.get_cycles()
        self.delta += delta
        self.position += delta
        if (self.min_position is not None) and (self.position < self.min_position):
            self.position = self.min_position
        if (self.max_position is not None) and (self.position > self.max_position):
            self.position = self.max_position
        return delta

    def update_button(self):
        something_happened = False
        if self.button_state != self.last_button_poll_state:
            self.last_button_poll_state = self.button_state
            if self.button_state:
                if not self.button_up_event:
                    self.button_up_event = True
                    something_happened = True
            else:
                if not self.button_down_event:
                    self.button_down_event = True
                    something_happened = True
        return something_happened

class EncoderThread(threading.Thread):
    def __init__(self, encoders, store_points=False):
        super(EncoderThread,self).__init__()
        self.delay = 0.0001
        self.daemon = True
        self.store_points = store_points
        self.points = []
        self.lock = threading.Lock()
        self.handlers=[]
        for encoder in encoders:
            handler = EncoderHandler(num=len(self.handlers), thread=self, **encoder)
            self.handlers.append(handler)

    def updated(self, handler):
        # override me
        pass

    def run(self):
        while True:
            need_notify = []
            something_changed = False
            for handler in self.handlers:
                handler.poll_input()
                with self.lock:
                    delta = handler.update()
                    if delta != 0:
                        something_changed = True
                        need_notify.append(handler)

                    if handler.update_button():
                        if handler not in need_notify:
                            need_notify.append(handler)

            # this stores a vector of all encoders, so they can be read at once
            if (self.store_points) and (something_changed):
                point = []
                with self.lock:
                    for handler in self.handlers:
                        point.append(handler.position)
                    self.points.append(point)

            # call these outside of self.lock
            for handler in need_notify:
                self.updated(handler)

            time.sleep(self.delay)

    def get_delta(self, num):
        with self.lock:
            delta = self.handlers[num].delta
            self.handlers[num].delta = 0
        return delta

    def get_button_down_event(self, num):
        with self.lock:
            event = self.handlers[num].button_down_event
            self.handlers[num].button_down_event = False
        return event

    def get_button_up_event(self, num):
        with self.lock:
            event = self.handlers[num].button_up_event
            self.handlers[num].button_up_event = False
        return event

    def get_position(self, num):
        return self.handlers[num].position

    def get_points(self):
        with self.lock:
            points = self.points[:]
            self.points = []
        return points
""" 
    main: 
"""

def main():
    GPIO.setmode(GPIO.BCM)

    encoder = EncoderThread(encoders
                            =[{"pin_a": PIN_ENC_A, "pin_b": PIN_ENC_B},
                              {"pin_a": PIN_ENC_A2, "pin_b": PIN_ENC_B2}],
                            store_points = True)
    #encoder = EncoderThread(encoders
    #                        =[{"pin_a": 18, "pin_b": 23, "pud": GPIO.PUD_UP},
    #                          ],
    #                        store_points = True)
    encoder.start()

    last_delta = 0
    last_position = 0
    last_delta2 = 0
    last_position2 = 0
    while True:
        points = encoder.get_points()
        if points:
            print points
        """
        delta = encoder.get_delta(0)
        position = encoder.get_position(0)
        delta2 = encoder.get_delta(1)
        position2 = encoder.get_position(1)
        if (delta!=last_delta) or (position!=last_position) or (delta2!=last_delta2) or (position!=last_position2):
            print position, delta, position2, delta2
            last_delta = delta
            last_position = position
            last_delta2 = delta2
            last_position2 = position2
        """
        time.sleep(0.01)


if __name__ == "__main__":
    main()