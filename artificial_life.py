import argparse
import itertools
import logging
import os
import random
import json
from dataclasses import asdict
from math import floor, sqrt
import sys
from dataclasses import dataclass
from time import time
import datetime

from screen_output import ScreenController

from pynput.keyboard import KeyCode, Listener

from collections import deque

from pixel_composer.rasterizer import ScreenDrawer, FrameBuffer, FullScreenPatternShader, PerPixelLightingShader, \
    MotionBlurShader, FullScreenGradientShader, FloatToRGBShader, ShaderStack, ToneMapShader, SpriteShader

from threading import Thread

from config.parameters import *

logger = logging.getLogger("alife-logger")


def diagonal_distance(x1, y1, x2, y2):
    """
    Calculates the diagonal distance between two points
    :param x1:
    :param y1:
    :param x2:
    :param y2:
    :return:
    """
    x_distance = x2 - x1
    y_distance = y2 - y1
    return sqrt(x_distance ** 2 + y_distance ** 2)


@dataclass
class Session:
    """
    This class holds all the parameters for the current session
    """
    highest_concurrent_lifeforms: int
    building_entities: bool
    max_enemy_factor: int
    wall_chance_multiplier: int
    draw_trails: bool
    retries: bool
    radiation_change: bool
    radiation: int
    radiation_curve = [(0, 0.5), (1, 2), (2, 1), (3, 1.5)]
    radiation_base_change_chance: float
    dna_chaos_chance: int
    max_attribute: int
    radiation_max: int
    gravity_on: bool
    current_session_start_time: datetime
    rendering_on: bool = False
    max_movement: int = 0
    coord_map: tuple = ()
    last_removal: int = -1
    current_life_form_amount: int = 0
    life_form_total_count: int = 0
    process_loop_on: bool = True

    directions = ('move_up', 'move_down', 'move_left', 'move_right', 'move_up_and_right',
                  'move_down_and_left', 'move_up_and_left', 'move_down_and_right', 'still')

    surrounding_point_choices = ('get_position_up', 'get_position_down', 'get_position_left',
                                 'get_position_right', 'get_position_up_and_right',
                                 'get_position_up_and_left', 'get_position_down_and_left',
                                 'get_position_down_and_right')

    def __post_init__(self):
        self.coord_map = tuple(
            (x, y) for x in range(screen_controller.u_width) for y in range(screen_controller.u_height))

        self.get_coord_map()

        self.free_board_positions.extend(self.shuffled_coord_map)

        self.base_radiation = self.radiation

    def get_coord_map(self):
        """
        This method creates a shuffled list of coordinates
        :return:
        """
        self.shuffled_coord_map = list(self.coord_map)

        random.shuffle(self.shuffled_coord_map)

        self.free_board_positions = deque()

        self.free_board_positions.extend(self.shuffled_coord_map)

    def get_dna_chaos_chance(self):
        """
        This method calculates the chance of a lifeforms DNA being mutated
        :return:
        """
        return self.dna_chaos_chance + percentage(self.radiation, self.dna_chaos_chance)

    def adjust_radiation_along_curve(self):
        """
        This method adjusts the radiation level according to the radiation curve
        :return:
        """
        if random.random() > self.radiation_base_change_chance:
            pass
        else:
            self.base_radiation = floor(self.radiation_max * random.random())

        self.radiation = max(
            min(self.radiation_max, int(self.base_radiation * random.uniform(min([y for x, y in self.radiation_curve]),
                                                                             max([y for x, y in
                                                                                  self.radiation_curve])))), 0)


class WorldSpaceControl:
    def __init__(self):
        self.template_world_space = {}

        self.world_space = {}

        self.world_space_2 = {}

        self.world_time = 0

        self.world_space_time = {}

        self.buffer_ready = False

    def write_to_world_space(self, pixel_coord, pixel_rgb, entity_id, world_space_selector=1):
        """
        This method writes to the world space
        :param pixel_coord:
        :param pixel_rgb:
        :param entity_id:
        :param world_space_selector:
        :return:
        """
        if world_space_selector == 1:
            self.world_space[pixel_coord] = pixel_rgb, entity_id
        elif world_space_selector == 2:
            self.world_space_2[pixel_coord] = pixel_rgb, entity_id

    def return_world_space(self, world_space_selector=1):
        """
        This method returns the world space
        :param world_space_selector:
        :return:
        """
        if world_space_selector == 1:
            return {key: value[0] for key, value in self.world_space.copy().items()}
        elif world_space_selector == 2:
            world_space_2_return = {key: value[0] for key, value in self.world_space_2.copy().items()}
            self.world_space_2 = {}
            return world_space_2_return

    def get_from_world_space(self, pixel_coord, world_space_selector=1):
        """
        This method returns the value of a pixel in the world space
        :param pixel_coord:
        :param world_space_selector:
        :return:
        """
        if world_space_selector == 1:
            try:
                return self.world_space[pixel_coord]
            except KeyError:
                return None
        elif world_space_selector == 2:
            try:
                return self.world_space_2[pixel_coord]
            except KeyError:
                return None

    def del_world_space_item(self, coord, world_space_selector=1):
        """
        This method deletes an item from the world space
        :param coord:
        :param world_space_selector:
        :return:
        """
        if world_space_selector == 1:
            try:
                del self.world_space[coord]
            except KeyError:
                pass
        elif world_space_selector == 2:
            try:
                del self.world_space_2[coord]
            except KeyError:
                pass

    def erase_world_space(self, world_space_selector=1):
        """
        This method erases the world space
        :param world_space_selector:
        :return:
        """
        if world_space_selector == 1:
            self.world_space = {}
        elif world_space_selector == 2:
            self.world_space_2 = {}

    def end_world_space(self, world_space_selector=1):
        """
        This method sets the world space to end, which is picked up by the rasterizer, which ends its loop
        :param world_space_selector:
        :return:
        """
        if world_space_selector == 1:
            self.world_space = {"end": "ended"}
        elif world_space_selector == 2:
            self.world_space_2 = {"end": "ended"}


