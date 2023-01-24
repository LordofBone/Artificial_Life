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
            # LED panel setup
            self.screen = PanelController()
        else:
            self.screen = UnicornHATController(screen_type, simulator, custom_size_simulator, led_brightness)

        self.u_width, self.u_height = self.screen.get_shape()
        # the unicorn hat led addresses are 0 indexed so need to account for this
        self.u_width_max = self.u_width - 1
        self.u_height_max = self.u_height - 1

    def draw_pixels(self, pixel_coord, pixel_rgb, current_layer=0):
        """
        Draw the position and colour of the current life form onto the board, if minecraft mode true, also set blocks
        relative to the player in the game world, adding 1 to the layer every iteration so that each time the current
        amount of entities is rendered it moves to another layer in minecraft, essentially building upwards.
        """
        try:
            self.screen.set_pixel(pixel_coord[0], pixel_coord[1], pixel_rgb[0], pixel_rgb[1], pixel_rgb[2])
        except IndexError:
            raise Exception(f"Set pixel did not like pixel coordinate: {pixel_coord} with RGB value: {pixel_rgb}")
        # todo: improve this greatly and move it out of this class/module
        # if args.mc_mode:
        #     player_x, player_y, player_z = mc.player.getPos()
        #     random.seed(r + g + b)
        #     random_block = random.randint(1, 22)
        #     random.seed()
        #     mc.setBlock(player_x + x, player_y + 10 + current_layer, player_z + y, random_block)

    def show(self):
        """
        Show the current state of the board
        """
        self.screen.show()
