#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <poll.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <time.h>
#include <fcntl.h>
#include <sys/time.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>

#define BCM2708_PERI_BASE 0x20000000
#define GPIO_BASE (BCM2708_PERI_BASE + 0x200000)

#define MIN_PIN 0
#define MAX_PIN 53

#define NUM_GPIO 54

#define PAGE_SIZE  4096
#define BLOCK_SIZE 4096

#define BANK1 13
#define BANK2 14

#define MILLION (1000000L)

volatile uint32_t *gpio ;

struct timeval now;

uint32_t monitorBank1, monitorBank2;
uint32_t displayBank1, displayBank2;
uint32_t inputBank1, inputBank2;
uint32_t legalBank1, legalBank2;

int trimChars;
int decimals;

int sampleRate, sampleInterval;
int usecs[]={1000000, 100000, 10000, 1000, 100, 10, 1};

char options[2048];

int initGpio(void)
{
   int      fd;
   uint8_t *gpioMem;
   struct timeval tv;

   if ((fd = open ("/dev/mem", O_RDWR | O_SYNC) ) < 0)
   {
     fprintf (stderr, "Unable to open /dev/mem: %s\n", strerror (errno)) ;
     exit(-1);
   }

   if ((gpioMem = malloc(BLOCK_SIZE + (PAGE_SIZE-1))) == NULL)
   {
     fprintf (stderr, "malloc failed: %s\n", strerror (errno)) ;
     exit(-1);
   }

   if (((uint32_t)gpioMem % PAGE_SIZE) != 0)
     gpioMem += PAGE_SIZE - ((uint32_t)gpioMem % PAGE_SIZE) ;

   gpio = (uint32_t *) mmap((caddr_t)gpioMem,
                            BLOCK_SIZE, PROT_READ|PROT_WRITE,
                            MAP_SHARED|MAP_FIXED, fd, GPIO_BASE) ;

   if ((int32_t)gpio < 0)
   {
     fprintf (stderr, "mmap failed: %s\n", strerror (errno)) ;
     exit(-1);
   }
}

void displayGPIOlevels(uint32_t bank1, uint32_t bank2)
{
   char buf[NUM_GPIO];
   int i, j;

   j = 0;

   for (i=0; i<32; i++)
   {
      if ((monitorBank1 & (1<<i)) || (displayBank1 & (1<<i)))
      {
         if (bank1 & (1<<i)) buf[j]='1'; else buf[j]='0';
         j++;
      }
   }

   for (i=0; i<22; i++)
   {
      if ((monitorBank2 & (1<<i)) || (displayBank2 & (1<<i)))
      {
         if (bank2 & (1<<i)) buf[j]='1'; else buf[j]='0';
         j++;
      }
   }

   buf[j]=0;

   printf("%s\n", buf);
}

void timestamp()
{
   /* statics persist over function calls */

   static struct timeval last;
   static char buf[32];

   struct tm tmp;

   if (now.tv_sec != last.tv_sec)
   {
      /* only reformat date/time once per second */

      last.tv_sec = now.tv_sec;
      localtime_r(&now.tv_sec, &tmp);
      strftime(buf, sizeof(buf), "%F@%T", &tmp);
   }

   if (decimals)
      printf("%s.%0*d ", buf+trimChars, decimals, now.tv_usec/usecs[decimals]);
   else
      printf("%s ", buf+trimChars);
}

typedef void (*pinFunc)(int);

void pinDisplay(int pin)
{
   if (pin < 32) displayBank1 |= (1<<pin);
   else          displayBank2 |= (1<<(pin-32));
}

void pinMonitor(int pin)
{
   if (pin < 32) monitorBank1 |= (1<<pin);
   else          monitorBank2 |= (1<<(pin-32));
}

void pinInput(int pin)
{
   int gpfsel, shift, legal;

   if (pin < 32) legal = legalBank1 & (1<<pin);
   else          legal = legalBank2 & (1<<(pin-32));

   if (legal)
   {
      if (pin < 32) inputBank1 |= (1<<pin);
      else          inputBank2 |= (1<<(pin-32));

      gpfsel = pin/10;
      shift = (pin%10)*3;
      *(gpio + gpfsel) &= ~(7 << shift);
   }
}