class BaseEntity:
    """
    The main class that handles each life forms initialisation, movement, colour, expiry and statistics.
    """

    # dictionary to hold all instances of this class
    lifeforms = {}

    def __init__(self, life_form_id, seed, seed2, seed3, start_x, start_y, max_attrib_expand=0):
        """
        When class initialised it gives the life form its properties from the random numbers inserted into it,
        the life seeds are used to seed random number generators that then are used to generate the life form
        properties, this is so that the same results will come from the same life seeds and that the properties
        generated from them are non-linear i.e. higher life seed does not equal higher life span etc.
        """
        self.life_form_id = life_form_id

        # this list will be used for storing the x, y positions around the life forms location
        self.positions_around_life_form = []

        self.adj_position = None

        # set life form life status
        self.alive = True

        self.wall = False

        self.material = 0
        # todo: add in a 'memory' system where the life form can remember where something good occured ie. breeding
        #  event, mining event etc.
        self.good_memories = {}
        self.bad_memories = {}

        self.waiting_to_spawn = False
        self.waiting_to_build = False

        self.waiting_seed1 = None
        self.waiting_seed2 = None
        self.waiting_seed3 = None
        self.waiting_max_attrib_expand = None

        # set linked status to False; when linked an entity will continue to move in the same direction as the entity
        # it is linked with essentially combining into one bigger entity
        self.linked_up = False
        self.linked_to = 0

        self.previous_direction = None

        self.life_seed1 = seed
        self.life_seed2 = seed2
        self.life_seed3 = seed3

        self.max_attribute = current_session.max_attribute

        # life seed 1 controls the random number generation for the red colour, maximum aggression factor starting
        # direction and maximum possible lifespan
        random.seed(self.life_seed1)
        if not args.fixed_function:
            self.red_color = random.uniform(0, 1)
        else:
            self.red_color = floor(256 * random.random())
        self.aggression_factor = floor(self.max_attribute * random.random())
        self.friend_factor = floor(current_session.max_enemy_factor * random.random())
        self.weight = floor(self.max_attribute * random.random())
        self.preferred_breed_direction = random.choice(current_session.surrounding_point_choices)
        self.momentum = floor(current_session.max_movement * random.random())
        self.rebel = random.choice([True, False])
        self.forgetfulness = floor(128 * random.random())

        # life seed 2 controls the random number generation for the green colour, aggression factor between 0 and the
        # maximum from above as well as the time the entity takes to change direction
        random.seed(self.life_seed2)
        if not args.fixed_function:
            self.green_color = random.uniform(0, 1)
        else:
            self.green_color = floor(256 * random.random())
        if not self.friend_factor == 0:
            self.breed_threshold = floor(self.max_attribute * random.random()) / self.friend_factor
        else:
            self.breed_threshold = floor(self.max_attribute * random.random())
        self.time_to_move = floor(current_session.max_movement * random.random())
        self.time_to_move_count = self.time_to_move
        self.combine_threshold = floor(self.max_attribute * random.random())
        self.bouncy = random.choice([True, False])
        self.builder = random.choice([True, False])
        self.wall_factor = floor(current_session.wall_chance_multiplier * random.random())
        if not self.forgetfulness == 0:
            self.memory_max = floor(self.max_attribute * random.random()) / self.forgetfulness
        else:
            self.memory_max = floor(self.max_attribute * random.random())
        self.memory_max_count = self.memory_max

        # life seed 3 controls the random number generation for the green colour, and time to live between 0 and the
        # maximum from above
        random.seed(self.life_seed3)
        if not args.fixed_function:
            self.blue_color = random.uniform(0, 1)
        else:
            self.blue_color = floor(256 * random.random())
        self.time_to_live = floor(self.max_attribute * random.random())
        self.time_to_live_count = self.time_to_live
        self.strength = floor(self.max_attribute * random.random())
        self.compatibility_factor = floor(self.max_attribute * random.random())
        self.direction = random.choice(current_session.directions)
        self.preferred_direction = self.direction
        if not self.wall_factor == 0:
            self.time_to_build = floor(self.max_attribute * random.random()) / self.wall_factor
        else:
            self.time_to_build = floor(self.max_attribute * random.random())

        # todo: add in wall strength based on entities own strength

        self.time_to_build_count = self.time_to_build

        # reset the global random seed
        random.seed()

        self.mining_strength = percentage(self.strength, 1)

        if self.rebel:
            self.good_memories = {}
            self.bad_memories = {}

        # set the starting location of the life form from the x and y positions
        self.matrix_position_x = start_x
        self.matrix_position_y = start_y

        self.prev_matrix_position = (self.matrix_position_x, self.matrix_position_y)

        self.lifeforms.update({self.life_form_id: self})

        world_space_access.write_to_world_space((self.matrix_position_x, self.matrix_position_y),
                                                (self.red_color, self.green_color, self.blue_color),
                                                self.life_form_id)

    def get_dna(self, dna_key, collided_life_form_id):
        """
        This method is used to get the dna either from the life form that is being collided with or the entity
        itself, it will return the dna 50% of the time from the entity and 50% of the time from the collided entity,
        or depending on the dna chaos chance it will return a random dna value
        :param dna_key:
        :param collided_life_form_id:
        :return:
        """
        dna_chaos = floor(100 * random.random())
        if dna_chaos <= current_session.get_dna_chaos_chance():
            return get_random()
        else:
            if dna_key == 1:
                if random.random() < .5:
                    return self.life_seed1
                else:
                    return BaseEntity.lifeforms[collided_life_form_id].life_seed1
            elif dna_key == 2:
                if random.random() < .5:
                    return self.life_seed2
                else:
                    return BaseEntity.lifeforms[collided_life_form_id].life_seed2
            elif dna_key == 3:
                if random.random() < .5:
                    return self.life_seed3
                else:
                    return BaseEntity.lifeforms[collided_life_form_id].life_seed3

    def add_coord_good_memory(self, x, y):
        if (x, y) in self.good_memories:
            # if self.good_memories[(x, y)] >= 10:
            #     return False
            self.good_memories[(x, y)] += 1
        else:
            self.good_memories[(x, y)] = 1
        return True

    def remove_coord_good_memory(self, x, y):
        if (x, y) in self.good_memories:
            self.good_memories[(x, y)] -= 1
            if self.good_memories[(x, y)] <= 0:
                del self.good_memories[(x, y)]
        return

    def get_count_good_memory(self, x, y):
        if (x, y) in self.good_memories:
            return self.good_memories[(x, y)]
        else:
            return 0

    def get_highest_coord_good_memory(self):
        highest_coord = None
        highest_count = 0
        for coord, count in self.good_memories.items():
            if count > highest_count:
                highest_coord = coord
                highest_count = count
        return highest_coord

    def get_stats(self):
        """
        This method is used to get the stats of the life form
        :return:
        """
        logger.debug(f'ID: {self.life_form_id}')
        logger.debug(f'Seed 1: {self.life_seed1}')
        logger.debug(f'Seed 2: {self.life_seed2}')
        logger.debug(f'Seed 3: {self.life_seed3}')
        logger.debug(f'Preferred Spawn Direction: {self.preferred_breed_direction}')
        logger.debug(f'Preferred Direction: {self.preferred_direction}')
        logger.debug(f'Direction: {self.direction}')
        logger.debug(f'Time to move total: {self.time_to_move}')
        logger.debug(f'Time to next move: {self.time_to_move_count}')
        logger.debug(f'Total lifetime: {self.time_to_live}')
        logger.debug(f'Time left to live: {self.time_to_live_count}')
        logger.debug(f'Aggression Factor: {self.aggression_factor}')
        logger.debug(f'Position X: {self.matrix_position_x}')
        logger.debug(f'Position Y: {self.matrix_position_y}')
        logger.debug(f'Surrounding positions: {self.positions_around_life_form}')
        logger.debug(f'Color: R: {self.red_color} G: {self.green_color} B: {self.blue_color} \n')

    def process(self):
        """
        This method is used to process the life form, it will check if the life form is dead, if it is it will remove
        it, this also handles all movement and breeding as well as gravity and momentum adjustments
        This is all wrapped within a try except block to catch any KeyErrors that may occur if the other life form the
        current one has collided with has been removed
        :return:
        """

        try:
            if self.time_to_live_count > 0:
                self.time_to_live_count -= percentage(current_session.radiation * args.radiation_dmg_multi, 1)
                expired = False
            elif self.time_to_live_count <= 0:
                expired = True

            if self.memory_max_count > 0:
                self.memory_max_count -= 1
            elif self.memory_max_count <= 0:
                self.memory_max_count = self.memory_max
                self.good_memories = {}
                self.bad_memories = {}

            if expired:
                self.entity_remove()
                return

            if not self.waiting_to_build and current_session.building_entities:
                if self.time_to_build_count > 0:
                    self.time_to_build_count -= 1
                elif self.time_to_build_count <= 0:
                    self.time_to_build_count = self.time_to_build
                    self.waiting_to_build = True

            current_session.current_life_form_amount = len(list(BaseEntity.lifeforms.values()))
            # if the current number of active life forms is higher than the previous record of concurrent
            # life forms, update the concurrent life forms variable
            if current_session.current_life_form_amount > current_session.highest_concurrent_lifeforms:
                current_session.highest_concurrent_lifeforms = current_session.current_life_form_amount

            # if entity is dead then skip and return
            if not self.alive:
                return "Dead"

            if self.direction == 'move_right':
                self.adj_position = self.matrix_position_x + 1, self.matrix_position_y
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None
            elif self.direction == 'move_left':
                self.adj_position = self.matrix_position_x - 1, self.matrix_position_y
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None
            elif self.direction == 'move_down':
                self.adj_position = self.matrix_position_x, self.matrix_position_y + 1
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None
            elif self.direction == 'move_up':
                self.adj_position = self.matrix_position_x, self.matrix_position_y - 1
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None
            elif self.direction == 'move_down_and_right':
                self.adj_position = self.matrix_position_x + 1, self.matrix_position_y + 1
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None
            elif self.direction == 'move_up_and_left':
                self.adj_position = self.matrix_position_x - 1, self.matrix_position_y - 1
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None
            elif self.direction == 'move_down_and_left':
                self.adj_position = self.matrix_position_x - 1, self.matrix_position_y + 1
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None
            elif self.direction == 'move_up_and_right':
                self.adj_position = self.matrix_position_x + 1, self.matrix_position_y - 1
                if self.adj_position not in current_session.coord_map:
                    self.adj_position = None

            if not self.direction == 'still':
                if not self.adj_position:
                    collision_detected = True
                    collided_life_form_id = None
                else:

                    try:
                        s_item_life_form_id = \
                            world_space_access.get_from_world_space(self.adj_position)[1]
                        collision_detected = True
                        collided_life_form_id = s_item_life_form_id
                    except TypeError:

                        collision_detected = False
                        collided_life_form_id = None
            else:

                collision_detected = False
                collided_life_form_id = None

            if self.waiting_to_spawn or self.waiting_to_build:
                preferred_direction = random.choice(current_session.surrounding_point_choices)

            # get the count of total life forms currently active
            # if there has been a collision with another entity it will attempt to interact with the other entity
            if collision_detected:
                collision_check = True

                if self.bouncy:
                    momentum_reduction = percentage(10, self.momentum)
                    self.momentum -= momentum_reduction
                else:
                    momentum_reduction = percentage(60, self.momentum)
                    self.momentum -= momentum_reduction

                logger.debug(f'Collision detected: {self.life_form_id} collided with {collided_life_form_id}')

                # store the current direction for later use, like if the life form kills another, it will continue
                # moving in that direction rather than bounce
                self.previous_direction = self.direction

                if not self.direction == self.preferred_direction:
                    self.direction = self.preferred_direction
                else:
                    self.direction = random.choice(current_session.directions)

                if collided_life_form_id:
                    if not BaseEntity.lifeforms[collided_life_form_id].wall:
                        BaseEntity.lifeforms[collided_life_form_id].momentum += momentum_reduction

                        # if the aggression factor is below the entities breed threshold the life form will attempt to
                        # breed with the one it collided with
                        if abs(self.aggression_factor - BaseEntity.lifeforms[collided_life_form_id].aggression_factor) \
                                <= self.breed_threshold:
                            # the other entity also needs to have its aggression factor below its breed threshold

                            if self.compatibility_factor + self.combine_threshold > \
                                    BaseEntity.lifeforms[
                                        collided_life_form_id].compatibility_factor \
                                    > self.compatibility_factor - self.combine_threshold:
                                self.add_coord_good_memory(self.matrix_position_x, self.matrix_position_y)

                                if args.combine_mode:
                                    logger.debug(f'Entity: {self.life_form_id} combined with: {collided_life_form_id}')

                                    self.add_coord_good_memory(self.matrix_position_x, self.matrix_position_y)

                                    BaseEntity.lifeforms[collided_life_form_id].linked_up = True
                                    BaseEntity.lifeforms[collided_life_form_id].linked_to = self.life_form_id

                                    BaseEntity.lifeforms[collided_life_form_id].direction = self.direction

                            if not self.waiting_to_spawn:
                                if random.random() < .5:
                                    attrib_boost = self.max_attribute
                                else:
                                    attrib_boost = BaseEntity.lifeforms[collided_life_form_id].max_attribute

                                preferred_direction = self.preferred_breed_direction
                                self.waiting_seed1 = self.get_dna(1, collided_life_form_id)
                                self.waiting_seed2 = self.get_dna(2, collided_life_form_id)
                                self.waiting_seed3 = self.get_dna(3, collided_life_form_id)
                                self.waiting_max_attrib_expand = attrib_boost
                                self.waiting_to_spawn = True

                        else:
                            if not BaseEntity.lifeforms[collided_life_form_id].aggression_factor < \
                                   BaseEntity.lifeforms[collided_life_form_id].breed_threshold:

                                # if the other entities' aggression factor is lower it will be killed and removed
                                # from the main loops list of entities

                                if BaseEntity.lifeforms[collided_life_form_id].strength < self.strength:
                                    logger.debug('Other entity killed')

                                    self.time_to_live_count += BaseEntity.lifeforms[
                                        collided_life_form_id].time_to_live_count

                                    self.material += BaseEntity.lifeforms[collided_life_form_id].material
                                    self.weight += BaseEntity.lifeforms[collided_life_form_id].material
                                    self.weight += BaseEntity.lifeforms[collided_life_form_id].weight
                                    self.strength += BaseEntity.lifeforms[collided_life_form_id].strength

                                    if self.momentum > BaseEntity.lifeforms[collided_life_form_id].momentum:
                                        collision_check = False

                                    BaseEntity.lifeforms[collided_life_form_id].entity_remove()

                                    self.direction = self.previous_direction

                                # if the other entities' aggression factor is higher it will be killed the current
                                # entity it will be removed from the main loops list of entities
                                elif BaseEntity.lifeforms[collided_life_form_id].strength > self.strength:
                                    logger.debug('Current entity killed')

                                    BaseEntity.lifeforms[
                                        collided_life_form_id].time_to_live_count += self.time_to_live_count
                                    BaseEntity.lifeforms[collided_life_form_id].material += self.material
                                    BaseEntity.lifeforms[collided_life_form_id].weight += self.material
                                    BaseEntity.lifeforms[collided_life_form_id].weight += self.weight
                                    BaseEntity.lifeforms[collided_life_form_id].strength += self.strength

                                    collision_check = "Died"

                                elif BaseEntity.lifeforms[collided_life_form_id].strength == self.strength:
                                    logger.debug('Entities matched, flipping coin')

                                    if random.random() < .5:
                                        logger.debug('Current entity killed')
                                        BaseEntity.lifeforms[
                                            collided_life_form_id].time_to_live_count += self.time_to_live_count
                                        BaseEntity.lifeforms[collided_life_form_id].material += self.material
                                        BaseEntity.lifeforms[collided_life_form_id].weight += self.material
                                        BaseEntity.lifeforms[collided_life_form_id].weight += self.weight
                                        BaseEntity.lifeforms[collided_life_form_id].strength += self.strength

                                        collision_check = "Died"

                                    else:
                                        logger.debug('Other entity killed')
                                        self.time_to_live_count += BaseEntity.lifeforms[
                                            collided_life_form_id].time_to_live_count

                                        self.material += BaseEntity.lifeforms[collided_life_form_id].material
                                        self.weight += BaseEntity.lifeforms[collided_life_form_id].material
                                        self.weight += BaseEntity.lifeforms[collided_life_form_id].weight
                                        self.strength += BaseEntity.lifeforms[collided_life_form_id].strength

                                        if self.momentum > BaseEntity.lifeforms[collided_life_form_id].momentum:
                                            collision_check = False

                                        BaseEntity.lifeforms[collided_life_form_id].entity_remove()

                                        self.direction = self.previous_direction

                            else:
                                logger.debug('Other entity killed')
                                self.time_to_live_count += BaseEntity.lifeforms[
                                    collided_life_form_id].time_to_live_count

                                self.material += BaseEntity.lifeforms[collided_life_form_id].material
                                self.weight += BaseEntity.lifeforms[collided_life_form_id].material
                                self.weight += BaseEntity.lifeforms[collided_life_form_id].weight
                                self.strength += BaseEntity.lifeforms[collided_life_form_id].strength

                                if self.momentum > BaseEntity.lifeforms[collided_life_form_id].momentum:
                                    collision_check = False

                                BaseEntity.lifeforms[collided_life_form_id].entity_remove()

                                self.direction = self.previous_direction

                    # todo: add in extra calculations for taking momentum and weight into account here?
                    elif BaseEntity.lifeforms[collided_life_form_id].wall:
                        if self.strength > BaseEntity.lifeforms[collided_life_form_id].strength \
                                and self.aggression_factor < self.breed_threshold:
                            logger.debug('Entity broke down wall')
                            self.add_coord_good_memory(self.matrix_position_x, self.matrix_position_y)
                            if BaseEntity.lifeforms[collided_life_form_id].material > 10 \
                                    and BaseEntity.lifeforms[collided_life_form_id].material >= self.mining_strength:
                                BaseEntity.lifeforms[collided_life_form_id].material -= self.mining_strength
                                BaseEntity.lifeforms[collided_life_form_id].weight -= self.mining_strength
                                self.material += self.mining_strength
                                self.weight += self.mining_strength
                                collision_check = True
                            else:
                                self.material += BaseEntity.lifeforms[collided_life_form_id].material
                                self.weight += BaseEntity.lifeforms[collided_life_form_id].material
                                if self.momentum > BaseEntity.lifeforms[collided_life_form_id].momentum:
                                    collision_check = False
                                BaseEntity.lifeforms[collided_life_form_id].entity_remove()
                        else:
                            logger.debug('Entity hit wall')
                            collision_check = True
            else:
                collision_check = False

            if collision_check == "Died":
                return collision_check
            elif not collision_check:
                world_space_access.del_world_space_item(
                    (self.matrix_position_x, self.matrix_position_y))

                if self.direction == 'move_up':
                    self.matrix_position_y -= 1
                    self.momentum -= 2

                if self.direction == 'move_down':
                    self.matrix_position_y += 1
                    if current_session.gravity_on:
                        self.momentum += 1
                    else:
                        self.momentum -= 2

                if self.direction == 'move_left':
                    self.matrix_position_x -= 1
                    self.momentum -= 2

                if self.direction == 'move_right':
                    self.matrix_position_x += 1
                    self.momentum -= 2

                if self.direction == 'move_up_and_right':
                    self.matrix_position_y -= 1
                    self.matrix_position_x += 1
                    self.momentum -= 2

                if self.direction == 'move_up_and_left':
                    self.matrix_position_y -= 1
                    self.matrix_position_x -= 1
                    self.momentum -= 2

                if self.direction == 'move_down_and_right':
                    self.matrix_position_y += 1
                    self.matrix_position_x += 1
                    if current_session.gravity_on:
                        self.momentum += 1
                    else:
                        self.momentum -= 2

                if self.direction == 'move_down_and_left':
                    self.matrix_position_y += 1
                    self.matrix_position_x -= 1
                    if current_session.gravity_on:
                        self.momentum += 1
                    else:
                        self.momentum -= 2

                if self.direction == 'still':
                    pass

                if self.momentum <= 0:
                    self.momentum = 0
                elif self.momentum >= 100:
                    self.momentum = 100

                # write new position in the buffer
                world_space_access.write_to_world_space(
                    (self.matrix_position_x, self.matrix_position_y),
                    (self.red_color, self.green_color,
                     self.blue_color), self.life_form_id)

            # the breeding will attempt only if the current life form count is not above the
            # population limit
            if self.waiting_to_spawn or self.waiting_to_build:
                if current_session.current_life_form_amount < args.pop_limit:
                    # find a place for the new entity to spawn around the current parent life form

                    if preferred_direction == 'get_position_right':
                        self.adj_position = self.matrix_position_x + 1, self.matrix_position_y
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None
                    elif preferred_direction == 'get_position_left':
                        self.adj_position = self.matrix_position_x - 1, self.matrix_position_y
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None
                    elif preferred_direction == 'get_position_down':
                        self.adj_position = self.matrix_position_x, self.matrix_position_y + 1
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None
                    elif preferred_direction == 'get_position_up':
                        self.adj_position = self.matrix_position_x, self.matrix_position_y - 1
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None
                    elif preferred_direction == 'get_position_down_and_right':
                        self.adj_position = self.matrix_position_x + 1, self.matrix_position_y + 1
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None
                    elif preferred_direction == 'get_position_up_and_left':
                        self.adj_position = self.matrix_position_x - 1, self.matrix_position_y - 1
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None
                    elif preferred_direction == 'get_position_down_and_left':
                        self.adj_position = self.matrix_position_x - 1, self.matrix_position_y + 1
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None
                    elif preferred_direction == 'get_position_up_and_right':
                        self.adj_position = self.matrix_position_x + 1, self.matrix_position_y - 1
                        if self.adj_position not in current_session.coord_map:
                            self.adj_position = None

                    if self.adj_position:
                        try:
                            world_space_access.get_from_world_space(self.adj_position)[1]
                        except TypeError:
                            post_x_gen, post_y_gen = self.adj_position

                        else:

                            post_x_gen, post_y_gen = None, None
                            self.waiting_to_spawn = True
                    else:
                        post_x_gen, post_y_gen = None, None
                        self.waiting_to_spawn = True

                    if not self.waiting_to_spawn and self.waiting_to_build:
                        if post_x_gen is not None and post_y_gen is not None and self.material >= 10:
                            Wall(
                                life_form_id=current_session.life_form_total_count,
                                seed=self.waiting_seed1,
                                seed2=self.waiting_seed2,
                                seed3=self.waiting_seed3,
                                start_x=post_x_gen,
                                start_y=post_y_gen,
                                max_attrib_expand=self.waiting_max_attrib_expand)

                            # increase the life form total by 1
                            current_session.life_form_total_count += 1

                            self.material -= 10
                            self.weight -= 10

                            logger.debug(f"Generated X, Y positions for new life form: {post_x_gen}, {post_y_gen}")

                            self.waiting_to_build = False

                    elif self.waiting_to_spawn:
                        if self.wall:
                            raise Exception("Wall life form is trying to spawn a life form")
                        if post_x_gen is not None and post_y_gen is not None:
                            LifeForm(
                                life_form_id=current_session.life_form_total_count,
                                seed=self.waiting_seed1,
                                seed2=self.waiting_seed2,
                                seed3=self.waiting_seed3,
                                start_x=post_x_gen,
                                start_y=post_y_gen,
                                max_attrib_expand=self.waiting_max_attrib_expand)

                            BaseEntity.lifeforms[
                                current_session.life_form_total_count].good_memories = self.good_memories
                            BaseEntity.lifeforms[
                                current_session.life_form_total_count].bad_memories = self.bad_memories

                            # increase the life form total by 1
                            current_session.life_form_total_count += 1

                            logger.debug(f"Generated X, Y positions for new life form: {post_x_gen}, {post_y_gen}")

                            self.waiting_to_spawn = False

                # if the current amount of life forms on the board is at the population limit or above
                # then do nothing
                elif current_session.current_life_form_amount >= args.pop_limit:
                    logger.debug(f"Max life form limit: {args.pop_limit} reached")
                    self.waiting_to_spawn = True
                    self.waiting_to_build = True

            if not collision_check:

                # minus 1 from the time to move count until it hits 0, at which point the entity will change
                # direction from the "randomise direction" function being called
                if not self.linked_up:
                    self.best_coord_memory = self.get_highest_coord_good_memory()

                    if self.best_coord_memory:
                        if self.matrix_position_x < self.best_coord_memory[0] and self.matrix_position_y > \
                                self.best_coord_memory[1]:
                            self.direction = 'move_up_and_right'
                        elif self.matrix_position_x < self.best_coord_memory[0] and self.matrix_position_y < \
                                self.best_coord_memory[1]:
                            self.direction = 'move_down_and_right'
                        elif self.matrix_position_x > self.best_coord_memory[0] and self.matrix_position_y > \
                                self.best_coord_memory[1]:
                            self.direction = 'move_up_and_left'
                        elif self.matrix_position_x > self.best_coord_memory[0] and self.matrix_position_y < \
                                self.best_coord_memory[1]:
                            self.direction = 'move_down_and_left'
                        elif self.matrix_position_x < self.best_coord_memory[0]:
                            self.direction = 'move_right'
                        elif self.matrix_position_x > self.best_coord_memory[0]:
                            self.direction = 'move_left'
                        elif self.matrix_position_y > self.best_coord_memory[1]:
                            self.direction = 'move_up'
                        elif self.matrix_position_y < self.best_coord_memory[1]:
                            self.direction = 'move_down'
                        else:
                            self.remove_coord_good_memory(self.matrix_position_x, self.matrix_position_y)
                            self.direction = self.preferred_direction
                    else:
                        if self.time_to_move_count > 0:
                            self.time_to_move_count -= 1
                        elif self.time_to_move_count <= 0:
                            self.time_to_move_count = self.time_to_move
                            if not self.direction == self.preferred_direction:
                                self.direction = self.preferred_direction
                            else:
                                self.direction = random.choice(current_session.directions)
                else:
                    # if combining is enabled set to the direction of the linked entity, however the other entity may
                    # have expired and weird things happen, and it may not be accessible from within the class holder
                    # so just randomise direction and de-link
                    try:
                        self.direction = BaseEntity.lifeforms[self.linked_to].direction
                    except KeyError:
                        self.linked_up = False
                        if not self.direction == self.preferred_direction:
                            self.direction = self.preferred_direction
                        else:
                            self.direction = random.choice(current_session.directions)

            if self.strength < self.weight:
                self.direction = 'still'

            if current_session.gravity_on and (self.strength < self.weight or self.direction == 'still'
                                               or self.momentum <= 0):
                self.direction = 'move_down'
                logger.debug(f"Moved from gravity")

        except KeyError:
            logger.debug(f"Missing entity: {self.life_form_id}")
            try:
                BaseEntity.lifeforms[collided_life_form_id].entity_remove()
            except KeyError:
                pass
            except UnboundLocalError:
                pass
            return

    def entity_remove(self):
        """
        Removes an entity from the board.
        :return:
        """
        world_space_access.del_world_space_item((self.matrix_position_x, self.matrix_position_y))
        self.alive = False
        current_session.last_removal = self.life_form_id
        del BaseEntity.lifeforms[self.life_form_id]
        logger.debug(f"Entity {self.life_form_id} removed")

    def fade_entity(self):
        """
        Fades an entity from the board using shaders from Pixel Composer.
        :return:
        """
        world_space_access.write_to_world_space(
            (self.matrix_position_x, self.matrix_position_y),
            (self.red_color, self.green_color,
             self.blue_color), self.life_form_id, 2)
        self.entity_remove()


