from time import time
import logging
from shaders import FullScreenPatternShader, PerPixelLightingShader, MotionBlurShader, \
    FullScreenGradientShader, \
    FloatToRGBShader, ShaderStack, ToneMapShader

logger = logging.getLogger("rasterizer-logger")


class PreBuffer:
    def __init__(self):
        self.template_pre_buffer = {}

        self.pre_buffer = {}
        self.blank_pixel = (0.0, 0.0, 0.0), -1

        self.buffer_ready = False

    def write_to_buffer(self, pixel_coord, pixel_rgb, entity_id):
        self.pre_buffer[pixel_coord] = pixel_rgb, entity_id

    def get_from_buffer(self, pixel_coord):
        try:
            return self.pre_buffer[pixel_coord]
        except KeyError:
            return None

    def del_buffer_pixel(self, coord):
        try:
            del self.pre_buffer[coord]
        except KeyError:
            pass


class FrameBuffer:
    def __init__(self, session_info):
        self.front_buffer = {}
        self.back_buffer = {}

        self.render_plane = {}

        self.previous_frame = {}

        self.session_info = session_info

        self.current_buffer_front = True
        self.blank_pixel = (0.0, 0.0, 0.0)

        self.shader_stack = ShaderStack(self.session_info)

        # WARNING: be careful with these, it can cause flashing images
        # self.shader_stack.multi_shader_creator(input_shader=FullScreenPatternShader, number_of_shaders=2, base_number=4,
        #                                        base_addition=16, base_rgb=(1.25, 0.0, 0.0))
        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=32, shader_colour=(0.0, 1.25, 0.0)))
        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=31, shader_colour=(0.0, 0.0, 1.25)))

        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=7, shader_colour=(0.0, 1.0, 0.0)))

        self.motion_blur = MotionBlurShader()

        self.motion_blur.shader_colour = (0.0, 0.0, 0.0)
        self.motion_blur.static_shader_alpha = 0.9

        self.lighting = PerPixelLightingShader()
        self.lighting.shader_colour = (1.0, 1.0, 1.0)
        self.lighting.light_strength = 10.0
        self.lighting.moving_light = False

        self.tone_map = ToneMapShader()

        self.float_to_rgb = FloatToRGBShader()

    def log_current_frame(self):
        self.previous_frame = self.render_plane.copy()

    def return_previous_frame(self):
        return self.previous_frame.copy()

    def write_to_render_plane(self, pixel_coord, pixel_rgb):
        self.render_plane[pixel_coord] = pixel_rgb

    def write_to_previous_frame(self, pixel_coord, pixel_rgb):
        self.previous_frame[pixel_coord] = pixel_rgb

    def get_from_render_plane(self, pixel_coord):
        try:
            pixel_rgb = self.render_plane[pixel_coord]
            return pixel_rgb
        except KeyError:
            return 0.0, 0.0, 0.0

    def blit_render_plane_to_buffer(self):
        if self.current_buffer_front:
            self.front_buffer = self.render_plane.copy()
        else:
            self.back_buffer = self.render_plane.copy()

    def render_render_plane_to_buffer(self):
        [self.write_to_buffer(coord, self.get_from_render_plane(coord)) for coord in self.session_info.coord_map]

    def write_to_buffer(self, pixel_coord, pixel_rgb):
        if self.current_buffer_front:
            self.front_buffer[pixel_coord] = pixel_rgb
        else:
            self.back_buffer[pixel_coord] = pixel_rgb

    def return_buffer(self):
        if self.current_buffer_front:
            return self.front_buffer
        else:
            return self.back_buffer

    def get_from_buffer(self, pixel_coord):
        try:
            if self.current_buffer_front:
                pixel_rgb = self.front_buffer[pixel_coord]
            else:
                pixel_rgb = self.back_buffer[pixel_coord]

            return pixel_rgb
        except KeyError:
            return None

    def flip_buffers(self):
        self.current_buffer_front = not self.current_buffer_front

    def flush_buffer(self):
        self.render_plane = {}

        if self.current_buffer_front:
            self.front_buffer = {}
        else:
            self.back_buffer = {}


