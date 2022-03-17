
class Shaders:
    def __init__(self):
        self.max_colour = 255
        self.base_red = (128, 0, 0)
        self.base_green = (0, 128, 0)
        self.base_blue = (0, 0, 128)
        self.base_white = (128, 128, 128)
        self.super_red = (255, 0, 0)
        self.super_green = (0, 255, 0)
        self.super_blue = (0, 0, 255)
        self.super_white = (255, 255, 255)

    # thanks to
    # https://stackoverflow.com/questions/52992900/how-to-blend-two-rgb-colors-front-and-back-based-on-their-alpha-channels
    def blend_shader(self, color_1, color_2, alpha):
        red = (color_1[0] * (self.max_colour - alpha) + color_2[0] * alpha) / self.max_colour
        green = (color_1[1] * (self.max_colour - alpha) + color_2[1] * alpha) / self.max_colour
        blue = (color_1[2] * (self.max_colour - alpha) + color_2[2] * alpha) / self.max_colour
        return int(red), int(green), int(blue)

    def red_shader(self, input_colour):
        shaded_colour = self.blend_shader(input_colour, self.base_red, alpha=128)
        return shaded_colour

    def green_shader(self, input_colour):
        shaded_colour = self.blend_shader(input_colour, self.base_green, alpha=128)
        return shaded_colour

    def blue_shader(self, input_colour):
        shaded_colour = self.blend_shader(input_colour, self.base_blue, alpha=128)
        return shaded_colour

    def white_shader(self, input_colour):
        shaded_colour = self.blend_shader(input_colour, self.base_white, alpha=128)
        return shaded_colour

    def custom_rgb_shader(self, input_colour, blend_colour, alpha_custom):
        shaded_colour = self.blend_shader(input_colour, blend_colour, alpha_custom)
        return shaded_colour

    def full_screen_shader_gradient(self, coord, pixel):
        output_from_coord = coord[0] + coord[1]
        pixel_alpha = (output_from_coord / 255) * 255
        shaded_colour = self.custom_rgb_shader(pixel, self.base_blue, pixel_alpha)
        return shaded_colour