class Wall(BaseEntity):
    def __init__(self, life_form_id, seed, seed2, seed3, start_x, start_y, max_attrib_expand=0):
        super().__init__(life_form_id, seed, seed2, seed3, start_x, start_y, max_attrib_expand)

        # todo: it seems this is calling the superclass in a way that allows for lifeforms to be spawned when a wall
        #  is meant ot be spawned, need to figure out the mechanics of this (more of a feature than a bug)

        self.wall_color_int = 127
        self.wall_color_float = 0.5

        self.wall = True

        self.material = 10

        if not args.fixed_function:
            self.red_color = self.wall_color_float
        else:
            self.red_color = self.wall_color_int

        if not args.fixed_function:
            self.green_color = self.wall_color_float
        else:
            self.green_color = self.wall_color_int

        if not args.fixed_function:
            self.blue_color = self.wall_color_float
        else:
            self.blue_color = self.wall_color_int

        # write new position in the buffer
        world_space_access.write_to_world_space(
            (self.matrix_position_x, self.matrix_position_y),
            (self.red_color, self.green_color,
             self.blue_color), self.life_form_id)

    def process(self):
        # todo: add in the possibility for radiation to cause a wall to turn into a life form
        pass


class Resource(BaseEntity):
    def __init__(self, life_form_id, seed, seed2, seed3, start_x, start_y, max_attrib_expand=0):
        super().__init__(life_form_id, seed, seed2, seed3, start_x, start_y, max_attrib_expand)

        self.wall = True

        self.material = floor(self.max_attribute * random.random())

        if not args.fixed_function:
            self.red_color = 0.95
        else:
            self.red_color = 243

        if not args.fixed_function:
            self.green_color = 0.0
        else:
            self.green_color = 0

        if not args.fixed_function:
            self.blue_color = 0.0
        else:
            self.blue_color = 0

        # write new position in the buffer
        world_space_access.write_to_world_space(
            (self.matrix_position_x, self.matrix_position_y),
            (self.red_color, self.green_color,
             self.blue_color), self.life_form_id)

        world_space_access.write_to_world_space(
            (self.matrix_position_x + 1, self.matrix_position_y),
            (self.red_color, self.green_color,
             self.blue_color), self.life_form_id)

        world_space_access.write_to_world_space(
            (self.matrix_position_x, self.matrix_position_y + 1),
            (self.red_color, self.green_color,
             self.blue_color), self.life_form_id)

        world_space_access.write_to_world_space(
            (self.matrix_position_x + 1, self.matrix_position_y + 1),
            (self.red_color, self.green_color,
             self.blue_color), self.life_form_id)

    def process(self):
        # todo: add in the possibility for radiation to cause a wall to turn into a life form
        pass


