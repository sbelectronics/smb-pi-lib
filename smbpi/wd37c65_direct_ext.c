#include <Python.h>
#include <wiringPi.h>
#include <unistd.h>
#include <stdio.h>

//#include "c_gpio.h"

#define RESULT_OKAY 0
#define RESULT_TIMEOUT_EXEC 0x14
#define RESULT_OVER_DRAIN 0x16
#define RESULT_OVER_CMDRES 0x17
#define RESULT_TIMEOUT_READRES 0x18
#define RESULT_READ_ERROR 0x19
#define RESULT_WRITE_ERROR 0x20

#define REG_MSR 0
#define REG_DATA 1

#define CS_FDC 0
#define CS_DOR 1
#define CS_DCR 2

#define WD_WR 6
#define WD_RD 5
#define WD_A0 12
#define WD_CS 13
#define WD_DOR 19
#define WD_CCR 16
#define WD_DACK 26
#define WD_TC 20
#define WD_RESET 21
#define WD_DC 7

const int WD_DATAPINS[] = { 17, 18, 27, 22, 23, 24, 25, 4 };
const int WD_DATAPINS_REVERSED[] = { 4, 25, 24, 23, 22, 27, 18, 17 };

#define myDigitalWrite(x,y) digitalWrite(x,y)
#define myDigitalRead(x) digitalRead(x)
#define myPinModeInput(x) pinMode(x,INPUT)
#define myPinModeOutput(x) pinMode(x,OUTPUT)

void wd_config_input(void)
{
  int i;
  for (i=0; i<8; i++) {
    myPinModeInput(WD_DATAPINS[i]);
  }
}

void wd_config_output(void)
{
  int i;
  for (i=0; i<8; i++) {
    myPinModeOutput(WD_DATAPINS[i]);
  }
}

void wd_set_addr(unsigned int addr)
{
  myDigitalWrite(WD_A0, addr);
}

void wd_set_rd(unsigned int value)
{
  myDigitalWrite(WD_RD,value);
}

void wd_set_wr(unsigned int value)
{
  myDigitalWrite(WD_WR,value);
}

void wd_set_cs(unsigned int cs, unsigned int value)
{
  switch(cs) {
    case CS_FDC:
      myDigitalWrite(WD_CS, value);
      break;

    case CS_DOR:
      myDigitalWrite(WD_DOR, value);
      break;

    case CS_DCR:
      myDigitalWrite(WD_CCR, value);
      break;
  }
}

void wd_set_data(unsigned int data)
{
  int i;
  for (i=0; i<8; i++) {
    myDigitalWrite(WD_DATAPINS[i], data & 0x01);
    data = data >> 1;
  }
}

unsigned int wd_get_data(void)
{
  int i;
  int data = 0;
  for (i=0; i<8; i++) {
    data = data << 1;
    data = data | myDigitalRead(WD_DATAPINS_REVERSED[i]);
  }
  return data;
}

unsigned int wd_get_tc(void)
{
  return myDigitalRead(WD_TC);  // XXX this is an output not an input...
}

unsigned int wd_get_dc(void)
{
  return myDigitalRead(WD_DC);
}

unsigned int wd_read_data(void) 
{
  unsigned int data;

  wd_config_input();
  wd_set_addr(REG_DATA);
  wd_set_cs(CS_FDC, 0);
  wd_set_rd(0);
  // see comment in dpmem_direct_read_block. Just to be safe...
  myDigitalRead(WD_DATAPINS_REVERSED[0]);
  data = wd_get_data();
  wd_set_rd(1);
  wd_set_cs(CS_FDC, 1);

  return data;
}

unsigned int wd_read_msr(void) 
{
  unsigned int msr;

  wd_config_input();
  wd_set_addr(REG_MSR);
  wd_set_cs(CS_FDC, 0);
  wd_set_rd(0);
  // see comment in dpmem_direct_read_block. Just to be safe...
  myDigitalRead(WD_DATAPINS_REVERSED[0]);
  msr = wd_get_data();
  wd_set_rd(1);
  wd_set_cs(CS_FDC, 1);

  return msr;
}

unsigned int wd_write_data(unsigned int data)
{
  //fprintf(stderr, "write data %02X\n", data);
  wd_config_output();
  wd_set_addr(REG_DATA);
  wd_set_data(data);
  wd_set_cs(CS_FDC, 0);
  wd_set_wr(0);
  wd_set_wr(1);
  wd_set_cs(CS_FDC, 1);
  wd_config_input();

  return data;
}

