import argparse
import itertools
import logging
import os
import random
from math import floor
from math import sqrt
import sys
from dataclasses import dataclass
from time import time

from screen_output import ScreenController

from collections import deque

# from mcpi.minecraft import Minecraft

renderer_dir = os.path.join(os.path.dirname(__file__), 'pixel_composer')

sys.path.append(renderer_dir)

from pixel_composer.rasterizer import ScreenDrawer, FrameBuffer

from threading import Thread

from config.parameters import initial_lifeforms_count, population_limit, logging_level, initial_dna_chaos_chance, \
    led_brightness, hat_model, hat_simulator_or_panel_size, hat_buffer_refresh_rate, refresh_logic_link, \
    max_trait_number, \
    initial_radiation, max_radiation, change_of_base_radiation_chance, radiation_dmg_multiplier, max_enemy_factor

logger = logging.getLogger("alife-logger")


def diagonal_distance(x1, y1, x2, y2):
    x_distance = x2 - x1
    y_distance = y2 - y1
    return sqrt(x_distance ** 2 + y_distance ** 2)


@dataclass
class Session:
    """
    Class for storing current session information to make it easily accessible from within the LifeForm class and the
    main logic loop
    """
    highest_concurrent_lifeforms: int
    max_enemy_factor: int
    draw_trails: bool
    retries: bool
    radiation_change: bool
    radiation: int
    radiation_curve = [(0, 0.5), (1, 2), (2, 1), (3, 1.5)]
    radiation_base_change_chance: float
    dna_chaos_chance: int
    max_attribute: int
    radiation_max: int
    max_movement: int = 0
    coord_map: tuple = ()
    last_removal: int = -1
    current_layer: int = 0
    current_life_form_amount: int = 0
    life_form_total_count: int = 0

    directions = ('move_up', 'move_down', 'move_left', 'move_right', 'move_up_and_right',
                  'move_down_and_left', 'move_up_and_left', 'move_down_and_right', 'still')

    surrounding_point_choices = ('get_position_up', 'get_position_down', 'get_position_left',
                                 'get_position_right', 'get_position_up_and_right',
                                 'get_position_up_and_left', 'get_position_down_and_left',
                                 'get_position_down_and_right')

    def __post_init__(self):
        self.coord_map = tuple(
            (x, y) for x in range(ScreenController.u_width) for y in range(ScreenController.u_height))

        self.get_coord_map()

        self.free_board_positions.extend(self.shuffled_coord_map)

        self.base_radiation = self.radiation

    def get_coord_map(self):
        self.shuffled_coord_map = list(self.coord_map)

        random.shuffle(self.shuffled_coord_map)

        self.free_board_positions = deque()

        self.free_board_positions.extend(self.shuffled_coord_map)

    def get_dna_chaos_chance(self):
        return self.dna_chaos_chance + percentage(self.radiation, self.dna_chaos_chance)

    def adjust_radiation_along_curve(self):
        # "curve" should be a list of (x, y) points
        # representing the curve
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

            self.buffer_ready = False

        def write_to_world_space(self, pixel_coord, pixel_rgb, entity_id):
            self.world_space[pixel_coord] = pixel_rgb, entity_id

        def return_world_space(self):
            return {key: value[0] for key, value in self.world_space.copy().items()}

        def get_from_world_space(self, pixel_coord):
            try:
                return self.world_space[pixel_coord]
            except KeyError:
                return None

        def del_world_space_item(self, coord):
            try:
                del self.world_space[coord]
            except KeyError:
                pass

        def erase_world_space(self):
            self.world_space = {"end": "ended"}

    world_space_access = WorldSpaceControl()


