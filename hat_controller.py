import logging

logger = logging.getLogger("hat-controller-logger")


class HATController:
    def __init__(self, hat_edition, simulator, custom_size_simulator, led_brightness):
        self.simulator_refresh = False

        try:
            import unicornhat as unicorn
            import unicornhathd as unicornhd
            from unicornhatmini import UnicornHATMini
        except ImportError:
            from unicorn_hat_sim import UnicornHatSim
            from unicorn_hat_sim import unicornhat as unicorn
            from unicorn_hat_sim import unicornhathd as unicornhd
            from unicorn_hat_sim import unicornphat as UnicornHATMini

            self.simulator_refresh = True

        if simulator:
            from unicorn_hat_sim import UnicornHatSim

            from unicorn_hat_sim import unicornhat as unicorn
            from unicorn_hat_sim import unicornhathd as unicornhd
            from unicorn_hat_sim import unicornphat as UnicornHATMini

            self.simulator_refresh = True

        if hat_edition == "MINI":
            # unicorn hat mini setup
            # todo: figure out why this doesn't work with the phat simulator
            try:
                self.unicorn = UnicornHATMini()
                self.unicorn.set_brightness(led_brightness)
                self.unicorn.set_rotation(0)
            except TypeError:
                self.unicorn = UnicornHATMini
        elif hat_edition == "SD":
            # unicorn hat + unicorn hat hd setup
            self.unicorn.set_layout(self.unicorn.AUTO)
            self.unicorn.brightness(led_brightness)
            self.unicorn.rotation(0)
        elif hat_edition == "HD":
            # unicorn hat + unicorn hat hd setup
            self.unicorn = unicornhd
            self.unicorn.set_layout(self.unicorn.AUTO)
            self.unicorn.brightness(led_brightness)
            self.unicorn.rotation(270)
        elif hat_edition == "CUSTOM":
            # unicorn hat + unicorn hat hd setup
            try:
                self. unicorn = UnicornHatSim(custom_size_simulator[0], custom_size_simulator[1], 180)
            except NameError:
                logger.info(f"Custom mode set without simulator mode on, defaulting to HD physical HAT")
                self.unicorn = unicornhd
                hat_edition = "HD"
            self.unicorn.set_layout(self.unicorn.AUTO)
            self.unicorn.brightness(led_brightness)
            self.unicorn.rotation(0)
            self.simulator_refresh = True

        self.u_width, self.u_height = self.unicorn.get_shape()
        # the unicorn hat led addresses are 0 indexed so need to account for this
        self.u_width_max = self.u_width - 1
        self.u_height_max = self.u_height - 1

    def draw_pixels(self, x, y, r, g, b, current_layer=0):
        """
        Draw the position and colour of the current life form onto the board, if minecraft mode true, also set blocks
        relative to the player in the game world, adding 1 to the layer every iteration so that each time the current
        amount of entities is rendered it moves to another layer in minecraft, essentially building upwards.
        """
        try:
            self.unicorn.set_pixel(x, y, r, g, b)
        except IndexError:
            raise Exception(f"Set pixel did not like X:{x} Y:{y} R:{r} G:{g} B:{b}")
        # todo: improve this greatly and move it out of this class/module
        # if args.mc_mode:
        #     player_x, player_y, player_z = mc.player.getPos()
        #     random.seed(r + g + b)
        #     random_block = random.randint(1, 22)
        #     random.seed()
        #     mc.setBlock(player_x + x, player_y + 10 + current_layer, player_z + y, random_block)
