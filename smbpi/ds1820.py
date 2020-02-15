import os
import sys
import traceback

DEVICE_DIR = "/sys/bus/w1/devices"


class DS1820:
    def __init__(self):
        self.find_devices()

    def find_devices(self):
        self.devices = []
        for fn in os.listdir(DEVICE_DIR):
            # literature says 28-, but mine are 10-
            if fn.startswith("10-") or fn.startswith("28-"):
                self.devices.append(fn)

    def measure_device(self, name):
        try:
            fn = os.path.join(DEVICE_DIR, name, "w1_slave")
            if not os.path.exists(fn):
                return None
            f = open(fn)
            firstLine = f.readline().strip()
            if not firstLine.endswith("YES"):
                return None
            secondLine = f.readline().strip()
            parts = secondLine.split("t=")
            if len(parts)!=2:
                return None
            tempC = float(parts[1])/1000.0
            return tempC
        except Exception:
            traceback.print_exc()

    def measure_first_device(self):
        if not self.devices:
            return None
        return self.measure_device(self.devices[0])

    def device_count(self):
        return len(self.devices)


def main():
    ds = DS1820()
    if ds.device_count() == 0:
        print >> sys.stderr, "No devices found"
        sys.exit(-1)

    print "%d devices found" % ds.device_count()

    tempC = ds.measure_first_device()
    if tempC == None:
        print >> sys.stderr, "Failed to read temperature"
        sys.exit(-1)

    print "Temperature %0.2f" % tempC


if __name__ == "__main__":
    main()