class LifeForm(BaseEntity):
    def __init__(self, life_form_id, seed, seed2, seed3, start_x, start_y, max_attrib_expand=0):
        super().__init__(life_form_id, seed, seed2, seed3, start_x, start_y, max_attrib_expand)


class DrawObjects(ScreenDrawer):

    def __init__(self, output_controller, buffer_refresh, session_info, world_space, exit_text):
        super().__init__(output_controller=output_controller,
                         buffer_refresh=buffer_refresh,
                         session_info=session_info,
                         world_space=world_space,
                         exit_text=exit_text)

        self.frame_buffer_access = FrameBufferInit(self.session_info)

        self.render_stack = [
            'background_shader_pass',
            'object_colour_pass',
            'removed_object_colour_pass',
            'fade_entity_pass',
            'tone_map_pass',
            'render_frame_buffer',
            'float_to_rgb_pass',
            'buffer_scan',
            'flush_buffer'
        ]

        # cool effect, ensure a background shader is active and configured
        # self.render_stack = [
        #     'background_shader_pass',
        #     'lighting_pass',
        #     'lensing_pass',
        #     'object_colour_pass',
        #     'removed_object_colour_pass',
        #     'fade_entity_pass',
        #     'log_current_frame',
        #     'tone_map_pass',
        #     'render_frame_buffer',
        #     'float_to_rgb_pass',
        #     'buffer_scan',
        #     'flush_buffer'
        # ]

        # with lens flares and lighting
        # self.render_stack = [
        #     'background_shader_pass',
        #     'object_colour_pass',
        #     'removed_object_colour_pass',
        #     'fade_entity_pass',
        #     'log_current_frame',
        #     'lighting_pass',
        #     'tone_map_pass',
        #     'render_frame_buffer',
        #     'float_to_rgb_pass',
        #     'sprite_pass',
        #     'write_texture',
        #     'buffer_scan',
        #     'flush_buffer'
        # ]

        self.draw()

    def fade_entity_pass(self):
        """
        Uses the motion blur shader to fade entities from the board.
        :return:
        """
        # todo: convert this to list comprehension? and tidy it up
        for coord, pixel in self.frame_buffer_access.removed_entity_buffer.items():
            new_pixel = self.frame_buffer_access.motion_blur.run_shader(pixel)
            if new_pixel:
                self.frame_buffer_access.write_to_render_plane(coord, new_pixel)
                self.frame_buffer_access.write_to_removed_entity_buffer(coord, new_pixel)

    def removed_object_colour_pass(self):
        """
        Adds the removed entity buffer to the render plane.
        :return:
        """
        [self.frame_buffer_access.write_to_removed_entity_buffer(coord, pixel) for coord, pixel in
         self.world_space_access.return_world_space(2).items()]


