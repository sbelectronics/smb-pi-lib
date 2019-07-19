# fan4pin.py
# Scott Baker, http://www.smbaker.com/
#
# 4pin fan driver using pigpiod.
#
# Uses a hardware pwm pin (GPIO18) to smoothly run fan
# Optionally supports RPM readback
#
# Tested using a delta ASB0305HP-00CP4
#
# Requires pigpiod installed

import pigpio
import sys

FAN_PWM_PIN = 18
FAN_RPM_PIN = 23


class Fan4Pin(object):
    def __init__(self, pi, pin=FAN_PWM_PIN, pin_rpm=FAN_RPM_PIN, weighting=0.1):
        self.pi = pi
        self.pin = pin
        self.pin_rpm = pin_rpm
        self.pwm = 0
        self._freq = 25000

        # Since we're using hardware PWM, limit to a pin that supports it
        if (self.pin not in [12, 13, 18, 19]):
            print >> sys.stderr, "Only support PWM on 12, 13, 18, or 19"
            sys.exit(-1)

        if (self.pin_rpm):
            self.pulses_per_rev = 2
            self._new = 1.0 - weighting
            self._old = weighting
            self._high_tick = None
            self._period = None
            self._watchdog = 200
            self._rpm_callback_enabled = False
            self.pi.set_mode(self.pin_rpm, pigpio.INPUT)
            self.pi.set_pull_up_down(self.pin_rpm, pigpio.PUD_UP)
            self.enable_rpm()

        self.set_pwm(255)

    def _set_pwm(self, v):
        # v is a value between 0 and 255
        print "XXX", v, self.pin, self._freq, v*1000/255
        self.pi.hardware_PWM(self.pin, self._freq, v*1000000/255)

    def set_pwm(self, v):
        self._set_pwm(v)
        self.pwm = v

    def _rpm_callback_handler(self, pin, level, tick):
        if not self._rpm_callback_enabled:
            return

        if level == 1:  # Rising edge.
            if self._high_tick is not None:
                t = pigpio.tickDiff(self._high_tick, tick)

                if t > 0:
                    # compute an rpm for bounds checking
                    t_rpm = 60000000.0 / (t * self.pulses_per_rev)
                else:
                    t_rpm = 0

                if (t_rpm > 12500) or (t_rpm < 100):
                    # abnormal reading, discard
                    pass
                else:
                    if self._period is not None:
                        self._period = (self._old * self._period) + (self._new * t)
                    else:
                        self._period = t

            self._high_tick = tick

        elif level == 2:  # Watchdog timeout.
            if self._period is not None:
                if self._period < 2000000000:
                    self._period += (self._watchdog * 1000)

    def enable_rpm(self):
        self._high_tick = None
        self._rpm_callback = self.pi.callback(self.pin_rpm, pigpio.RISING_EDGE, self._rpm_callback_handler)
        self._rpm_callback_enabled = True

    def disable_rpm(self):
        if self._rpm_callback:
            self._rpm_callback_enabled = False
            self._rpm_callback.cancel()
            self._rpm_callback = None

    def get_fan_rpm(self):
        if self._period is not None:
            return 60000000.0 / (self._period * self.pulses_per_rev)
        else:
            return 0

    def get_rpm(self):
        return self.get_fan_rpm()

    def report_rpm(self, rpm):
        pass


def main():
    import time

    pi = pigpio.pi()

    fan = Fan4Pin(pi)

    if len(sys.argv) > 1:
        fan.set_pwm(int(sys.argv[1]))

    while True:
        print "rpm", int(fan.get_rpm())
        time.sleep(1)


if __name__ == "__main__":
    main()
