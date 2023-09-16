import logging

logger = logging.getLogger("hat-controller-logger")

try:
    import unicornhat as unicorn
    import unicornhathd as unicornhd
    from unicornhatmini import UnicornHATMini
    simulator_exists = False
except (ImportError, ModuleNotFoundError):
    simulator_exists = True
    try:
        from unicorn_hat_sim import UnicornHatSim
        from unicorn_hat_sim import unicornhat as unicorn
        from unicorn_hat_sim import unicornhathd as unicornhd
        from unicorn_hat_sim import unicornphat as UnicornHATMini
    except ModuleNotFoundError:
        logger.exception("UnicornHAT and Simulated Unicorn HAT not found")

class UnicornHATController:
    SCREEN_TYPE_MINI = "MINI"
    SCREEN_TYPE_SD = "SD"
    SCREEN_TYPE_HD = "HD"
    SCREEN_TYPE_CUSTOM = "CUSTOM"

    def __init__(self, screen_type, simulator=False, custom_size_simulator=None, led_brightness=0.5):
        self.simulator_refresh = simulator_exists or simulator

        if self.simulator_refresh:
            print("Using Simulated Unicorn HAT")
        else:
            print("Using Unicorn HAT")

        if screen_type == self.SCREEN_TYPE_MINI:
            self.init_mini_screen(led_brightness)
        elif screen_type == self.SCREEN_TYPE_SD:
            self.init_sd_screen(led_brightness)
        elif screen_type == self.SCREEN_TYPE_HD:
            self.init_hd_screen(led_brightness)
        elif screen_type == self.SCREEN_TYPE_CUSTOM:
            self.init_custom_screen(custom_size_simulator, led_brightness)

    def init_mini_screen(self, led_brightness):
        try:
            self.screen = UnicornHATMini()
        except TypeError:
            self.screen = UnicornHATMini
        self.screen.set_brightness(led_brightness)
        self.screen.set_rotation(0)

    def init_sd_screen(self, led_brightness):
        self.screen = unicorn
        self.screen.set_layout(unicorn.AUTO)
        self.screen.brightness(led_brightness)
        self.screen.rotation(0)

    def init_hd_screen(self, led_brightness):
        self.screen = unicornhd
        self.screen.set_layout(unicornhd.AUTO)
        self.screen.brightness(led_brightness)
        self.screen.rotation(270)

    def init_custom_screen(self, custom_size_simulator, led_brightness):
        try:
            self.screen = UnicornHatSim(custom_size_simulator[0], custom_size_simulator[1], 180)
            self.simulator_refresh = True
        except NameError:
            logger.info("Custom mode set without simulator mode on, defaulting to HD physical HAT")
            self.init_hd_screen(led_brightness)

        self.screen.set_layout(self.screen.AUTO)
        self.screen.brightness(led_brightness)
        self.screen.rotation(0)

    def get_shape(self):
        """
        Returns the shape of the screen
        """
        return self.screen.get_shape()

    def set_pixel(self, x, y, r, g, b):
        """
        Sets a pixel on the screen to the specified RGB color

        :param x: x-coordinate of the pixel
        :param y: y-coordinate of the pixel
        :param r: Red component of the color
        :param g: Green component of the color
        :param b: Blue component of the color
        """
        self.screen.set_pixel(x, y, r, g, b)

    def show(self):
        """
        Refreshes the screen to reflect the current state
        """
        self.screen.show()
