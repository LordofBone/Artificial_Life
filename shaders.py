class ShaderStack:
    def __init__(self, width, height):
        self.shader_id = 0
        self.shader_stack = {}
        self.max_pixel_combine = width * height

    def add_to_shader_stack(self, configured_shader):
        self.shader_stack[self.shader_id] = configured_shader
        self.shader_stack[self.shader_id].max_coord_combine = self.max_pixel_combine
        self.shader_id += 1

    def multi_shader_creator(self, input_shader, number_of_shaders=4, base_number=8, base_addition=2, base_rgb=(128, 128, 128)):
        blank = False

        for i in range(number_of_shaders):
            shader_to_configure = input_shader()

            shader_to_configure.max_coord_combine = self.max_pixel_combine
            shader_to_configure.count_number_max = base_number

            if blank:
                shader_to_configure.shader_colour = (0, 0, 0)
            else:
                shader_to_configure.shader_colour = base_rgb

            self.add_to_shader_stack(shader_to_configure)

            blank = not blank
            base_number = base_number + base_addition

        print(self.shader_stack)

    def run_shader_stack(self, pixel_rgb):
        pixel_in = pixel_rgb

        for shader in self.shader_stack.values():
            pixel_in = shader.run_shader(pixel_in)

        return pixel_in


class ConfigurableShader:
    max_colour = 255
    max_coord_combine: int

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1,
                 count_number_step_down=1, addition_shader=True, invert_count=True, shader_colour=(128, 128, 128)):
        self.count_number = count_number
        self.count_number_max = count_number_max

        self.count_number_step_up = count_number_step_up
        self.count_number_step_down = count_number_step_down

        self.addition_shader = addition_shader
        self.invert_count = invert_count

        self.shader_colour = shader_colour

    # thanks to
    # https://stackoverflow.com/questions/52992900/how-to-blend-two-rgb-colors-front-and-back-based-on-their-alpha-channels
    def blend_shader(self, color_1, color_2, alpha):
        red = (color_1[0] * (self.max_colour - alpha) + color_2[0] * alpha) / self.max_colour
        green = (color_1[1] * (self.max_colour - alpha) + color_2[1] * alpha) / self.max_colour
        blue = (color_1[2] * (self.max_colour - alpha) + color_2[2] * alpha) / self.max_colour
        return int(red), int(green), int(blue)

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
        shaded_colour = self.custom_rgb_shader(pixel, self.shader_colour, pixel_alpha)

        return shaded_colour

    # found this accidentally; I am not entirely sure how this works, but changing the max number that can be stepped
    # to will result in various cool effects as well as plus/minus stepping and whether the stepping will reset
    # when maxed or count back the other way
    def run_shader(self, pixel):
        if self.addition_shader:
            self.number_count_step_plus()
        else:
            self.number_count_step_minus()

        pixel_alpha = (self.count_number / self.count_number_max) * self.max_colour
        shaded_colour = self.custom_rgb_shader(pixel, self.shader_colour, pixel_alpha)

        return shaded_colour