class ScreenDrawer:
    def __init__(self, output_controller, buffer_refresh, session_info):
        self.session_info = session_info
        self.hat_control = output_controller
        self.frame_refresh_delay_ms = 1 / buffer_refresh
        logger.debug(f'Milliseconds per-frame to aim for: {self.frame_refresh_delay_ms}')

        self.frame_buffer_access = FrameBuffer(self.session_info)

        self.next_frame = time() + self.frame_refresh_delay_ms

        self.draw()

    def float_to_rgb_pass(self):
        [self.frame_buffer_access.write_to_buffer(coord, self.frame_buffer_access.float_to_rgb.run_shader(pixel)) for
         coord, pixel in
         self.frame_buffer_access.front_buffer.items()]

    def object_colour_pass(self):
        [self.frame_buffer_access.write_to_render_plane(coord, pixel[0]) for coord, pixel in
         pre_buffer_access.pre_buffer.copy().items()]

    def background_shader_pass(self):
        [self.frame_buffer_access.write_to_render_plane(coord, self.frame_buffer_access.shader_stack.run_shader_stack(
            self.frame_buffer_access.get_from_render_plane(coord)))
         for coord in
         self.session_info.coord_map]

    def lighting_pass(self):
        [self.frame_buffer_access.write_to_render_plane(coord,
                                                        self.frame_buffer_access.lighting.run_shader(coord, pixel))
         for coord, pixel in self.frame_buffer_access.render_plane.items()]

    def tone_map_pass(self):
        [self.frame_buffer_access.write_to_render_plane(coord, self.frame_buffer_access.tone_map.run_shader(pixel))
         for coord, pixel in self.frame_buffer_access.render_plane.items()]

    def buffer_scan(self):
        [self.draw_to_output(coord, pixel) for coord, pixel in self.frame_buffer_access.return_buffer().items()]

        self.hat_control.unicorn.show()

    def buffer_flip(self):
        self.frame_buffer_access.flip_buffers()

    def log_current_frame(self):
        self.frame_buffer_access.log_current_frame()

    def blit_render_plane(self):
        self.frame_buffer_access.blit_render_plane_to_buffer()

    def render_frame_buffer(self):
        self.frame_buffer_access.render_render_plane_to_buffer()

    def draw_to_output(self, coord, pixel):
        self.hat_control.draw_pixels(coord, pixel)

    def motion_blur_pass(self):
        # todo: convert this to list comprehension? and tidy it up
        for coord, pixel in self.frame_buffer_access.return_previous_frame().items():
            try:
                new_pixel = self.frame_buffer_access.motion_blur.run_shader(pixel,
                                                                            self.frame_buffer_access.render_plane[
                                                                                coord])
            except KeyError:
                new_pixel = self.frame_buffer_access.motion_blur.run_shader(pixel)
            if new_pixel:
                self.frame_buffer_access.write_to_render_plane(coord, new_pixel)

    def lensing_pass(self):
        # todo: convert this to list comprehension
        # this is similar function to motion blur but it results in some
        # weird/cool effects when implemented after background and lighting passes, causes the background to react
        # to the lighting
        for coord, pixel in self.frame_buffer_access.return_previous_frame().items():
            new_pixel = self.frame_buffer_access.motion_blur.run_shader(pixel)
            if new_pixel:
                self.frame_buffer_access.write_to_render_plane(coord, new_pixel)

    def flush_buffer(self):
        self.frame_buffer_access.flush_buffer()

    def draw(self):
        # you can get some different/cool effects by swapping things about here
        render_stack = ['background_shader_pass',
                        'object_colour_pass',
                        'log_current_frame',
                        'tone_map_pass',
                        'render_frame_buffer',
                        'float_to_rgb_pass',
                        'buffer_scan',
                        'flush_buffer']

        try:
            while True:
                [getattr(self, render_stage)() for render_stage in render_stack]

                if time() > self.next_frame:
                    # todo: do something clever with buffer flipping here?
                    pass

        # upon keyboard interrupt display information about the program run before exiting
        except KeyboardInterrupt:
            logger.info(
                f'Program ended by user.\n Total life forms produced: {self.session_info.life_form_total_count}\n Max '
                f'concurrent Lifeforms was: {self.session_info.highest_concurrent_lifeforms}\n Last count of active '
                f'Lifeforms: {self.session_info.current_life_form_amount}')
            self.frame_buffer_access.flush_buffer()
            self.buffer_scan()


pre_buffer_access = PreBuffer()
