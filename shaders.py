import math
from time import time


class ShaderStack:
    def __init__(self, session_info):
        self.shader_id = 0
        self.shader_stack = {}

        self.session_info = session_info

        self.max_pixel_combine = len(session_info.coord_map)

    def add_to_shader_stack(self, configured_shader):
        self.shader_stack[self.shader_id] = configured_shader
        self.shader_stack[self.shader_id].max_coord_combine = self.max_pixel_combine
        self.shader_id += 1

    def multi_shader_creator(self, input_shader, number_of_shaders=4, base_number=8, base_addition=2,
                             base_rgb=(0.5, 0.5, 0.5)):
        blank = False

        for i in range(number_of_shaders):
            shader_to_configure = input_shader()

            shader_to_configure.max_coord_combine = self.max_pixel_combine
            shader_to_configure.count_number_max = base_number

            if blank:
                shader_to_configure.shader_colour = (0.0, 0.0, 0.0)
            else:
                shader_to_configure.shader_colour = base_rgb

            self.add_to_shader_stack(shader_to_configure)

            blank = not blank
            base_number = base_number + base_addition

    def run_shader_stack(self, pixel_rgb):
        pixel_in = pixel_rgb
        # replace with map()?
        for shader in self.shader_stack.values():
            pixel_in = shader.run_shader(pixel_in)

        return pixel_in


# todo: split all this up into different classes for different shaders, built from a superclass
# WARNING: be careful with these, it can cause flashing images
class ConfigurableShaderSuper:
    max_colour = 255
    max_float = 10.0
    max_coord_combine: int

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1,
                 count_number_step_down=1, addition_shader=True, invert_count=True, shader_colour=(0.5, 0.5, 0.5),
                 static_shader_alpha=0.5):
        self.count_number = count_number
        self.count_number_max = count_number_max

        self.count_number_step_up = count_number_step_up
        self.count_number_step_down = count_number_step_down

        self.addition_shader = addition_shader
        self.invert_count = invert_count

        self.shader_colour = shader_colour
        self.static_shader_alpha = static_shader_alpha

    def calculate_distance(self, coord_1, coord_2):
        dist = math.sqrt((coord_2[0] - coord_1[0]) ** 2 + (coord_2[1] - coord_1[1]) ** 2)
        return round(dist)

    def tone_map(self, sub_pixel):
        sub_pixel = sub_pixel / (sub_pixel + 1.0)

        return sub_pixel

    def convert_float_to_rgb(self, pixel):
        red = round(pixel[0] * self.max_colour)
        green = round(pixel[1] * self.max_colour)
        blue = round(pixel[2] * self.max_colour)

        return red, green, blue

    # thanks to
    # https://stackoverflow.com/questions/52992900/how-to-blend-two-rgb-colors-front-and-back-based-on-their-alpha-channels
    def blend_colour_alpha(self, color_1, color_2, alpha):
        red = (color_1[0] * (self.max_float - alpha) + color_2[0] * alpha) / self.max_float
        green = (color_1[1] * (self.max_float - alpha) + color_2[1] * alpha) / self.max_float
        blue = (color_1[2] * (self.max_float - alpha) + color_2[2] * alpha) / self.max_float
        # todo: get this to stop calculating insanely low values, essentially filling the render plane with 0 rgb vals

        return red, green, blue

    def multiply_colours(self, object_colour):
        red = self.shader_colour[0] * object_colour[0]
        green = self.shader_colour[1] * object_colour[1]
        blue = self.shader_colour[2] * object_colour[2]

        return red, green, blue

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


class FullScreenPatternShader(ConfigurableShaderSuper):

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1, count_number_step_down=1,
                 addition_shader=True, invert_count=True, shader_colour=(0.5, 0.5, 0.5)):
        super().__init__(count_number, count_number_max, count_number_step_up, count_number_step_down, addition_shader,
                         invert_count, shader_colour)

    # found this accidentally; I am not entirely sure how this works, but changing the max number that can be stepped
    # to will result in various cool effects as well as plus/minus stepping and whether the stepping will reset
    # when maxed or count back the other way
    def run_shader(self, pixel):
        if self.addition_shader:
            self.number_count_step_plus()
        else:
            self.number_count_step_minus()

        pixel_alpha = (self.count_number / self.count_number_max) * self.max_float
        shaded_colour = self.blend_colour_alpha(pixel, self.shader_colour, pixel_alpha)

        return shaded_colour