unsigned int wd_write_dor(unsigned int data)
{
  //fprintf(stderr, "write dor %02X\n", data);
  wd_config_output();
  wd_set_addr(0);
  wd_set_data(data);
  wd_set_cs(CS_DOR, 0);
  wd_set_wr(0);
  wd_set_wr(1);
  wd_set_cs(CS_DOR, 1);
  wd_config_input();

  return data;
}

unsigned int wd_write_dcr(unsigned int data)
{
  //fprintf(stderr, "write dcr %02X\n", data);
  wd_config_output();
  wd_set_addr(0);
  wd_set_data(data);
  wd_set_cs(CS_DCR, 0);
  wd_set_wr(0);
  wd_set_wr(1);
  wd_set_cs(CS_DCR, 1);
  wd_config_input();

  return data;
}

unsigned int wd_wait_msr(unsigned int mask, unsigned int val)
{
  unsigned int msr;
  unsigned int timeout = 65535 * 3;

  wd_config_input();
  while (TRUE) {
      // wiringPi
      delayMicroseconds(3);

      msr = wd_read_msr();
      if ((msr & mask) == val) {
        return 0;
      }

      timeout--;
      if (timeout == 0) {
        fprintf(stderr, "waitmsr timedout with %02X\n", msr);
        return RESULT_TIMEOUT_EXEC;
      }
  }
}

unsigned int wd_drain(void)
{
  unsigned int msr;
  unsigned int max = 1024;

  wd_config_input();
  while (max > 0) {
      // wiringPi
      delayMicroseconds(10);

      msr = wd_read_msr();
      if ((msr & 0xC0) != 0xC0) {
        // no data
        return 0;
      }

      // there is a byte
      wd_read_data();
      max --;
  }

  // something weird must have happened
  return RESULT_OVER_DRAIN;
}

void wd_init(void)
{
  unsigned int i;

  myDigitalWrite(WD_A0, 1);
  myDigitalWrite(WD_CS, 1);
  myDigitalWrite(WD_DOR, 1);
  myDigitalWrite(WD_CCR, 1);
  myDigitalWrite(WD_RD, 1);
  myDigitalWrite(WD_WR, 1);
  myDigitalWrite(WD_RESET, 0); // start with reset deasserted
  myDigitalWrite(WD_TC, 1);
  myDigitalWrite(WD_DACK, 1);
  myPinModeOutput(WD_A0);
  myPinModeOutput(WD_CS);
  myPinModeOutput(WD_DOR);
  myPinModeOutput(WD_CCR);
  myPinModeOutput(WD_RD);
  myPinModeOutput(WD_WR);
  myPinModeOutput(WD_RESET);
  myPinModeOutput(WD_TC);
  myPinModeOutput(WD_DACK);

  for (i=0; i<8; i++) {
    pullUpDnControl(WD_DATAPINS[i], PUD_DOWN);
  }

  delayMicroseconds(10);
  myDigitalWrite(WD_RESET, 1); // assert reset
  delayMicroseconds(100);
  myDigitalWrite(WD_RESET, 0); // deassert reset
  delayMicroseconds(1000);
}

void wd_reset(unsigned int dor)
{
    int i;

    wd_write_dor(0);
    delayMicroseconds(17);
    wd_write_dor(dor);

    // 2.4ms delay    
    for (i=0; i<240; i++) {
      // wiringPi
      delayMicroseconds(10);
    }
}

void wd_pulse_dack(void)
{
  myDigitalWrite(WD_DACK, 0);
  delayMicroseconds(1);
  myDigitalWrite(WD_DACK, 1);
}

void short_delay(void)
{
    // Just do nothing for a while. This is to allow the RAM some time to do it's work.
    //
    int j;

    for (j=0; j<1; j++) {
        asm("nop");
    }
}

static PyObject *wd_direct_init(PyObject *self, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  wd_init();
  return Py_BuildValue("");
}

static PyObject *wd_direct_reset(PyObject *self, PyObject *args)
{
  unsigned int dor;
  if (!PyArg_ParseTuple(args, "i", &dor)) {
    return NULL;
  }
  wd_reset(dor);
  return Py_BuildValue("");
}

