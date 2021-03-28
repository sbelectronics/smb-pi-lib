#include <Python.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <sched.h>

/* Borrowed from https://www.raspberrypi.org/forums/viewtopic.php?t=228727
 *
 * tjrob's techniques for real time scheduling a process on a pi.
 * 
 * works by isolating a cpu from Linux, then pinning the process to that cpu
 */

/* A different comment from another thread (https://www.raspberrypi.org/forums/viewtopic.php?t=200793), about using taskset:
 * Heater ... I have done everything you said, and it works just perfectly now:
 * - add this at kernel boot prompt, to reserve cores 2 and 3 (first core is #0): isolcpus=2,3
 * - start my bash script on core 2: /usr/bin/taskset -c 2 /root/ws2812-spi/ws2812.sh
 *- in this script, call the python API (the one that really performs the SPI calls) on core 3: taskset -c 3 nice -n -20 /root/ws2812-spi/ws2812.05.py
 *   since I am now using taskset, nice is probably useless. And then, reboot.
 */

/* Another option may be partrt, uses cgroups
 */

/* some tests
 *
 *    fdc with no special options, 4.4% failure
 *    fdc with --realtime, 3% failure
 *       a lot of these are 90 followed by D0 errors, and I wonder if something else is going on
 *    fdc with --realtime and sleep before the op, 3% failure
 *    fdc with --realtime --pincpu 3 and isolcpus=3 on cmdline, 3% failure
 * 
 */


static PyObject *realtime_realTimeSched(PyObject *self, PyObject *args)
{
  int prio;
  int rc;
  struct sched_param param;

  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }

  prio = sched_get_priority_max(SCHED_FIFO);
  param.sched_priority = prio;

  sched_setscheduler(0,SCHED_FIFO,&param);
  // This permits realtime processes to use 100% of a CPU, but on a
  // RPi that starves the kernel. Without this there are latencies
  // up to 50 MILLISECONDS.
  rc = system("echo -1 >/proc/sys/kernel/sched_rt_runtime_us");
  return Py_BuildValue("i", rc);
}

static PyObject *realtime_pinCPU(PyObject *self, PyObject *args)
{
  unsigned int cpu;

  if (!PyArg_ParseTuple(args, "i", &cpu)) {
    return NULL;
  }

  cpu_set_t cpuset;
  CPU_ZERO(&cpuset);
  CPU_SET(cpu,&cpuset);
  sched_setaffinity(0,sizeof(cpu_set_t),&cpuset);

  return Py_BuildValue("i", 0);
}

static PyObject *realtime_enableTurbo(PyObject *self, PyObject *args)
{
  unsigned int turbo;
  int rc;

  if (!PyArg_ParseTuple(args, "i", &turbo)) {
    return NULL;
  }

  if (turbo) {
        rc = system("sudo cp /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq "
                "/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq");
  } else {
        rc = system("sudo cp /sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq "
                "/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq");
  }

  return Py_BuildValue("i", rc);
}

static PyMethodDef realtime_methods[] = {
  {"realTimeSched", realtime_realTimeSched, METH_VARARGS, "Enable real-time scheduling"},
  {"pinCPU", realtime_pinCPU, METH_VARARGS, "Pin process to CPU"},
  {"enableTurbo", realtime_enableTurbo, METH_VARARGS, "Enable or disble turbo mode"},

  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initrealtime_ext(void)
{
  (void) Py_InitModule("realtime_ext", realtime_methods);
}
