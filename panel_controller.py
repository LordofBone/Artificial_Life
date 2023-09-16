from rgbmatrix import RGBMatrix, RGBMatrixOptions


class PanelSetup:
    DEFAULT_OPTIONS = {
        'chain_length': 1,
        'parallel': 1,
        'row_address_type': 0,
        'multiplexing': 0,
        'pwm_bits': 11,
        'pwm_lsb_nanoseconds': 130,
        'led_rgb_sequence': "RGB",
        'pixel_mapper_config': "",
        'panel_type': "",
        'show_refresh_rate': 0,
        'gpio_slowdown': 4,
        'disable_hardware_pulsing': False,
        'drop_privileges': True,
    }

    def __init__(self, panel_x, panel_y, led_brightness):
        self.options = RGBMatrixOptions()
        self.setup_options(panel_x, panel_y, led_brightness)
        self.matrix = RGBMatrix(options=self.options)

    def setup_options(self, panel_x, panel_y, led_brightness):
        self.options.rows = panel_y
        self.options.cols = panel_x
        self.options.brightness = int(led_brightness*100)

        for option, value in self.DEFAULT_OPTIONS.items():
            setattr(self.options, option, value)


class PanelController(PanelSetup):
    def __init__(self, panel_x, panel_y, led_brightness):
        super().__init__(panel_x, panel_y, led_brightness)
        self.offset_canvas = self.matrix.CreateFrameCanvas()

    def set_pixel(self, x, y, r, g, b):
        """
        Sets a pixel on the screen to the specified RGB color

        :param x: x-coordinate of the pixel
        :param y: y-coordinate of the pixel
        :param r: Red component of the color
        :param g: Green component of the color
        :param b: Blue component of the color
        """
        self.offset_canvas.SetPixel(x, y, r, g, b)

    def get_shape(self):
        """
        Returns the shape (rows and columns) of the panel
        """
        return self.options.cols, self.options.rows

    def show(self):
        """
        Refreshes the screen to reflect the current state
        """
        self.matrix.SwapOnVSync(self.offset_canvas)