static PyObject *wd_direct_pulse_dack(PyObject *self, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  wd_pulse_dack();
  return Py_BuildValue("");
}

static PyObject *wd_direct_get_tc(PyObject *self, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return Py_BuildValue("i", wd_get_tc());
}

static PyObject *wd_direct_get_dc(PyObject *self, PyObject *args)
{
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  return Py_BuildValue("i", wd_get_dc());
}

static PyObject *wd_direct_set_addr(PyObject *self, PyObject *args)
{
  int addr;  
  if (!PyArg_ParseTuple(args, "i", &addr)) {
    return NULL;    
  }
  wd_set_addr(addr);
  return Py_BuildValue("");
}

static PyObject *wd_direct_read_byte(PyObject *self, PyObject *args)
{
  unsigned int cs, addr;
  unsigned int data;
  if (!PyArg_ParseTuple(args, "ii", &cs, &addr)) {
    return NULL;
  }
  data = wd_read_data();
  return Py_BuildValue("i", data);
}

static PyObject *wd_direct_write_byte(PyObject *self, PyObject *args)
{
  unsigned int cs, addr, data;
  if (!PyArg_ParseTuple(args, "iii", &cs, &addr, &data)) {
    return NULL;
  }
  wd_config_output();
  wd_set_addr(addr);
  wd_set_data(data);
  wd_set_cs(cs, 0);
  wd_set_wr(0);
  wd_set_wr(1);
  wd_set_cs(cs, 1);
  wd_config_input();
  return Py_BuildValue("");
}

static PyObject *wd_direct_write_data(PyObject *self, PyObject *args)
{
  unsigned int data;
  if (!PyArg_ParseTuple(args, "i", &data)) {
    return NULL;
  }
  wd_write_data(data);
  return Py_BuildValue("");
}

static PyObject *wd_direct_write_dor(PyObject *self, PyObject *args)
{
  unsigned int data;
  if (!PyArg_ParseTuple(args, "i", &data)) {
    return NULL;
  }
  wd_write_dor(data);
  return Py_BuildValue("");
}

static PyObject *wd_direct_write_dcr(PyObject *self, PyObject *args)
{
  unsigned int data;
  if (!PyArg_ParseTuple(args, "i", &data)) {
    return NULL;
  }
  wd_write_dcr(data);
  return Py_BuildValue("");
}

static PyObject *wd_direct_read_block(PyObject *self, PyObject *args)
{
  unsigned int count;
  char buf[1024];
  int i;

  if (!PyArg_ParseTuple(args, "i", &count)) {
    return NULL;
  }

  if (count > 1024) {
      // throw exception?
      return NULL;
  }

  for (i=0; i<count; i++) {
      unsigned int status = wd_wait_msr(0xFF, 0xF0);   // RQM=1, DIO=1, NDM=1, BUS=1
      unsigned int msr;
      if (status!=0) {
        msr = wd_read_msr();
        if (msr == 0xD0) {
            fprintf(stderr, "read_block aborting on index %d with read error\n", i);
            return Py_BuildValue("is#", RESULT_READ_ERROR, buf, count);
        } else {
            fprintf(stderr, "read_block aborting on index %d with msr %02X\n", i, msr);
            return Py_BuildValue("is#", status, buf, count);
        }
      }

      buf[i] = wd_read_data();
  }

  // Terminate the transfer
  wd_pulse_dack();

  return Py_BuildValue("is#", 0, buf, count);
}

static PyObject *wd_direct_read_result(PyObject *self, PyObject *args)
{
  unsigned int count;
  unsigned int maxTime = 10000;
  char buf[1024];

  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }

  count = 0;
  while (maxTime>0) {
      unsigned int msr;

      // wiringPi
      delayMicroseconds(10);      
      
      msr = wd_read_msr();
      //fprintf(stderr, "readRes msr %2X\n", msr);
      if ((msr & 0xF0) == 0xD0) {
          // RQM=1, DIO=1, BUSY=1 ... byte is ready to read
          buf[count] = wd_read_data();
          count++;
          maxTime = 10000;
      } else if ((msr & 0xF0) == 0x80) {
          // RQM=1, DIO=0, BUSY=0 ... fdc is waiting for next command ... we are done
          return Py_BuildValue("is#", 0, buf, count);
      } else {
         maxTime--;
      }

      if (count>128) {
        return Py_BuildValue("is#", RESULT_OVER_CMDRES, buf, count);
      }
  }

  return Py_BuildValue("is#", RESULT_TIMEOUT_READRES, buf, count);
}

