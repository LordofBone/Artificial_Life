from rgbmatrix import RGBMatrix, RGBMatrixOptions


class PanelSetup(object):
    def __init__(self):
        self.options = RGBMatrixOptions()
        self.options.rows = 32
        self.options.cols = 64
        self.options.chain_length = 1
        self.options.parallel = 1
        self.options.row_address_type = 0
        self.options.multiplexing = 0
        self.options.pwm_bits = 11
        self.options.brightness = 100
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
    def __init__(self):
        super(PanelController, self).__init__()
        self.offset_canvas = self.matrix.CreateFrameCanvas()

    def set_pixel(self, x, y, r, g, b):
        self.offset_canvas.SetPixel(x, y, r, g, b)

    def get_shape(self):
        return self.options.cols, self.options.rows

    def show(self):
        self.matrix.SwapOnVSync(self.offset_canvas)