class FrameBufferInit(FrameBuffer):

    def __init__(self, session_info):
        super().__init__(session_info=session_info)

        self.blank_pixel = (0.0, 0.0, 0.0)

        self.removed_entity_buffer = {}

        # WARNING: be careful with these, it can cause flashing images
        # self.shader_stack.multi_shader_creator(input_shader=FullScreenPatternShader, number_of_shaders=4, base_number=3,
        #                                        base_addition=16, base_rgb=(1.25, 0.0, 0.0))
        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=445, shader_colour=(0.0, 1.25, 0.0)))
        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=31, shader_colour=(0.0, 0.0, 1.25)))

        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=7, shader_colour=(0.7, 0.05, 0.001)))

        self.motion_blur.shader_colour = (0.0, 0.0, 0.0)
        self.motion_blur.static_shader_alpha = 0.9
        self.motion_blur.float_clip_min = 0.001

        self.lighting.shader_colour = (10.0, 10.0, 10.0)
        self.lighting.light_strength = 10.0
        self.lighting.moving_light = False
        self.lighting.light_position = (32, 32)

    def write_to_removed_entity_buffer(self, pixel_coord, pixel_rgb):
        """
        Writes to the removed entity buffer.
        :param pixel_coord:
        :param pixel_rgb:
        :return:
        """
        self.removed_entity_buffer[pixel_coord] = pixel_rgb


