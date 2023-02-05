from rgbmatrix import RGBMatrix, RGBMatrixOptions


class PanelSetup(object):
    def __init__(self, panel_x, panel_y, led_brightness):
        self.options = RGBMatrixOptions()
        self.options.rows = panel_y
        self.options.cols = panel_x
        self.options.chain_length = 1
        self.options.parallel = 1
        self.options.row_address_type = 0
        self.options.multiplexing = 0
        self.options.pwm_bits = 11
        self.options.brightness = int(led_brightness*100)
        self.options.pwm_lsb_nanoseconds = 130
        self.options.led_rgb_sequence = "RGB"
        self.options.pixel_mapper_config = ""
        self.options.panel_type = ""
        self.options.show_refresh_rate = 0
        self.options.gpio_slowdown = 4
        self.options.disable_hardware_pulsing = False
        self.options.drop_privileges = True

        self.matrix = RGBMatrix(options=self.options)


class PanelController(PanelSetup):
    def __init__(self, panel_x, panel_y, led_brightness):
        super(PanelController, self).__init__(panel_x, panel_y, led_brightness)
        self.offset_canvas = self.matrix.CreateFrameCanvas()

    def set_pixel(self, x, y, r, g, b):
        """
        Set a pixel on the screen
        :param x:
        :param y:
        :param r:
        :param g:
        :param b:
        :return:
        """
        self.offset_canvas.SetPixel(x, y, r, g, b)

    def get_shape(self):
        """
        Get the shape of the panel for use in the simulator logic
        :return:
        """
        return self.options.cols, self.options.rows

    def show(self):
        """
        Show the screen, nothing will be displayed until this is called
        :return:
        """
        self.matrix.SwapOnVSync(self.offset_canvas)
