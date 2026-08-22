import logging

try:
    from panel_controller import PanelController
except ModuleNotFoundError:
    print("RGB Matrix install not found, skipping import - go here if you want to install: "
          "https://learn.adafruit.com/adafruit-rgb-matrix-bonnet-for-raspberry-pi/driving-matrices")

try:
    from hat_controller import UnicornHATController
except ModuleNotFoundError:
    print("Unicorn HAT install not found, skipping import - go here if you want to install: "
          "https://github.com/pimoroni/unicorn-hat-hd")

import time

logger = logging.getLogger("screen-output-logger")


class ScreenController:
    def __init__(self, screen_type, simulator, custom_size_simulator, led_brightness):
        if screen_type == "PANEL":
            self.screen = PanelController(custom_size_simulator[0], custom_size_simulator[1], led_brightness)
        else:
            self.screen = UnicornHATController(screen_type, simulator, custom_size_simulator, led_brightness)

        self.u_width, self.u_height = self.screen.get_shape()
        # the unicorn hat led addresses are 0 indexed so need to account for this
        self.u_width_max = self.u_width - 1
        self.u_height_max = self.u_height - 1

    def draw_pixels(self, pixel_coord, pixel_rgb, current_layer=0):
        """
        Draw a pixel on the screen, ends loop if pixel_rgb is "e", will raise an exception if the pixel_coord is out
        of range
        :param pixel_coord:
        :param pixel_rgb:
        :param current_layer:
        :return:
        """
        try:
            self.screen.set_pixel(pixel_coord[0], pixel_coord[1], pixel_rgb[0], pixel_rgb[1], pixel_rgb[2])
        except IndexError:
            if pixel_rgb == "e":
                logger.info("Render thread purposely ended")
                quit()
            else:
                raise Exception(f"Set pixel did not like pixel coordinate: {pixel_coord} with RGB value: {pixel_rgb}")

    def show(self):
        """
        Show the current state of the board
        """
        self.screen.show()

    def off(self):
        """
        Clear & Turn off the screen
        """
        self.screen.off()

