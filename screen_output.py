import logging
from urllib.error import URLError

# Constants for URLs and Loggers
PANEL_INSTALL_URL = "https://learn.adafruit.com/adafruit-rgb-matrix-bonnet-for-raspberry-pi/driving-matrices"
HAT_INSTALL_URL = "https://github.com/pimoroni/unicorn-hat-hd"
SCREEN_OUTPUT_LOGGER = "screen-output-logger"

# Setting up logger
logger = logging.getLogger(SCREEN_OUTPUT_LOGGER)

try:
    from panel_controller import PanelController
except ModuleNotFoundError:
    logger.warning(f"RGB Matrix install not found. If you want to install: {PANEL_INSTALL_URL}")

try:
    from hat_controller import UnicornHATController
except ModuleNotFoundError:
    logger.warning(f"Unicorn HAT install not found. If you want to install: {HAT_INSTALL_URL}")


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
        Draw a pixel on the screen, ends loop if pixel_rgb is "e",
        will raise an exception if the pixel_coord is out of range

        :param pixel_coord: Coordinate of the pixel
        :param pixel_rgb: RGB value of the pixel
        :param current_layer: The current layer of the screen
        :return: None
        """
        try:
            self.screen.set_pixel(pixel_coord[0], pixel_coord[1], pixel_rgb[0], pixel_rgb[1], pixel_rgb[2])
        except IndexError as e:
            if pixel_rgb == "e":
                logger.info("Render thread purposely ended")
                quit()
            else:
                err_msg = f"Set pixel did not like pixel coordinate: {pixel_coord} with RGB value: {pixel_rgb}"
                logger.error(err_msg, exc_info=True)
                raise

    def show(self):
        """
        Refreshes the screen to reflect the current state
        """
        self.screen.show()