class LifeForm:
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

        self.waiting_to_spawn = False

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

        self.max_attribute = current_session.max_attribute + max_attrib_expand

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

        # reset the global random seed
        random.seed()

        # set the starting location of the life form from the x and y positions
        self.matrix_position_x = start_x
        self.matrix_position_y = start_y

        self.prev_matrix_position = (self.matrix_position_x, self.matrix_position_y)

        self.lifeforms.update({self.life_form_id: self})

        current_session.world_space_access.write_to_world_space((self.matrix_position_x, self.matrix_position_y),
                                                                (self.red_color, self.green_color, self.blue_color),
                                                                self.life_form_id)

    def get_dna(self, dna_key, collided_life_form_id):
        dna_chaos = floor(100 * random.random())
        if dna_chaos <= current_session.get_dna_chaos_chance():
            return get_random()
        else:
            if dna_key == 1:
                if random.random() < .5:
                    return self.life_seed1
                else:
                    return LifeForm.lifeforms[collided_life_form_id].life_seed1
            elif dna_key == 2:
                if random.random() < .5:
                    return self.life_seed2
                else:
                    return LifeForm.lifeforms[collided_life_form_id].life_seed2
            elif dna_key == 3:
                if random.random() < .5:
                    return self.life_seed3
                else:
                    return LifeForm.lifeforms[collided_life_form_id].life_seed3

    def get_stats(self):
        """
        Display stats of life form.
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
        Will move the entity in its currently set direction (with 8 possible directions), if it hits the
        edge of the board it will then assign a new random direction to go in, this function also handles the time to
        move count which when hits 0 will select a new random direction for the entity regardless of whether it has hit
        the edge of the board or another entity.
        """

        try:
            if self.time_to_live_count > 0:
                self.time_to_live_count -= percentage(current_session.radiation * args.radiation_dmg_multi, 1)
                expired = False
            elif self.time_to_live_count <= 0:
                expired = True

            if expired:
                self.entity_remove()
                return
        except KeyError:
            logger.debug(f"Missing entity: {self.life_form_id}")
            return

        current_session.current_life_form_amount = len(list(LifeForm.lifeforms.values()))
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
                        current_session.world_space_access.get_from_world_space(self.adj_position)[1]
                    collision_detected = True
                    collided_life_form_id = s_item_life_form_id
                except TypeError:

                    collision_detected = False
                    collided_life_form_id = None
        else:

            collision_detected = False
            collided_life_form_id = None

        if self.waiting_to_spawn:
            preferred_direction = random.choice(current_session.surrounding_point_choices)

        # get the count of total life forms currently active
        # if there has been a collision with another entity it will attempt to interact with the other entity
        if collision_detected:
            if self.bouncy:
                momentum_reduction = percentage(10, self.momentum)
                self.momentum -= momentum_reduction
            else:
                momentum_reduction = percentage(60, self.momentum)
                self.momentum -= momentum_reduction

            logger.debug(f'Collision detected: {self.life_form_id} collided with {collided_life_form_id}')

            # store the current direction for later use, like if the life form kills another, it will continue moving
            # in that direction rather than bounce
            self.previous_direction = self.direction

            if not self.direction == self.preferred_direction:
                self.direction = self.preferred_direction
            else:
                self.direction = random.choice(current_session.directions)

            if collided_life_form_id:
                LifeForm.lifeforms[collided_life_form_id].momentum += momentum_reduction

                # if the aggression factor is below the entities breed threshold the life form will attempt to
                # breed with the one it collided with
                if abs(self.aggression_factor - LifeForm.lifeforms[collided_life_form_id].aggression_factor) \
                        <= self.breed_threshold:
                    # the other entity also needs to have its aggression factor below its breed threshold

                    if self.compatibility_factor + self.combine_threshold > \
                            LifeForm.lifeforms[
                                collided_life_form_id].compatibility_factor > self.compatibility_factor - self.combine_threshold:
                        if args.combine_mode:
                            logger.debug(f'Entity: {self.life_form_id} combined with: {collided_life_form_id}')

                            LifeForm.lifeforms[collided_life_form_id].linked_up = True
                            LifeForm.lifeforms[collided_life_form_id].linked_to = self.life_form_id

                            LifeForm.lifeforms[collided_life_form_id].direction = self.direction

                    if not self.waiting_to_spawn:
                        if random.random() < .5:
                            attrib_boost = self.max_attribute
                        else:
                            attrib_boost = LifeForm.lifeforms[collided_life_form_id].max_attribute

                        preferred_direction = self.preferred_breed_direction
                        self.waiting_seed1 = self.get_dna(1, collided_life_form_id)
                        self.waiting_seed2 = self.get_dna(2, collided_life_form_id)
                        self.waiting_seed3 = self.get_dna(3, collided_life_form_id)
                        self.waiting_max_attrib_expand = attrib_boost
                        self.waiting_to_spawn = True

                else:
                    if not LifeForm.lifeforms[collided_life_form_id].aggression_factor < \
                           LifeForm.lifeforms[collided_life_form_id].breed_threshold:

                        # if the other entities' aggression factor is lower it will be killed and removed from the
                        # main loops list of entities

                        if LifeForm.lifeforms[collided_life_form_id].strength < self.strength:
                            logger.debug('Other entity killed')

                            self.time_to_live_count += LifeForm.lifeforms[collided_life_form_id].time_to_live_count
                            self.weight += LifeForm.lifeforms[collided_life_form_id].weight
                            self.strength += LifeForm.lifeforms[collided_life_form_id].strength

                            LifeForm.lifeforms[collided_life_form_id].entity_remove()

                            self.direction = self.previous_direction

                            collision_check = True

                        # if the other entities' aggression factor is higher it will be killed the current entity
                        # it will be removed from the main loops list of entities
                        elif LifeForm.lifeforms[collided_life_form_id].strength > self.strength:
                            logger.debug('Current entity killed')

                            LifeForm.lifeforms[collided_life_form_id].time_to_live_count += self.time_to_live_count
                            LifeForm.lifeforms[collided_life_form_id].weight += self.weight
                            LifeForm.lifeforms[collided_life_form_id].strength += self.strength

                            collision_check = "Died"

                        elif LifeForm.lifeforms[collided_life_form_id].strength == self.strength:
                            logger.debug('Entities matched, flipping coin')

                            if random.random() < .5:
                                logger.debug('Current entity killed')
                                LifeForm.lifeforms[collided_life_form_id].time_to_live_count += self.time_to_live_count
                                LifeForm.lifeforms[collided_life_form_id].weight += self.weight
                                LifeForm.lifeforms[collided_life_form_id].strength += self.strength

                                collision_check = "Died"

                            else:
                                logger.debug('Other entity killed')
                                self.time_to_live_count += LifeForm.lifeforms[
                                    collided_life_form_id].time_to_live_count

                                LifeForm.lifeforms[collided_life_form_id].entity_remove()

                                self.direction = self.previous_direction

                                collision_check = True
                    else:
                        logger.debug('Other entity killed')
                        self.time_to_live_count += LifeForm.lifeforms[
                            collided_life_form_id].time_to_live_count

                        LifeForm.lifeforms[collided_life_form_id].entity_remove()

                        self.direction = self.previous_direction

                        collision_check = True

            collision_check = True
        else:
            collision_check = False

        if collision_check == "Died":
            return collision_check
        elif not collision_check:
            current_session.world_space_access.del_world_space_item((self.matrix_position_x, self.matrix_position_y))

            if self.direction == 'move_up':
                self.matrix_position_y -= 1
                self.momentum -= 2

            if self.direction == 'move_down':
                self.matrix_position_y += 1
                if args.gravity:
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
                if args.gravity:
                    self.momentum += 1
                else:
                    self.momentum -= 2

            if self.direction == 'move_down_and_left':
                self.matrix_position_y += 1
                self.matrix_position_x -= 1
                if args.gravity:
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
            current_session.world_space_access.write_to_world_space(
                (self.matrix_position_x, self.matrix_position_y),
                (self.red_color, self.green_color,
                 self.blue_color), self.life_form_id)

            # minus 1 from the time to move count until it hits 0, at which point the entity will change
            # direction from the "randomise direction" function being called
            if not self.linked_up:
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
                    self.direction = LifeForm.lifeforms[self.linked_to].direction
                except KeyError:
                    self.linked_up = False
                    if not self.direction == self.preferred_direction:
                        self.direction = self.preferred_direction
                    else:
                        self.direction = random.choice(current_session.directions)

        # the breeding will attempt only if the current life form count is not above the
        # population limit
        if self.waiting_to_spawn:
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
                        current_session.world_space_access.get_from_world_space(self.adj_position)[1]
                    except TypeError:
                        post_x_gen, post_y_gen = self.adj_position

                    else:

                        post_x_gen, post_y_gen = None, None
                        self.waiting_to_spawn = True
                else:
                    post_x_gen, post_y_gen = None, None
                    self.waiting_to_spawn = True

                if post_x_gen is not None and post_y_gen is not None:
                    # increase the life form total by 1
                    current_session.life_form_total_count += 1

                    LifeForm(
                        life_form_id=current_session.life_form_total_count,
                        seed=self.waiting_seed1,
                        seed2=self.waiting_seed2,
                        seed3=self.waiting_seed3,
                        start_x=post_x_gen,
                        start_y=post_y_gen,
                        max_attrib_expand=self.waiting_max_attrib_expand)

                    logger.debug(f"Generated X, Y positions for new life form: {post_x_gen}, {post_y_gen}")

                    self.waiting_to_spawn = False

            # if the current amount of life forms on the board is at the population limit or above
            # then do nothing
            elif current_session.current_life_form_amount >= args.pop_limit:
                logger.debug(f"Max life form limit: {args.pop_limit} reached")
                self.waiting_to_spawn = True

        if self.strength < self.weight:
            self.direction = 'still'

        if args.gravity and (self.strength < self.weight or self.direction == 'still'
                             or self.momentum <= 0):
            self.direction = 'move_down'
            logger.debug(f"Moved from gravity")

    def entity_remove(self):
        """
        Due to the fact the class holder needs copying to be able to iterate and modify it at the same time we can
        have dead entities being looped over before the current board has been processed, so we need to remove the
        entity from the board entirely and blank it on top of the alive check that will skip it, to double ensure a
        dead entity is no longer interacted with during a loop that it died in.
        """
        current_session.world_space_access.del_world_space_item((self.matrix_position_x, self.matrix_position_y))
        self.alive = False
        current_session.last_removal = self.life_form_id
        del LifeForm.lifeforms[self.life_form_id]
        logger.debug(f"Entity {self.life_form_id} removed")

    def fade_entity(self):
        """
        Erases an entity from the board by fading it away.
        """
        # todo: make a shader for this instead
        for c in range(0, 255):
            if self.red_color > 0:
                self.red_color -= 1
            if self.green_color > 0:
                self.green_color -= 1
            if self.blue_color > 0:
                self.blue_color -= 1
            ScreenController.screen.set_pixel(self.matrix_position_x, self.matrix_position_y, self.red_color,
                                              self.green_color,
                                              self.blue_color)
            ScreenController.screen.show()
        self.life_form_id.entity_remove()