def on_press(key):
    """
    Listens for key presses and calls the appropriate function.
    :param key:
    :return:
    """
    if key == KeyCode(char='T'):
        thanos_snap()
    if key == KeyCode(char='G'):
        gravity_switch()
    if key == KeyCode(char='F'):
        render_switch()
    if key == KeyCode(char='R'):
        increase_max_radiation()
    if key == KeyCode(char='r'):
        decrease_max_radiation()
    if key == KeyCode(char='S'):
        show_current_session_stats()
    # if key == KeyCode(char='Q'):
    #     save_space_time()
    # if key == KeyCode(char='A'):
    #     load_space_time()


def global_board_generator():
    """
    Generates a global board for the life forms to live on, ensuring that no life form is spawned on top of another.
    :return:
    """
    try:
        random_free_coord = current_session.free_board_positions.popleft()

    except IndexError:
        # if no free space is found return None
        return None

    logger.debug(f"Free space around the entity found: {random_free_coord}")
    # if no other entity is in this location return the co-ords
    return random_free_coord[0], random_free_coord[1]


def percentage(percent, whole):
    """
    Calculate a percentage of a whole number.
    :param percent:
    :param whole:
    :return:
    """
    return int(round(percent * whole) / 100.0)


def get_random():
    """
    Get a pseudo random number.
    :return:
    """
    # todo: add in some sort of fibonacci sequence stuff in here?
    return random.getrandbits(500)


def thanos_snap():
    """
    Remove half of the life forms from the board
    :return:
    """
    life_form_instances = [i for i in BaseEntity.lifeforms.values() if isinstance(i, LifeForm)]

    for x in range(int(len(life_form_instances) / 2)):
        vanished = random.choice(life_form_instances)
        try:
            LifeForm.lifeforms[vanished.life_form_id].fade_entity()
        except KeyError:
            pass
    logger.info("Perfectly balanced as all things should be")


def gravity_switch():
    """
    Switch the gravity on and off
    :return:
    """
    current_session.gravity_on = not current_session.gravity_on
    logger.info(f"Gravity is now {current_session.gravity_on}")


def render_switch():
    """
    Switch the rendering on and off
    :return:
    """
    current_session.rendering_on = not current_session.rendering_on
    logger.info(f"Rendering is now {current_session.rendering_on}")


def increase_max_radiation():
    """
    Increase the radiation level by 100, if radiation change is on then increase the max radiation level
    :return:
    """
    if current_session.radiation_change:
        current_session.radiation_max += 100
        logger.info(f"Max radiation level increased to {current_session.radiation_max}")
    else:
        current_session.radiation += 100
        logger.info(f"Radiation level increased to {current_session.radiation}")


def decrease_max_radiation():
    """
    Decrease the radiation level by 100, if radiation change is on then decrease the max radiation level
    :return:
    """
    if current_session.radiation_change:
        current_session.radiation_max -= 100
        logger.info(f"Max radiation level decreased to {current_session.radiation_max}")
    else:
        current_session.radiation -= 100
        logger.info(f"Radiation level decreased to {current_session.radiation}")


