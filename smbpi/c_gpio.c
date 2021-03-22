#include <Python.h>
#include <unistd.h>
#include <stdio.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include "c_gpio.h"

#define GPIO_IN(g)    *(gpio+((g)/10))   &= ~(7<<(((g)%10)*3))
#define GPIO_OUT(g)   *(gpio+((g)/10))   |=  (1<<(((g)%10)*3))
#define GPIO_ALT(g,a) *(gpio+(((g)/10))) |= (((a)<=3?(a)+4:(a)==4?3:2)<<(((g)%10)*3))

#define GPIO_SET(g)   *(gpio+7)  = 1<<(g)  /* sets   bit which are 1, ignores bit which are 0 */
#define GPIO_CLR(g)   *(gpio+10) = 1<<(g)  /* clears bit which are 1, ignores bit which are 0 */
#define GPIO_LEV(g)  (*(gpio+13) >> (g)) & 0x00000001

// -----------------------------------------------------------
// GPIO stuff, when I flipped out that time because wiringpi didn't work
//    note to self: it needed an upgrade, because the peri base changed
// -----------------------------------------------------------

/* GPIO registers address */
#define BCM2708_PERI_BASE  0xFE000000  // pi4
                          //0x20000000 some other pi
#define GPIO_BASE          (BCM2708_PERI_BASE + 0x200000) /* GPIO controller */
#define BLOCK_SIZE         (256)

int                mem_fd;
void              *gpio_map;
volatile uint32_t *gpio;

void myGpioInit(void)
{
    /* open /dev/mem */
    mem_fd = open("/dev/mem", O_RDWR|O_SYNC);
    if (mem_fd == -1) {
              perror("Cannot open /dev/mem");
              exit(1);
     }

     /* mmap GPIO */
    gpio_map = mmap(NULL, BLOCK_SIZE, PROT_READ|PROT_WRITE, MAP_SHARED, mem_fd, GPIO_BASE);
    if (gpio_map == MAP_FAILED) {
            perror("mmap() failed");
            exit(1);
    }
      /* Always use volatile pointer! */
    gpio = (volatile uint32_t *)gpio_map;
}

unsigned int myDigitalRead(unsigned int pin)
{
  return GPIO_LEV(pin);
}

void myDigitalWrite(unsigned int pin, unsigned int val)
{
  if (val) {
    fprintf(stdout, "set %d\n", pin);
    GPIO_SET(pin);
  } else {
    fprintf(stdout, "clr %d\n", pin);
    GPIO_CLR(pin);
  }
}

void myPinModeInput(unsigned int pin)
{
    fprintf(stdout, "input %d\n", pin);
    GPIO_IN(pin);
}

void myPinModeOutput(unsigned int pin)
{
    fprintf(stdout, "output %d\n", pin);
    GPIO_IN(pin);
    GPIO_OUT(pin);
}