class DrawObjects(ScreenDrawer):

    def __init__(self, output_controller, buffer_refresh, session_info, exit_text):
        super().__init__(output_controller=output_controller,
                         buffer_refresh=buffer_refresh,
                         session_info=session_info,
                         exit_text=exit_text)

        self.frame_buffer_access = FrameBufferInit(self.session_info)

        self.render_stack = ['background_shader_pass',
                             'object_colour_pass',
                             'tone_map_pass',
                             'render_frame_buffer',
                             'float_to_rgb_pass',
                             'buffer_scan',
                             'flush_buffer']

        self.draw()


class FrameBufferInit(FrameBuffer):

    def __init__(self, session_info):
        super().__init__(session_info=session_info)

        self.blank_pixel = (0.0, 0.0, 0.0)

        # WARNING: be careful with these, it can cause flashing images
        # self.shader_stack.multi_shader_creator(input_shader=FullScreenPatternShader, number_of_shaders=2, base_number=4,
        #                                        base_addition=16, base_rgb=(1.25, 0.0, 0.0))
        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=32, shader_colour=(0.0, 1.25, 0.0)))
        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=31, shader_colour=(0.0, 0.0, 1.25)))

        # self.shader_stack.add_to_shader_stack(
        #     FullScreenPatternShader(count_number_max=7, shader_colour=(0.0, 1.0, 0.0)))

        self.motion_blur.shader_colour = (0.0, 0.0, 0.0)
        self.motion_blur.static_shader_alpha = 0.9

        self.lighting.shader_colour = (1.0, 1.0, 1.0)
        self.lighting.light_strength = 10.0
        self.lighting.moving_light = False


