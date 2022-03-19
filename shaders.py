class Shaders:
    max_colour = 255
    base_red = (128, 0, 0)
    base_green = (0, 128, 0)
    base_blue = (0, 0, 128)
    base_white = (128, 128, 128)
    super_red = (255, 0, 0)
    super_green = (0, 255, 0)
    super_blue = (0, 0, 255)
    super_white = (255, 255, 255)

    def __init__(self, max_coord_combine, count_number=0, count_number_max=32, count_number_step_up=1, count_number_step_down=1, addition_shader=True, invert_count=True):
        self.max_coord_combine = max_coord_combine

        self.count_number = count_number
        self.count_number_max = count_number_max

        self.count_number_step_up = count_number_step_up
        self.count_number_step_down = count_number_step_down

        self.addition_shader = addition_shader
        self.invert_count = invert_count

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
            self.count_number += self.count_number_step_up
        else:
            if self.invert_count:
                self.addition_shader = not self.addition_shader
            else:
                self.count_number = 0

    def number_count_step_minus(self):
        if self.count_number > 0:
            self.count_number -= self.count_number_step_down
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