int parsePins(char * pins, pinFunc f)
{
   char * token;
   int i1, i2, t;

   token = strtok(pins, ",");

   while (token != NULL)
   {
      if (index(token, '-') != NULL)
      {
         t = sscanf(token, "%d-%d", &i1, &i2);
         if (t != 2) return -1;
      }
      else
      {
         i1 = atoi(token);
         i2 = i1;
      }

      if (i1 > i2) {t = i1; i1 = i2; i2 = t;}

      if ((i1<MIN_PIN) || (i2>MAX_PIN)) return -1;

      for (t=i1; t<=i2; t++) (f)(t);

      token = strtok(NULL, ",");
   }
   return 0;
}

void usage()
{
   fprintf(stderr, "\n" \
      "Usage: sudo ./gpio-monitor [OPTION] ...\n" \
      "   -d RANGE, gpios to display, default NONE\n" \
      "       (additional to those being monitored)\n" \
      "   -i RANGE, gpios to set as inputs, default NONE\n" \
      "       (0-5,7-11,14-15,17-18,21-25,27 only legal, others ignored)\n" \
      "   -m RANGE, gpios to monitor, default NONE\n" \
      "   -s value, sample rate per second, 1-1000000, default 100\n" \
      "   -t value, characters to trim from date/time, 0-18, default 0\n" \
      "RANGE may be pin or pin1-pin2 or any combination\n" \
      "      separated by commas without spaces\n" \
      "      (pin numbers range from 0 to 53)\n" \
      "      e.g. 0-31,36,40,50-53\n" \
      "EXAMPLE\n" \
      "sudo ./gpio-monitor -m0-7 -d11,15-18 -s200\n" \
      "  Monitor state changes on gpios 0 to 7 at 200 Hz.\n" \
      "  Also display the states of gpios 11 and 15 to 18\n" \
      "  when one of 0 to 7 changes state.\n" \
   "\n");
}

int initOpts(int argc, char *argv[])
{
   int opt, include, status;

   trimChars = 0;
   decimals = 2;
   sampleRate = 100;
   sampleInterval = MILLION / sampleRate;

   monitorBank1=0x00000000;
   monitorBank2=0x00000000;

   displayBank1=0x00000000;
   displayBank2=0x00000000;

   inputBank1=0x00000000;
   inputBank2=0x00000000;

   /*          31     24      16       8       0  */
   /*           |      |       |       |       |  */
   legalBank1=0b00001011111001101100111110111111;

   /*                    53   48      40       32 */
   /*                     |    |       |       |  */
   legalBank2=0b00000000000000000000000000000000;

   while ((opt = getopt(argc, argv, "d:i:m:s:t:")) != -1)
   {
      switch (opt)
      {
         case 'd':
            status = parsePins(optarg, pinDisplay);
            if (status < 0)
            {
               usage();
               exit(-1);
            }
            break;

         case 'i':
            status = parsePins(optarg, pinInput);
            if (status < 0)
            {
               usage();
               exit(-1);
            }
            break; 

         case 'm':
            status = parsePins(optarg, pinMonitor);
            if (status < 0)
            {
               usage();
               exit(-1);
            }
            break;

        case 's':

            sampleRate = atoi(optarg);

            if ((sampleRate<1) || (sampleRate>MILLION))
            {
               usage();
               exit(-1);
            }

            if      (sampleRate <= 1) decimals = 0;
            else if (sampleRate <= 10) decimals = 1;
            else if (sampleRate <= 100) decimals = 2;
            else if (sampleRate <= 1000) decimals = 3;
            else if (sampleRate <= 10000) decimals = 4;
            else if (sampleRate <= 100000) decimals = 5;
            else                            decimals = 6;

            sampleInterval = MILLION / sampleRate;

            break;

         case 't':
            trimChars=atoi(optarg);
            if ((trimChars<0) || (trimChars>18))
            {
               usage();
               exit(-1);
            }
            break;

        default: /* '?' */
           usage();
           exit(-1);
        }
    }
}

