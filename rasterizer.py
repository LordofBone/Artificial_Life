from time import time
import logging
from shaders import Shaders

logger = logging.getLogger("rasterizer-logger")


class FrameBuffer:
    def __init__(self):
        self.front_buffer = {}
        self.back_buffer = {}
        self.current_buffer_front = True
        self.blank_pixel = (0, 0, 0)

    def generate_buffers(self, width, height):
        for x_position in range(width):
            for y_position in range(height):
                self.front_buffer[(x_position, y_position)] = self.blank_pixel
                self.back_buffer[(x_position, y_position)] = self.blank_pixel

    def write_to_buffer(self, x, y, r, g, b):
        base_colour = (r, g, b)
        if self.current_buffer_front:
            self.front_buffer[(x, y)] = base_colour
        else:
            self.back_buffer[(x, y)] = base_colour

    def flip_buffers(self):
        self.current_buffer_front = not self.current_buffer_front

    def clear_buffer_pixel(self, coord):
        if self.current_buffer_front:
            self.front_buffer[coord] = self.blank_pixel


class ScreenDrawer:
    def __init__(self, hat_controller, buffer_refresh):
        self.hat_control = hat_controller
        self.frame_refresh_delay_ms = 1 / buffer_refresh
        logger.debug(f'Milliseconds per-frame to aim for: {self.frame_refresh_delay_ms}')

        self.max_pixel_combine = self.hat_control.u_width_max * self.hat_control.u_height_max

        frame_buffer_access.generate_buffers(self.hat_control.u_width, self.hat_control.u_height)

        self.shader_access = Shaders(self.max_pixel_combine)

        # todo: make this configurable by parameters.py and/or argsparse
        self.gradient_background = True

        self.draw()

    def draw(self):
        next_frame = time() + self.frame_refresh_delay_ms

        while True:

            if time() > next_frame:
                if frame_buffer_access.current_buffer_front:
                    for coord, pixel in frame_buffer_access.front_buffer.items():
                        if self.gradient_background:
                            pixel = self.shader_access.full_screen_shader_gradient(coord, pixel)
                        self.hat_control.draw_pixels(x=coord[0], y=coord[1], r=pixel[0], g=pixel[1],
                                                     b=pixel[2])
                else:
                    for coord, pixel in frame_buffer_access.back_buffer.items():
                        if self.gradient_background:
                            pixel = self.shader_access.full_screen_shader_gradient(coord, pixel)
                        self.hat_control.draw_pixels(x=coord[0], y=coord[1], r=pixel[0], g=pixel[1],
                                                     b=pixel[2])

                self.hat_control.unicorn.show()

                next_frame = time() + self.frame_refresh_delay_ms


frame_buffer_access = FrameBuffer()
