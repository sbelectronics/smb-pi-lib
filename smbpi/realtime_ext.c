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