void formatPins(char * str, uint32_t p1, uint32_t p2)
{
   int i;
   char buf[8];

   if (p1 || p2)
   {
      for (i=MIN_PIN; i<=MAX_PIN; i++)
      {
         if (i<32)
         {
            if (p1 & (1<<i)) {sprintf(buf, " %d", i); strcat(str, buf);}
         }
         else
         {
            if (p2 & (1<<(i-32))) {sprintf(buf, " %d", i); strcat(str, buf);}
         }
      }
   }
   else strcat(str, "NONE");
}

void formatOpts(char * str)
{
   int i;
   char buf[256];

   struct tm tmp;

   gettimeofday(&now, NULL);
   localtime_r(&now.tv_sec, &tmp);
   strftime(buf, sizeof(buf), "#0 %F@%T\n", &tmp);
   strcat(str, buf);

   sprintf(buf, "#1 Sample rate (Hz): %d\n", sampleRate);
   strcat(str, buf);

   sprintf(buf, "#2 Sample interval (microseconds): %d\n", sampleInterval);
   strcat(str, buf);

   sprintf(buf, "#3 Trim date/time characters: %d\n", trimChars);
   strcat(str, buf);

   sprintf(buf, "#4 Seconds decimal places: %d\n", decimals);
   strcat(str, buf);

   sprintf(buf, "#5 Monitoring gpios: ");
   formatPins(buf, monitorBank1, monitorBank2);
   strcat(str, buf);
   strcat(str, "\n");

   sprintf(buf, "#6 Also displaying gpios: ");
   formatPins(buf, displayBank1, displayBank2);
   strcat(str, buf);
   strcat(str, "\n");

   sprintf(buf, "#7 Setting gpios as inputs: ");
   formatPins(buf, inputBank1, inputBank2);
   strcat(str, buf);
   strcat(str, "\n");

   sprintf(buf, "#8 gpios display order: ");
   formatPins(buf, monitorBank1|displayBank1, monitorBank2|displayBank2);
   strcat(str, buf);
   strcat(str, "\n");

   strcat(str, "#9 \n");
   strcat(str, "#A \n");
   strcat(str, "#B \n");
   strcat(str, "#C \n");
   strcat(str, "#D \n");
   strcat(str, "#E \n");
   strcat(str, "#F \n");
}

int main(int argc, char *argv[])
{
   uint32_t oldBank1, oldBank2, newBank1, newBank2;
   int seconds, micros;
   int diff;
   struct timeval next;

   initGpio();

   initOpts(argc, argv);

   formatOpts(options);

   printf("%s", options);

   oldBank1 = *(gpio + BANK1);
   oldBank2 = *(gpio + BANK2);

   /* arbitrarily start sampling on a second boundary */

   gettimeofday(&now, NULL);

   next.tv_sec = now.tv_sec+1;
   next.tv_usec = 0;
 
   while(1)
   {
      gettimeofday(&now, NULL);

      seconds = now.tv_sec  - next.tv_sec;
      micros  = now.tv_usec - next.tv_usec;
      diff = (seconds * MILLION) + micros;

      if (diff >= 0)
      {
         newBank1 = *(gpio + BANK1);
         newBank2 = *(gpio + BANK2);

         if (((newBank1&monitorBank1) != (oldBank1&monitorBank1)) ||
             ((newBank2&monitorBank2) != (oldBank2&monitorBank2)))
         {
            timestamp();

            displayGPIOlevels(newBank1, newBank2);

            oldBank1 = newBank1;
            oldBank2 = newBank2;
         }

         next.tv_usec += sampleInterval;
         if (next.tv_usec >= MILLION)
         {
            next.tv_usec -= MILLION;
            next.tv_sec += 1;
         }
      }
      if (sampleRate < 1000) usleep(250);
   }
}