def show_current_session_stats():
    """
    Show the current stats of the session
    :return:
    """
    logging.info("Current session stats:")
    logging.info(f"Current session start time: {current_session.current_session_start_time}")
    logging.info(f"Highest concurrent lifeforms: {current_session.highest_concurrent_lifeforms}")
    logging.info(f"Built entities: {current_session.building_entities}")
    logging.info(f"Max friend factor: {current_session.max_enemy_factor}")
    logging.info(f"Wall chance multiplier: {current_session.wall_chance_multiplier}")
    logging.info(f"Drawing trails: {current_session.draw_trails}")
    logging.info(f"Retries enabled: {current_session.retries}")
    logging.info(f"Radiation change enabled: {current_session.radiation_change}")
    logging.info(f"Current Radiation: {current_session.radiation}")
    logging.info(f"Radiation curve: {current_session.radiation_curve}")
    logging.info(f"Radiation base change chance: {current_session.radiation_base_change_chance}")
    logging.info(f"DNA chaos chance: {current_session.dna_chaos_chance}")
    logging.info(f"Max attribute: {current_session.max_attribute}")
    logging.info(f"Max radiation: {current_session.radiation_max}")
    logging.info(f"Gravity enabled: {current_session.gravity_on}")
    logging.info(f"Rendering enabled: {current_session.rendering_on}")
    logging.info(f"Max movement: {current_session.max_movement}")
    logging.info(f"Last removal: {current_session.last_removal}")
    logging.info(f"Current life form amount: {current_session.current_life_form_amount}")
    logging.info(f"Life form total count: {current_session.life_form_total_count}")
    logging.info(f"Process loop on: {current_session.process_loop_on}\n")


def save_space_time():
    world_space_access.world_space_time['save'] = current_session, BaseEntity.lifeforms.copy()
    logger.info("Saved space time")


def load_space_time():
    # todo: WIP, needs fixing and finishing
    # world_space_access.world_space_time[
    #     world_space_access.world_time] = LifeForm.lifeforms.copy().values(), current_session

    # current_session = world_space_access.world_space_time['save'][0]
    # LifeForm.lifeforms = world_space_access.world_space_time['save'][1]
    # print(current_session)
    # print(world_space_access.world_space_time['save'][0])

    # print(world_space_access.world_space_time['save'][0])

    # current_session = world_space_access.world_space_time['save'][0]
    # world_space_access.erase_world_space()

    current_session.process_loop_on = False

    current_session.highest_concurrent_lifeforms = world_space_access.world_space_time['save'][
        0].highest_concurrent_lifeforms
    current_session.max_enemy_factor = world_space_access.world_space_time['save'][0].max_enemy_factor
    current_session.draw_trails = world_space_access.world_space_time['save'][0].draw_trails
    current_session.radiation_change = world_space_access.world_space_time['save'][0].radiation_change
    current_session.radiation = world_space_access.world_space_time['save'][0].radiation
    current_session.radiation_base_change_chance = world_space_access.world_space_time['save'][
        0].radiation_base_change_chance
    current_session.dna_chaos_chance = world_space_access.world_space_time['save'][0].dna_chaos_chance
    current_session.max_attribute = world_space_access.world_space_time['save'][0].max_attribute
    current_session.radiation_max = world_space_access.world_space_time['save'][0].radiation_max
    current_session.gravity_on = world_space_access.world_space_time['save'][0].gravity_on
    current_session.rendering_on = world_space_access.world_space_time['save'][0].rendering_on
    current_session.last_removal = world_space_access.world_space_time['save'][0].last_removal
    current_session.current_life_form_amount = world_space_access.world_space_time['save'][0].current_life_form_amount
    current_session.life_form_total_count = world_space_access.world_space_time['save'][0].life_form_total_count

    print(len(BaseEntity.lifeforms))
    print(len(world_space_access.world_space_time['save'][1]))
    BaseEntity.lifeforms = {}
    world_space_access.erase_world_space()
    print(len(BaseEntity.lifeforms))
    BaseEntity.lifeforms = world_space_access.world_space_time['save'][1]
    logger.info("Loaded space time")
    print(len(BaseEntity.lifeforms))

    current_session.process_loop_on = True


def class_generator(life_form_id, entity="lifeform"):
    """
    Generates a life form class based on the life form id.
    :param entity:
    :param wall:
    :param life_form_id:
    :return:
    """
    try:
        starting_x, starting_y = global_board_generator()
    except TypeError:
        return

    if entity == "wall":
        Wall(life_form_id=current_session.life_form_total_count, seed=get_random(), seed2=get_random(),
             seed3=get_random(),
             start_x=starting_x, start_y=starting_y)
        current_session.life_form_total_count += 1
    elif entity == "lifeform":
        LifeForm(life_form_id=current_session.life_form_total_count, seed=get_random(), seed2=get_random(),
                 seed3=get_random(),
                 start_x=starting_x, start_y=starting_y)
        current_session.life_form_total_count += 1
    elif entity == "resource":
        Resource(life_form_id=current_session.life_form_total_count, seed=get_random(), seed2=get_random(),
                 seed3=get_random(),
                 start_x=starting_x, start_y=starting_y)
        current_session.life_form_total_count += 1