class PerPixelLightingShader(ConfigurableShaderSuper):

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1, count_number_step_down=1,
                 addition_shader=True, invert_count=True, shader_colour=(0.5, 0.5, 0.5)):
        super().__init__(count_number, count_number_max, count_number_step_up, count_number_step_down, addition_shader,
                         invert_count, shader_colour)

        self.light_position = (10, 10)
        self.light_strength = 1.0
        self.moving_light = False
        self.light_move = time() + 3

    def move_light(self):
        if time() > self.light_move:
            plus_zone = (1, 1)
            self.light_position = tuple(
                x + y for x, y in zip(self.light_position, plus_zone))
            self.light_move = time() + 3

    def run_shader(self, coord, pixel):
        if self.moving_light:
            self.move_light()

        pre_distance_shaded_colour = self.multiply_colours(pixel)

        light_distance = (self.calculate_distance(self.light_position, coord)) / self.light_strength

        # must always ensure light distance is at least 1 to prevent divide by zero errors
        if light_distance == 0:
            light_distance = 1 / self.light_strength

        red = self.shader_colour[0] * pre_distance_shaded_colour[0] / abs(light_distance)
        green = self.shader_colour[1] * pre_distance_shaded_colour[1] / abs(light_distance)
        blue = self.shader_colour[2] * pre_distance_shaded_colour[2] / abs(light_distance)

        shaded_colour = (red, green, blue)

        return shaded_colour


class FullScreenGradientShader(ConfigurableShaderSuper):

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1, count_number_step_down=1,
                 addition_shader=True, invert_count=True, shader_colour=(0.5, 0.5, 0.5)):
        super().__init__(count_number, count_number_max, count_number_step_up, count_number_step_down, addition_shader,
                         invert_count, shader_colour)

    def run_shader(self, coord, pixel):
        output_from_coord = coord[0] * coord[1]

        pixel_alpha = (output_from_coord / self.max_coord_combine) * self.max_float
        shaded_colour = self.blend_colour_alpha(pixel, self.shader_colour, pixel_alpha)

        return shaded_colour


class ToneMapShader(ConfigurableShaderSuper):

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1, count_number_step_down=1,
                 addition_shader=True, invert_count=True, shader_colour=(0.5, 0.5, 0.5)):
        super().__init__(count_number, count_number_max, count_number_step_up, count_number_step_down, addition_shader,
                         invert_count, shader_colour)

    def run_shader(self, pixel):
        red = self.tone_map(pixel[0])
        green = self.tone_map(pixel[1])
        blue = self.tone_map(pixel[2])

        shaded_colour = (red, green, blue)

        return shaded_colour


class MotionBlurShader(ConfigurableShaderSuper):

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1, count_number_step_down=1,
                 addition_shader=True, invert_count=True, shader_colour=(0.5, 0.5, 0.5)):
        super().__init__(count_number, count_number_max, count_number_step_up, count_number_step_down, addition_shader,
                         invert_count, shader_colour)

    def run_shader(self, pixel, second_pixel=None):
        if not second_pixel:
            second_pixel = self.shader_colour
        shaded_colour = self.blend_colour_alpha(pixel, second_pixel, self.static_shader_alpha)

        if sum(shaded_colour) > 0.1:
            return shaded_colour
        else:
            return None


class FloatToRGBShader(ConfigurableShaderSuper):

    def __init__(self, count_number=0, count_number_max=32, count_number_step_up=1, count_number_step_down=1,
                 addition_shader=True, invert_count=True, shader_colour=(0.5, 0.5, 0.5)):
        super().__init__(count_number, count_number_max, count_number_step_up, count_number_step_down, addition_shader,
                         invert_count, shader_colour)

    def run_shader(self, pixel):
        converted_pixel = self.convert_float_to_rgb(pixel)

        return converted_pixel
