
class Shaders:
    def __init__(self, max_coord_combine):
        self.max_colour = 255
        self.base_red = (128, 0, 0)
        self.base_green = (0, 128, 0)
        self.base_blue = (0, 0, 128)
        self.base_white = (128, 128, 128)
        self.super_red = (255, 0, 0)
        self.super_green = (0, 255, 0)
        self.super_blue = (0, 0, 255)
        self.super_white = (255, 255, 255)

        self.max_coord_combine = max_coord_combine

        self.count_number = 0
        self.count_number_max = 256

        self.addition_shader = True
        self.invert_count = True

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

    def number_count_step_plus(self):
        if self.count_number < self.count_number_max:
            self.count_number += 1
        else:
            if self.invert_count:
                self.addition_shader = not self.addition_shader
            else:
                self.count_number = 0

    def number_count_step_minus(self):
        if self.count_number > 0:
            self.count_number -= 1
        else:
            if self.invert_count:
                self.addition_shader = not self.addition_shader
            else:
                self.count_number = self.count_number_max

    def full_screen_shader_gradient(self, coord, pixel):
        output_from_coord = coord[0] * coord[1]

        pixel_alpha = (output_from_coord / self.max_coord_combine) * self.max_colour
        shaded_colour = self.custom_rgb_shader(pixel, self.base_green, pixel_alpha)

        return shaded_colour

    # found this accidentally; I am not entirely sure how this works, but changing the max number that can be stepped
    # to will result in various cool effects as well as plus/minus stepping and whether the stepping will reset
    # when maxed or count back the other way
    def full_screen_shader_2(self, pixel):
        if self.addition_shader:
            self.number_count_step_plus()
        else:
            self.number_count_step_minus()

        pixel_alpha = (self.count_number / self.count_number_max) * self.max_colour
        shaded_colour = self.custom_rgb_shader(pixel, self.base_green, pixel_alpha)

        return shaded_colour
