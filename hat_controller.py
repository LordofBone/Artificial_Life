import logging

logger = logging.getLogger("hat-controller-logger")


class UnicornHATController:
    def __init__(self, screen_type, simulator, custom_size_simulator, led_brightness):
        self.simulator_refresh = False

        try:
            import unicornhat as unicorn
            import unicornhathd as unicornhd
            from unicornhatmini import UnicornHATMini
        except ImportError:
            try:
                from unicorn_hat_sim import UnicornHatSim
                from unicorn_hat_sim import unicornhat as unicorn
                from unicorn_hat_sim import unicornhathd as unicornhd
                from unicorn_hat_sim import unicornphat as UnicornHATMini
            except ModuleNotFoundError:
                pass
        except:
            pass

            self.simulator_refresh = True

        if simulator:
            from unicorn_hat_sim import UnicornHatSim

            from unicorn_hat_sim import unicornhat as unicorn
            from unicorn_hat_sim import unicornhathd as unicornhd
            from unicorn_hat_sim import unicornphat as UnicornHATMini

            self.simulator_refresh = True

        if screen_type == "MINI":
            # unicorn hat mini setup
            # todo: figure out why this doesn't work with the phat simulator
            try:
                self.screen = UnicornHATMini()
                self.screen.set_brightness(led_brightness)
                self.screen.set_rotation(0)
            except TypeError:
                self.screen = UnicornHATMini
        elif screen_type == "SD":
            # unicorn hat + unicorn hat hd setup
            self.screen.set_layout(self.screen.AUTO)
            self.screen.brightness(led_brightness)
            self.screen.rotation(0)
        elif screen_type == "HD":
            # unicorn hat + unicorn hat hd setup
            self.screen = unicornhd
            self.screen.set_layout(self.screen.AUTO)
            self.screen.brightness(led_brightness)
            self.screen.rotation(270)
        elif screen_type == "CUSTOM":
            # unicorn hat + unicorn hat hd setup
            try:
                self.screen = UnicornHatSim(custom_size_simulator[0], custom_size_simulator[1], 180)
            except NameError:
                logger.info(f"Custom mode set without simulator mode on, defaulting to HD physical HAT")
                self.screen = unicornhd
                screen_type = "HD"
            self.screen.set_layout(self.screen.AUTO)
            self.screen.brightness(led_brightness)
            self.screen.rotation(0)
            self.simulator_refresh = True

    def get_shape(self):
        return self.screen.get_shape()

    def set_pixel(self, x, y, r, g, b):
        self.screen.set_pixel(x, y, r, g, b)

    def show(self):
        self.screen.show()
