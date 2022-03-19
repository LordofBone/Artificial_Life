from time import time
import logging
from shaders import Shaders

logger = logging.getLogger("rasterizer-logger")


class PreBuffer:
    def __init__(self):
        self.pre_buffer = {}
        self.blank_pixel = (0, 0, 0)

    def generate_buffer(self, width, height):
        for x_position in range(width):
            for y_position in range(height):
                self.pre_buffer[(x_position, y_position)] = self.blank_pixel

    def write_to_buffer(self, pixel_coord, pixel_rgb):
        self.pre_buffer[pixel_coord] = pixel_rgb

    def clear_buffer_pixel(self, coord):
        self.pre_buffer[coord] = self.blank_pixel


class FrameBuffer:
    def __init__(self, buffer_width, buffer_height):
        self.front_buffer = {}
        self.back_buffer = {}

        self.current_buffer_front = True
        self.blank_pixel = (0, 0, 0)

        self.buffer_width = buffer_width
        self.buffer_height = buffer_height

        self.max_pixel_combine = buffer_width * buffer_height

        self.shader = Shaders(self.max_pixel_combine)

    def generate_buffers(self, width, height):
        for x_position in range(width):
            for y_position in range(height):
                self.front_buffer[(x_position, y_position)] = self.blank_pixel
                self.back_buffer[(x_position, y_position)] = self.blank_pixel

    def write_to_buffer(self, pixel_coord, pixel_rgb):
        pixel_rgb = self.shader.full_screen_shader_2(pixel_rgb)
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
    def __init__(self, hat_controller, buffer_refresh):
        self.hat_control = hat_controller
        self.frame_refresh_delay_ms = 1 / buffer_refresh
        logger.debug(f'Milliseconds per-frame to aim for: {self.frame_refresh_delay_ms}')

        self.frame_buffer_access = FrameBuffer(self.hat_control.u_width, self.hat_control.u_height)

        pre_buffer_access.generate_buffer(self.hat_control.u_width, self.hat_control.u_height)

        self.draw()

    def draw(self):
        next_frame = time() + self.frame_refresh_delay_ms

        while True:

            if time() > next_frame:
                for coord, pixel in pre_buffer_access.pre_buffer.items():
                    self.frame_buffer_access.write_to_buffer(coord, pixel)
                    final_pixel = self.frame_buffer_access.get_from_buffer(coord)
                    self.hat_control.draw_pixels(coord, final_pixel)

                self.hat_control.unicorn.show()

                next_frame = time() + self.frame_refresh_delay_ms


pre_buffer_access = PreBuffer()
