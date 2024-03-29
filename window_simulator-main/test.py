import neopixel
import board
import time
from LED_Strip import LED_Strip
import Modes

def main():    
    pixels = neopixel.NeoPixel(pin = board.D19,
                               n = 30,
                               bpp = 4,
                               brightness = 0.8,
                               auto_write = False,
                               pixel_order = neopixel.GRBW)

    # # with pixels:
    # while True:
        # try:
            # index_0 = int(input("index 0: "))
            # index_1 = int(input("index 1: "))
            # index_2 = int(input("index 2: "))
            # index_3 = int(input("index 3: "))
            
            # print("({}, {}, {}, {})".format(index_0, index_1, index_2, index_3))
            # pixels.fill((index_0, index_1, index_2, index_3))
        # except KeyboardInterrupt:
            # # pixels.fill((0, 0, 0, 0))
            # break   
        # pixels.show()
        # time.sleep(1)
    
    # l = LED_Strip("off")
    # m = Modes.Rainbow()
    # m.cycle(pixels)
    print(pixels.n)
    
if __name__ == "__main__":
    main()