#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

/* Borrowed from https://www.raspberrypi.org/forums/viewtopic.php?t=228727 */

#include <fcntl.h>
#include <sys/mman.h>
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <sched.h>

#include "micros.h"

static volatile uint32_t *systReg;
static int fdMem;
static uint32_t phys;

void initMicros(void)
{
        // based on pigpio source; simplified and re-arranged
        fdMem = open("/dev/mem",O_RDWR|O_SYNC);
        if(fdMem < 0) {
                fprintf(stderr,"Cannot map memory (need sudo?)\n");
                exit(1);
        }
        // figure out the address
        FILE *f = fopen("/proc/cpuinfo","r");
        char buf[1024];
        if (fgets(buf,sizeof(buf),f)!=0) { // skip first line
                fprintf(stderr,"failed to skip line1\n");
                exit(1);
        }            
        if (fgets(buf,sizeof(buf),f) !=0) { // model name
                fprintf(stderr,"failed to skip line1\n");
                exit(1);
        }
        // would be a better way to check:
        // https://www.raspberrypi-spy.co.uk/2012/09/checking-your-raspberry-pi-board-version/
        if(strstr(buf,"ARMv6")) {
                phys = 0x20000000;
        } else if(strstr(buf,"ARMv7")) {
                //phys = 0x3F000000;
                phys = 0xFE000000;           // address for pi4
        } else if(strstr(buf,"ARMv8")) {
                phys = 0x3F000000;
        } else {
                fprintf(stderr,"Unknown CPU type\n");
                exit(1);
        }
        fclose(f);
        systReg = (uint32_t *)mmap(0,0x1000,PROT_READ|PROT_WRITE,
                                MAP_SHARED|MAP_LOCKED,fdMem,phys+0x3000);

}

void delayMicros(int us)
{
        // The final microsecond can be short; don't let the delay be short.
        ++us;

        // usleep() on its own gives latencies 20-40 us; this combination
        // gives < 25 us.
        uint32_t start = micros();
        if(us >= 100)
                usleep(us - 50);
        while(micros()-start < us)
                ;
}

uint32_t micros(void) {
  return systReg[1]; 
}
