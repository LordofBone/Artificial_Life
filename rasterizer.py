from time import time
import logging
from shaders import ConfigurableShader, ShaderStack

logger = logging.getLogger("rasterizer-logger")


# todo: move the pre-buffer into artificial_life.py ?
class PreBuffer:
    def __init__(self):
        self.pre_buffer = {}
        self.blank_pixel = (0, 0, 0), -1

        self.buffer_ready = False

    def generate_buffer(self, coord_map):
        for pos in coord_map:
            self.pre_buffer[pos] = self.blank_pixel

        self.buffer_ready = True

    def write_to_buffer(self, pixel_coord, pixel_rgb, entity_id):
        self.pre_buffer[pixel_coord] = pixel_rgb, entity_id

    def get_from_buffer(self, pixel_coord):
        pixel_rgb = self.pre_buffer[pixel_coord]

        if not pixel_rgb[0] == (0, 0, 0):
            return pixel_rgb[1]

    def check_buffer_position(self, pixel_coord):
        try:
            pixel_out = self.pre_buffer[pixel_coord]
            if pixel_out == self.blank_pixel:
                return pixel_coord
        except KeyError:
            return

    def clear_buffer_pixel(self, coord):
        self.pre_buffer[coord] = self.blank_pixel


class FrameBuffer:
    def __init__(self, session_info):
        self.front_buffer = {}
        self.back_buffer = {}

        self.session_info = session_info

        self.current_buffer_front = True
        self.blank_pixel = (0, 0, 0)

        self.shader_stack = ShaderStack(self.session_info)

        self.generate_buffers()

        # WARNING: be careful with these, it can cause flashing images
        self.shader_stack.multi_shader_creator(input_shader=ConfigurableShader, number_of_shaders=2, base_number=4,
                                               base_addition=16, base_rgb=(64, 0, 0))
        self.shader_stack.add_to_shader_stack(ConfigurableShader(count_number_max=32, shader_colour=(0, 64, 0)))
        self.shader_stack.add_to_shader_stack(ConfigurableShader(count_number_max=31, shader_colour=(0, 0, 64)))

        self.motion_blur = ConfigurableShader()

    def generate_buffers(self):
        for pos in self.session_info.coord_map:
            self.front_buffer[pos] = self.blank_pixel
            self.back_buffer[pos] = self.blank_pixel

    def write_to_buffer(self, pixel_coord, pixel_rgb):
        if self.current_buffer_front:
            self.front_buffer[pixel_coord] = pixel_rgb
        else:
            self.back_buffer[pixel_coord] = pixel_rgb

    def get_from_buffer(self, pixel_coord):
        if self.current_buffer_front:
            pixel_rgb = self.front_buffer[pixel_coord]
        else:
            pixel_rgb = self.back_buffer[pixel_coord]

        return pixel_rgb

    def flip_buffers(self):
        self.current_buffer_front = not self.current_buffer_front


class ScreenDrawer:
    def __init__(self, hat_controller, buffer_refresh, session_info):
        self.session_info = session_info
        self.hat_control = hat_controller
        self.frame_refresh_delay_ms = 1 / buffer_refresh
        logger.debug(f'Milliseconds per-frame to aim for: {self.frame_refresh_delay_ms}')

        self.frame_buffer_access = FrameBuffer(self.session_info)

        pre_buffer_access.generate_buffer(self.session_info.coord_map)

        self.draw()

    def life_form_pass(self):
        [self.frame_buffer_access.write_to_buffer(coord, pixel[0]) for coord, pixel in
         pre_buffer_access.pre_buffer.items() if not pixel[0] == (0, 0, 0)]

    def shader_pass(self):
        [self.frame_buffer_access.write_to_buffer(coord, self.frame_buffer_access.shader_stack.run_shader_stack(pixel))
         for coord, pixel in
         self.frame_buffer_access.front_buffer.items()]

    def buffer_scan(self):
        [self.draw_to_output(coord, pixel) for coord, pixel in self.frame_buffer_access.front_buffer.items()]

        self.hat_control.unicorn.show()

    def draw_to_output(self, coord, pixel):
        self.hat_control.draw_pixels(coord, pixel)

        self.frame_buffer_access.write_to_buffer(coord, (
            self.frame_buffer_access.motion_blur.custom_rgb_shader(pixel, (0, 0, 0), 128)))

    def draw(self):
        next_frame = time() + self.frame_refresh_delay_ms
        try:
            while True:
                self.shader_pass()

                self.life_form_pass()

                self.buffer_scan()

                if time() > next_frame:
                    # todo: do something clever with buffer flipping here?
                    pass

                next_frame = time() + self.frame_refresh_delay_ms

        # upon keyboard interrupt display information about the program run before exiting
        except KeyboardInterrupt:
            logger.info(
                f'Program ended by user.\n Total life forms produced: {self.session_info.life_form_total_count}\n Max '
                f'concurrent Lifeforms was: {self.session_info.highest_concurrent_lifeforms}\n Last count of active '
                f'Lifeforms: {self.session_info.current_life_form_amount}')
            self.frame_buffer_access.generate_buffers()
            self.buffer_scan()


pre_buffer_access = PreBuffer()