def global_board_generator():
    # with collision detection determine if a spot on the board contains a life form
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
    Determine percentage of a whole number
    """
    return int(round(percent * whole) / 100.0)


def get_random():
    """
    Generate a random number to be used as a seed, this is used to generate all 3 life seeds resulting in 1.e+36
    possible types of life form.
    """
    # todo: add in some sort of fibonacci sequence stuff in here?
    return random.getrandbits(500)


def thanos_snap():
    """
    Randomly kill half of the entities in existence on the board
    """
    # todo: reconfigure all this to use the new rasterizer
    # loop for 50% of all existing entities choosing at random to eliminate
    for x in range(int(len(LifeForm.lifeforms.values()) / 2)):
        vanished = random.choice((list(LifeForm.lifeforms.values())))
        # fade them away
        LifeForm.lifeforms[vanished].fade_entity()
    logger.info("Perfectly balanced as all things should be")


def class_generator(life_form_id):
    """
    Assign all the life_form_ids into class instances for each life form for each life_form_id in the list of all
    life form life_form_ids assign a random x and y number for the position on the board and create the new life
    form with random seeds for each life seed generation.
    """
    try:
        starting_x, starting_y = global_board_generator()
    except TypeError:
        return

    LifeForm(life_form_id=life_form_id, seed=get_random(), seed2=get_random(), seed3=get_random(),
             start_x=starting_x, start_y=starting_y)


def main():
    frame_refresh_delay_ms = 1 / hat_buffer_refresh_rate
    """
    Main loop where all life form movement and interaction takes place
    """
    # wrap main loop into a try/catch to allow keyboard exit and cleanup
    first_run = True
    current_session.max_movement = diagonal_distance(0, 0, ScreenController.u_width, ScreenController.u_height)
    next_frame = time() + frame_refresh_delay_ms
    while True:
        # todo: add in a check to see if the buffer is ready to be written to before writing to it, will need to
        #  implement a buffer ready flag on the rasterizer side of things also
        # if time() > next_frame or not refresh_logic_link and current_session.world_space_access.buffer_ready:
        # for now this just checks whether the next frame time is ready or whether refresh logic is disabled
        # this allows the internal logic to operate faster than the refresh rate of the display, so it will run faster
        # but the display will always be behind resulting in entities looking like they are teleporting around
        life_form_container = LifeForm.lifeforms.copy().values()
        if time() > next_frame or not refresh_logic_link:
            # check the list of entities has items within
            if life_form_container:
                # for time the current set of life forms is processed increase the layer for minecraft to set blocks
                # on by 1
                # current_session.current_layer += 1
                # for each life_form_id in the list use the life_form_id of the life form to work from
                # replace with map()?
                [life_form.process() for life_form in life_form_container]

            # if the main list of entities is empty then all have expired; the program displays final information
            # about the programs run and exits; unless retry mode is active, then a new set of entities are created
            # and the simulation starts fresh with the same initial configuration
            elif not life_form_container:
                if first_run:
                    [class_generator(i) for i in range(args.life_form_total)]

                    first_run = False

                    continue

                elif current_session.retries:
                    current_session.highest_concurrent_lifeforms = 0
                    current_session.current_layer = 0
                    current_session.last_removal = -1
                    current_session.get_coord_map()

                    [class_generator(i) for i in range(args.life_form_total)]

                    continue
                else:
                    logger.info(
                        f'\n All Lifeforms have expired.\n Total life forms produced: '
                        f'{current_session.life_form_total_count}\n '
                        f'Max concurrent Lifeforms was: {current_session.highest_concurrent_lifeforms}\n')
                    current_session.world_space_access.erase_world_space()
                    quit()

            logger.debug(f"Lifeforms: {current_session.life_form_total_count}")

            if args.radiation_change:
                current_session.adjust_radiation_along_curve()

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

    parser.add_argument('-shs', '--simulator-hat-size', action="store", dest="custom_size_simulator", type=tuple,
                        default=hat_simulator_or_panel_size,
                        help='Maximum possible time to move number for entities')

    parser.add_argument('-c', '--combine-mode', action="store_true", dest="combine_mode",
                        help='Enables life forms to combine into bigger ones')

    parser.add_argument('-mc', '--minecraft-mode', action="store_true", dest="mc_mode",
                        help='Enables Minecraft mode')

    parser.add_argument('-tr', '--trails', action="store_true", dest="trails_on",
                        help='Stops the HAT from being cleared, resulting in trails of entities')

    parser.add_argument('-g', '--gravity', action="store_true", dest="gravity",
                        help='Gravity enabled, still entities will fall to the floor')

    parser.add_argument('-rc', '--radiation-change', action="store_true", dest="radiation_change",
                        help='Whether to adjust radiation levels across the simulation or not')

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

    parser.add_argument('-rt', '--retry', action="store_true", dest="retry_on",
                        help='Whether the loop will automatically restart upon the expiry of all entities')

    parser.add_argument('-sim', '--unicorn-hat-sim', action="store_true", dest="simulator",
                        help='Whether to use the Unicorn HAT simulator or not')

    parser.add_argument('-hm', '--hat-model', action="store", dest="hat_edition", type=str, default=hat_model,
                        choices=['SD', 'HD', 'MINI', 'PANEL', 'CUSTOM'],
                        help='What type of HAT the program is using. CUSTOM '
                             'only works with Unicorn HAT Simulator')

    parser.add_argument('-l', '--log-level', action="store", dest="log_level", type=str, default=logging_level,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], help='Logging level')

    parser.add_argument('-ff', '--fixed-function', action="store_true", dest="fixed_function",
                        help='Whether to bypass pixel composer and use fixed function '
                             'for drawing (faster, less pretty)')

    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    ScreenController = ScreenController(screen_type=args.hat_edition, simulator=args.simulator,
                                        custom_size_simulator=args.custom_size_simulator, led_brightness=led_brightness)

    # setup Minecraft connection if mc_mode is True
    # if args.mc_mode:
    #     mc = Minecraft.create()
    #     mc.postToChat("PiLife Plugged into Minecraft!")

    current_session = Session(life_form_total_count=args.life_form_total,
                              max_enemy_factor=args.max_enemy_factor,
                              draw_trails=args.trails_on,
                              retries=args.retry_on,
                              highest_concurrent_lifeforms=args.life_form_total,
                              radiation=args.radiation,
                              radiation_max=args.max_radiation,
                              dna_chaos_chance=args.dna_chaos_chance,
                              radiation_change=args.radiation_change,
                              radiation_base_change_chance=args.radiation_base_change_chance,
                              max_attribute=args.max_num)

    Thread(target=main, daemon=True).start()

    if not args.fixed_function:
        draw_control = DrawObjects(output_controller=ScreenController,
                                   buffer_refresh=hat_buffer_refresh_rate,
                                   session_info=current_session,
                                   exit_text='Program ended by user.\n Total life forms produced: ${'
                                             'life_form_total_count}\n Max'
                                             'concurrent Lifeforms was: ${highest_concurrent_lifeforms}\n Last count '
                                             'of active'
                                             'Lifeforms: ${current_life_form_amount}')
    else:
        while True:
            [ScreenController.draw_pixels(coord, (0, 0, 0)) for coord in
             current_session.coord_map]
            [ScreenController.draw_pixels(coord, pixel[0]) for coord, pixel in
             current_session.world_space_access.world_space.copy().items()]
            ScreenController.show()