static PyObject *wd_direct_write_block(PyObject *self, PyObject *args)
{
  const char *buf;
  unsigned int buf_len, count;
  int i;

  if (!PyArg_ParseTuple(args, "s#i", &buf, &buf_len, &count)) {
    return NULL;
  }

  for (i=0; i<count; i++) {
      unsigned int status = wd_wait_msr(0xFF, 0xB0);  // suspicious
      if (status!=0) {
        unsigned int msr = wd_read_msr();
        if (msr == 0xD0) {
            fprintf(stderr, "write_block aborting on index %d with write error\n", i);
            return Py_BuildValue("i", RESULT_WRITE_ERROR);
        } else {
            fprintf(stderr, "write_block aborting on index %d with msr %02X\n", i, msr);
            return Py_BuildValue("i", status);
        }
      }

      wd_write_data(*buf);
      buf++;
  }

  // Terminate the transfer
  wd_pulse_dack();

  return Py_BuildValue("i", 0);
}

static PyObject *wd_direct_write_command(PyObject *self, PyObject *args)
{
  const char *buf;
  unsigned int buf_len, count;
  int i;

  if (!PyArg_ParseTuple(args, "s#i", &buf, &buf_len, &count)) {
    return NULL;
  }

  for (i=0; i<count; i++) {
      unsigned int status = wd_wait_msr(0xC0, 0x80);
      if (status!=0) {
        fprintf(stdout, "write_command status %2X on byte %d\n", status, i);
        wd_config_input();
        return Py_BuildValue("i", status);
      }

      wd_write_data(*buf);
      buf++;
  }
  wd_config_input();
  return Py_BuildValue("i", 0);
}

static PyObject *wd_direct_wait_msr(PyObject *self, PyObject *args)
{
  unsigned int mask, value;
  unsigned int status;
  if (!PyArg_ParseTuple(args, "ii", &mask, &value)) {
    return NULL;
  }
  status = wd_wait_msr(mask, value);
  return Py_BuildValue("i", status);
}

static PyObject *wd_direct_drain(PyObject *self, PyObject *args)
{
  unsigned int status;
  if (!PyArg_ParseTuple(args, "")) {
    return NULL;
  }
  status = wd_drain();
  return Py_BuildValue("i", status);
}

static PyMethodDef wd_direct_methods[] = {
  {"init", wd_direct_init, METH_VARARGS, "Initialize"},
  {"reset", wd_direct_reset, METH_VARARGS, "Reset"},
  {"pulse_dack", wd_direct_pulse_dack, METH_VARARGS, "Pulse Dack"},
  {"get_tc", wd_direct_get_tc, METH_VARARGS, "Get TC"},
  {"get_dc", wd_direct_get_dc, METH_VARARGS, "Get DC"},
  {"set_addr", wd_direct_set_addr, METH_VARARGS, "Set a0 bit"},
  {"read_byte", wd_direct_read_byte, METH_VARARGS, "Read byte at cs,address"},
  {"write_byte", wd_direct_write_byte, METH_VARARGS, "Write byte at cs,address"},
  {"write_data", wd_direct_write_data, METH_VARARGS, "Write data reg"},
  {"write_command", wd_direct_write_command, METH_VARARGS, "Write data reg"},  
  {"write_dor", wd_direct_write_dor, METH_VARARGS, "Write dor reg"},
  {"write_dcr", wd_direct_write_dcr, METH_VARARGS, "Write dcr reg"},
  {"read_block", wd_direct_read_block, METH_VARARGS, "Read block"},
  {"write_block", wd_direct_write_block, METH_VARARGS, "Write block"},
  {"read_result", wd_direct_read_result, METH_VARARGS, "Read command result"},
  {"wait_msr", wd_direct_wait_msr, METH_VARARGS, "wait for msr"},
  {"drain", wd_direct_drain, METH_VARARGS, "drain data"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initwd37c65_direct_ext(void)
{
  wiringPiSetupGpio();

  (void) Py_InitModule("wd37c65_direct_ext", wd_direct_methods);
}