def main():
    """
    Main function, sets up the board and starts the main loop. Then processes all entities, if retries are enabled
    then when all entities are gone it will respawn them and start again.
    :return:
    """
    frame_refresh_delay_ms = 1 / hat_buffer_refresh_rate
    """
    Main loop where all life form movement and interaction takes place
    """
    # wrap main loop into a try/catch to allow keyboard exit and cleanup
    current_session.max_movement = diagonal_distance(0, 0, screen_controller.u_width, screen_controller.u_height)
    next_frame = time() + frame_refresh_delay_ms
    while True:
        # while current_session.process_loop_on:
        # if time() > next_frame or not refresh_logic_link and current_session.world_space_access.buffer_ready:
        # for now this just checks whether the next frame time is ready or whether refresh logic is disabled
        # this allows the internal logic to operate faster than the refresh rate of the display, so it will run faster
        # but the display will always be behind resulting in entities looking like they are teleporting around
        life_form_container = BaseEntity.lifeforms.copy().values()
        if time() > next_frame or not args.logic_sync:
            # check the list of entities has items within
            if life_form_container:
                [life_form.process() for life_form in life_form_container]

            # if the main list of entities is empty then all have expired; the program displays final information
            # about the programs run and exits; unless retry mode is active, then a new set of entities are created
            # and the simulation starts fresh with the same initial configuration

            elif not life_form_container:
                if current_session.retries:
                    current_session.rendering_on = False

                    current_session.highest_concurrent_lifeforms = 0
                    current_session.life_form_total_count = 0
                    current_session.last_removal = -1
                    current_session.get_coord_map()
                    current_session.current_session_start_time = datetime.datetime.now()
                    [class_generator(i, "wall") for i in range(args.wall_number)]
                    [class_generator(i) for i in range(args.life_form_total)]

                    current_session.rendering_on = True

                    continue
                else:
                    logger.info(
                        f'\n All Lifeforms have expired.\n Total life forms produced: '
                        f'{current_session.life_form_total_count}\n '
                        f'Max concurrent Lifeforms was: {current_session.highest_concurrent_lifeforms}\n')
                    world_space_access.end_world_space()
                    quit()

            logger.debug(f"Lifeforms: {current_session.life_form_total_count}")

            if args.radiation_change:
                current_session.adjust_radiation_along_curve()

            world_space_access.world_time += 1

            next_frame = time() + frame_refresh_delay_ms


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Artificial Life')

    parser.add_argument('-m', '--max-num', action="store", type=int, dest="max_num", default=max_trait_number,
                        help='Maximum number possible for any entity traits')

    parser.add_argument('-ilc', '--initial-lifeforms-count', action="store", dest="life_form_total", type=int,
                        default=initial_lifeforms_count,
                        help='Number of lifeforms to start with')
    # todo: add sync
    parser.add_argument('-s', '--refresh-rate', action="store", dest="loop_speed", type=float,
                        default=hat_buffer_refresh_rate,
                        help='The refresh rate for the buffer processing, also sets a maximum speed for the main loop '
                             'processing, if sync is enabled (this is to prevent the display falling behind the logic '
                             'loop)')

    parser.add_argument('-p', '--population-limit', action="store", dest="pop_limit", type=int,
                        default=population_limit,
                        help='Limit of the population at any one time')

    parser.add_argument('-me', '--max-enemy-factor', action="store", dest="max_enemy_factor", type=int,
                        default=max_enemy_factor,
                        help='Factor that calculates into the maximum breed threshold of an entity')

    parser.add_argument('-dc', '--dna-chaos', action="store", dest="dna_chaos_chance", type=int,
                        default=initial_dna_chaos_chance,
                        help='Percentage chance of random DNA upon breeding of entities')

    parser.add_argument('-shs', '--simulator-hat-size', action="store", dest="custom_size_simulator", nargs='+',
                        type=int,
                        default=hat_simulator_or_panel_size,
                        help="Size of the simulator HAT in pixels; to use pass in '-shs 16 16' for 16x16 pixels (x "
                             "and y)")

    parser.add_argument('-c', '--combine-mode', action="store_true", dest="combine_mode", default=combine_mode,
                        help='Enables life forms to combine into bigger ones')

    # parser.add_argument('-mc', '--minecraft-mode', action="store_true", dest="mc_mode",
    #                     help='Enables Minecraft mode')

    parser.add_argument('-tr', '--trails', action="store_true", dest="trails_on", default=trails_on,
                        help='Stops the HAT from being cleared, resulting in trails of entities')

    parser.add_argument('-g', '--gravity', action="store_true", dest="gravity", default=gravity_on,
                        help='Gravity enabled, still entities will fall to the floor')

    parser.add_argument('-rc', '--radiation-change', action="store_true", dest="radiation_change",
                        default=radiation_change,
                        help='Whether to adjust radiation levels across the simulation or not')

    parser.add_argument('-w', '--walls', action="store", dest="wall_number", type=int,
                        default=walls,
                        help='Number of walls to randomly spawn that will block entities')

    parser.add_argument('-rs', '--resources', action="store", dest="resources_number", type=int,
                        default=resources,
                        help='Number of resources to begin with that entities can mine')

    parser.add_argument('-r', '--radiation', action="store", dest="radiation", type=int, default=initial_radiation,
                        help='Radiation enabled, will increase random mutation chance and damage entities')

    parser.add_argument('-mr', '--max-radiation', action="store", dest="max_radiation", type=int, default=max_radiation,
                        help='Maximum radiation level possible')

    parser.add_argument('-rm', '--radiation-multi', action="store", dest="radiation_dmg_multi", type=int,
                        default=radiation_dmg_multiplier,
                        help='Maximum radiation level possible')

    parser.add_argument('-rbc', '--radiation-base-change', action="store", dest="radiation_base_change_chance",
                        type=float,
                        default=change_of_base_radiation_chance,
                        help='The percentage chance that the base radiation level will change randomly.')

    parser.add_argument('-be', '--building-entities', action="store_true", dest="building_entities",
                        default=entities_build_walls,
                        help='Whether lifeforms can build static blocks on the board')

    parser.add_argument('-wc', '--wall-chance', action="store", dest="wall_chance_multiplier", type=int,
                        default=wall_chance_multiplier,
                        help='Whether lifeforms can build static blocks on the board')

    parser.add_argument('-rt', '--retry', action="store_true", dest="retry_on", default=retries_on,
                        help='Whether the loop will automatically restart upon the expiry of all entities')

    parser.add_argument('-sim', '--unicorn-hat-sim', action="store_true", dest="simulator", default=unicorn_simulator,
                        help='Whether to use the Unicorn HAT simulator or not')

    parser.add_argument('-hm', '--hat-model', action="store", dest="hat_edition", type=str, default=hat_model,
                        choices=['SD', 'HD', 'MINI', 'PANEL', 'CUSTOM'],
                        help='What type of HAT the program is using. CUSTOM '
                             'only works with Unicorn HAT Simulator')

    parser.add_argument('-l', '--log-level', action="store", dest="log_level", type=str, default=logging_level,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], help='Logging level')

    parser.add_argument('-sl', '--sync-logic', action="store_true", dest="logic_sync", default=refresh_logic_link,
                        help='Whether to sync the logic loop to the refresh rate of the screen')

    parser.add_argument('-ff', '--fixed-function', action="store_true", dest="fixed_function", default=fixed_function,
                        help='Whether to bypass pixel composer and use fixed function '
                             'for drawing (faster, less pretty)')

    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    world_space_access = WorldSpaceControl()

    screen_controller = ScreenController(screen_type=args.hat_edition,
                                         simulator=args.simulator,
                                         custom_size_simulator=args.custom_size_simulator,
                                         led_brightness=led_brightness)

    current_session = Session(life_form_total_count=args.life_form_total,
                              building_entities=args.building_entities,
                              max_enemy_factor=args.max_enemy_factor,
                              wall_chance_multiplier=args.wall_chance_multiplier,
                              draw_trails=args.trails_on,
                              retries=args.retry_on,
                              highest_concurrent_lifeforms=args.life_form_total,
                              radiation=args.radiation,
                              radiation_max=args.max_radiation,
                              dna_chaos_chance=args.dna_chaos_chance,
                              radiation_change=args.radiation_change,
                              radiation_base_change_chance=args.radiation_base_change_chance,
                              max_attribute=args.max_num,
                              gravity_on=args.gravity,
                              current_session_start_time=datetime.datetime.now())

    [class_generator(i, "resource") for i in range(args.resources_number)]
    [class_generator(i, "wall") for i in range(args.wall_number)]
    [class_generator(i) for i in range(args.life_form_total)]

    current_session.rendering_on = True

    listener = Listener(on_press=on_press, daemon=True)
    listener.start()

    Thread(target=main, daemon=True).start()

    if not args.fixed_function:
        draw_control = DrawObjects(output_controller=screen_controller,
                                   buffer_refresh=hat_buffer_refresh_rate,
                                   session_info=current_session,
                                   world_space=world_space_access,
                                   exit_text='Program ended by user.\n Total life forms produced: ${'
                                             'life_form_total_count}\n Max'
                                             'concurrent Lifeforms was: ${highest_concurrent_lifeforms}\n Last count '
                                             'of active'
                                             'Lifeforms: ${current_life_form_amount}')
    else:
        while True:
            [screen_controller.draw_pixels(coord, (0, 0, 0)) for coord in
             current_session.coord_map]
            [screen_controller.draw_pixels(coord, pixel[0]) for coord, pixel in
             world_space_access.world_space.copy().items()]
            screen_controller.show()
