import argparse
import logging
import os
import random
import sys
from dataclasses import dataclass
import statistics
from time import time

from screen_output import ScreenController

# from mcpi.minecraft import Minecraft

renderer_dir = os.path.join(os.path.dirname(__file__), 'pixel_composer')

sys.path.append(renderer_dir)

from pixel_composer.rasterizer import ScreenDrawer

from threading import Thread

from config.parameters import initial_lifeforms_count, population_limit, logging_level, initial_dna_chaos_chance, \
    led_brightness, hat_model, hat_simulator_size, hat_buffer_refresh_rate, refresh_logic_link, max_trait_number, \
    initial_radiation

logger = logging.getLogger("alife-logger")


def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)


# todo: move this into the class
def find_adjacent_positions(grid, object_position):
    surrounding_positions = []
    x, y = object_position
    for i in range(-1, 2):
        for j in range(-1, 2):
            if i == 0 and j == 0:
                continue
            new_row, new_col = x + i, y + j
            if 0 <= new_row < len(grid) and 0 <= new_col < len(grid[0]):
                surrounding_positions.append((new_row, new_col))
    return surrounding_positions


@dataclass
class Session:
    """
    Class for storing current session information to make it easily accessible from within the LifeForm class and the
    main logic loop
    """
    highest_concurrent_lifeforms: int
    draw_trails: bool
    retries: bool
    radiation_change: bool
    radiation: int
    radiation_curve = [(0, 0.5), (1, 2), (2, 1), (3, 1.5)]
    dna_chaos_chance: int
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

        self.free_board_positions = list(self.coord_map)

        self.base_radiation = self.radiation

    def get_dna_chaos_chance(self):
        return clamp(statistics.median([self.dna_chaos_chance + self.radiation]), 0, 100)

    def adjust_radiation_along_curve(self):
        # "curve" should be a list of (x, y) points
        # representing the curve
        self.radiation = int(self.base_radiation * random.uniform(min([y for x, y in self.radiation_curve]),
                                                                  max([y for x, y in self.radiation_curve])))

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

        # set linked status to False; when linked an entity will continue to move in the same direction as the entity
        # it is linked with essentially combining into one bigger entity
        self.linked_up = False
        self.linked_to = 0

        self.previous_direction = None

        self.life_seed1 = seed
        self.life_seed2 = seed2
        self.life_seed3 = seed3

        random.seed(self.life_seed1 + self.life_seed2 + self.life_seed3)
        self.max_attribute = random.randint(1, args.max_num) + max_attrib_expand

        # life seed 1 controls the random number generation for the red colour, maximum aggression factor starting
        # direction and maximum possible lifespan
        random.seed(self.life_seed1)
        if not args.fixed_function:
            self.red_color = random.uniform(0, 1)
        else:
            self.red_color = random.randint(0, 255)
        self.breed_threshold = random.randint(0, self.max_attribute)
        self.combine_threshold = random.randint(0, self.max_attribute)
        self.preferred_breed_direction = random.choice(current_session.surrounding_point_choices)
        self.strength = random.randint(0, self.max_attribute)

        # life seed 2 controls the random number generation for the green colour, aggression factor between 0 and the
        # maximum from above as well as the time the entity takes to change direction
        random.seed(self.life_seed2)
        if not args.fixed_function:
            self.green_color = random.uniform(0, 1)
        else:
            self.green_color = random.randint(0, 255)
        self.aggression_factor = random.randint(0, self.max_attribute)
        self.time_to_move = random.randint(1, self.max_attribute)
        self.time_to_move_count = self.time_to_move
        self.weight = random.randint(0, self.max_attribute)

        # life seed 3 controls the random number generation for the green colour, and time to live between 0 and the
        # maximum from above
        random.seed(self.life_seed3)
        if not args.fixed_function:
            self.blue_color = random.uniform(0, 1)
        else:
            self.blue_color = random.randint(0, 255)
        self.time_to_live = random.randint(0, self.max_attribute)
        self.time_to_live_count = self.time_to_live

        self.direction = random.choice(current_session.directions)
        self.preferred_direction = self.direction

        self.out_of_moves = False
        self.attempted_directions = set()

        # reset the global random seed
        random.seed()

        # set the starting location of the life form from the x and y positions
        self.matrix_position_x = start_x
        self.matrix_position_y = start_y

        self.prev_matrix_position = (self.matrix_position_x, self.matrix_position_y)

        # get current surrounding co-ords of the life form
        self.surrounding_positions()

        self.lifeforms.update({self.life_form_id: self})

        current_session.world_space_access.write_to_world_space((self.matrix_position_x, self.matrix_position_y),
                                                                (self.red_color, self.green_color, self.blue_color),
                                                                self.life_form_id)

    def get_dna(self, dna_key, collided_life_form_id):
        dna_chaos = random.randint(1, 100)
        if dna_chaos <= current_session.get_dna_chaos_chance():
            return get_random()
        else:
            if dna_key == 1:
                if fifty_fifty():
                    return self.life_seed1
                else:
                    return LifeForm.lifeforms[collided_life_form_id].life_seed1
            elif dna_key == 2:
                if fifty_fifty():
                    return self.life_seed2
                else:
                    return LifeForm.lifeforms[collided_life_form_id].life_seed2
            elif dna_key == 3:
                if fifty_fifty():
                    return self.life_seed3
                else:
                    return LifeForm.lifeforms[collided_life_form_id].life_seed3

    def collision_factory(self):
        # check for any collisions with any other entities and return the life_form_id of an entity
        # collided with
        collision_detected, collided_life_form_id = self.collision_detector()
        # get the count of total life forms currently active
        # if there has been a collision with another entity it will attempt to interact with the other entity
        if collision_detected:
            logger.debug(f'Collision detected: {self.life_form_id} collided with {collided_life_form_id}')

            # store the current direction for later use, like if the life form kills another, it will continue moving
            # in that direction rather than bounce
            self.previous_direction = self.direction

            self.attempted_directions = set()

            self.out_of_moves = False

            self.attempted_directions.add(self.direction)

            # call to randomise direction function for the entity
            self.randomise_direction()

            collision_detected_again, collided_life_form_id_again = self.collision_detector()

            # find a new direction until a free space is found, if nowhere around the life form is clear
            # it will go to a still state until it attempts to change direction again
            while collision_detected_again:
                logger.debug(
                    f'Collision detected again: {self.life_form_id} collided with {collided_life_form_id_again}, '
                    f'with previously tried directions: {self.attempted_directions}')

                # storing previously attempted directions so that the same direction is not tried again
                self.attempted_directions.add(self.direction)

                self.randomise_direction()

                if self.out_of_moves:
                    break

                collision_detected_again, collided_life_form_id_again = self.collision_detector()

            if collided_life_form_id:
                if collided_life_form_id is None:
                    raise Exception("Should not reach this point if ID was none")

                # if the aggression factor is below the entities breed threshold the life form will attempt to
                # breed with the one it collided with
                if self.aggression_factor < self.breed_threshold:
                    # the other entity also needs to have its aggression factor below its breed threshold
                    if LifeForm.lifeforms[collided_life_form_id].aggression_factor < \
                            LifeForm.lifeforms[collided_life_form_id].breed_threshold:
                        self.combine_entities(life_form_2=collided_life_form_id)
                        # the breeding will attempt only if the current life form count is not above the
                        # population limit
                        if current_session.current_life_form_amount < args.pop_limit:
                            # find a place for the new entity to spawn around the current parent life form
                            try:
                                post_x_gen, post_y_gen = self.board_position_generator()
                            except TypeError:
                                logger.debug("No space available for a spawn of a new life form")

                                return True

                            # increase the life form total by 1
                            current_session.life_form_total_count += 1

                            if fifty_fifty():
                                attrib_boost = self.max_attribute
                            else:
                                attrib_boost = LifeForm.lifeforms[collided_life_form_id].max_attribute

                            LifeForm(
                                life_form_id=current_session.life_form_total_count,
                                seed=self.get_dna(1, collided_life_form_id),
                                seed2=self.get_dna(2, collided_life_form_id),
                                seed3=self.get_dna(3, collided_life_form_id),
                                start_x=post_x_gen,
                                start_y=post_y_gen,
                                max_attrib_expand=attrib_boost)

                            logger.debug(f"Generated X, Y positions for new life form: {post_x_gen}, {post_y_gen}")

                        # if the current amount of life forms on the board is at the population limit or above
                        # then do nothing
                        elif current_session.current_life_form_amount >= args.pop_limit:
                            logger.debug(f"Max life form limit: {args.pop_limit} reached")
                    else:
                        # if the life form has bumped into another life form that is above the breed
                        # threshold, the two life forms will engage in combat
                        return self.combat(other_life_form_id=collided_life_form_id)

                # if the entities' aggression factor is above its breed threshold it will attempt to kill the entity
                # it has collided with instead of breed
                elif self.aggression_factor > self.breed_threshold:
                    return self.combat(other_life_form_id=collided_life_form_id)

            return True
        else:
            return False

    def combat(self, other_life_form_id):
        # if the other entities' aggression factor is lower it will be killed and removed from the
        # main loops list of entities

        if LifeForm.lifeforms[other_life_form_id].strength < self.strength:
            logger.debug('Other entity killed')

            self.time_to_live_count += LifeForm.lifeforms[other_life_form_id].time_to_live_count
            self.weight += LifeForm.lifeforms[other_life_form_id].weight
            self.strength += LifeForm.lifeforms[other_life_form_id].strength

            LifeForm.lifeforms[other_life_form_id].entity_remove()

            self.direction = self.previous_direction

            return True

        # if the other entities' aggression factor is higher it will be killed the current entity
        # it will be removed from the main loops list of entities
        elif LifeForm.lifeforms[other_life_form_id].strength > self.strength:
            logger.debug('Current entity killed')

            LifeForm.lifeforms[other_life_form_id].time_to_live_count += self.time_to_live_count
            LifeForm.lifeforms[other_life_form_id].weight += self.weight
            LifeForm.lifeforms[other_life_form_id].strength += self.strength

            return "Died"

        elif LifeForm.lifeforms[other_life_form_id].strength == self.strength:
            logger.debug('Entities matched, flipping coin')

            if fifty_fifty():
                logger.debug('Current entity killed')
                LifeForm.lifeforms[other_life_form_id].time_to_live_count += self.time_to_live_count
                LifeForm.lifeforms[other_life_form_id].weight += self.weight
                LifeForm.lifeforms[other_life_form_id].strength += self.strength

                return "Died"

            else:
                logger.debug('Other entity killed')
                self.time_to_live_count += LifeForm.lifeforms[
                    other_life_form_id].time_to_live_count

                LifeForm.lifeforms[other_life_form_id].entity_remove()

                self.direction = self.previous_direction

                return True

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

    def get_position_up(self):
        self.adj_position = (self.matrix_position_x, self.matrix_position_y - 1)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def get_position_down(self):
        self.adj_position = (self.matrix_position_x, self.matrix_position_y + 1)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def get_position_left(self):
        self.adj_position = (self.matrix_position_x - 1, self.matrix_position_y)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def get_position_right(self):
        self.adj_position = (self.matrix_position_x + 1, self.matrix_position_y)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def get_position_up_and_right(self):
        self.adj_position = (self.matrix_position_x + 1, self.matrix_position_y - 1)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def get_position_up_and_left(self):
        self.adj_position = (self.matrix_position_x - 1, self.matrix_position_y - 1)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def get_position_down_and_right(self):
        self.adj_position = (self.matrix_position_x + 1, self.matrix_position_y + 1)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def get_position_down_and_left(self):
        self.adj_position = (self.matrix_position_x - 1, self.matrix_position_y + 1)
        if self.adj_position not in current_session.coord_map:
            self.adj_position = None

    def move_up(self):
        self.matrix_position_y -= 1
        return True

    def move_down(self):
        self.matrix_position_y += 1
        return True

    def move_left(self):
        self.matrix_position_x -= 1
        return True

    def move_right(self):
        self.matrix_position_x += 1
        return True

    def move_up_and_right(self):
        self.move_up()
        self.move_right()
        return True

    def move_up_and_left(self):
        self.move_up()
        self.move_left()
        return True

    def move_down_and_right(self):
        self.move_down()
        self.move_right()
        return True

    def move_down_and_left(self):
        self.move_down()
        self.move_left()
        return True

    def still(self):
        return True

    def movement(self):
        """
        Will move the entity in its currently set direction (with 8 possible directions), if it hits the
        edge of the board it will then assign a new random direction to go in, this function also handles the time to
        move count which when hits 0 will select a new random direction for the entity regardless of whether it has hit
        the edge of the board or another entity.
        """

        # if entity is dead then skip and return
        if not self.alive:
            return "Dead"
        # todo: make the gravity system a lot better and work off of calculations of weight strength etc.
        if self.strength < self.weight:
            self.direction = 'still'
        elif self.strength > self.weight and self.direction == 'still':
            self.randomise_direction()

        collision_check = self.collision_factory()

        # self.prev_matrix_position = (self.matrix_position_x, self.matrix_position_y)

        if collision_check == "Died":
            return collision_check
        elif not collision_check:
            # todo: tidy up the movement system for less repeated code, so the collision checks are done within the
            #  movement functions
            current_session.world_space_access.del_world_space_item((self.matrix_position_x, self.matrix_position_y))
            moved = getattr(self, self.direction)()
            if moved:
                self.surrounding_positions()

                # write new position in the buffer
                current_session.world_space_access.write_to_world_space(
                    (self.matrix_position_x, self.matrix_position_y),
                    (self.red_color, self.green_color,
                     self.blue_color), self.life_form_id)

                if args.gravity and (self.strength < self.weight or self.direction == 'still'):

                    self.prev_matrix_position = (self.matrix_position_x, self.matrix_position_y)
                    pre_grav_direction = self.direction
                    self.direction = 'move_down'

                    # if entity is dead then skip and return
                    if not self.alive:
                        return "Dead"

                    collision_check = self.collision_factory()

                    if collision_check == "Died":
                        return collision_check
                    elif not collision_check:
                        current_session.world_space_access.del_world_space_item(
                            (self.matrix_position_x, self.matrix_position_y))
                        moved = getattr(self, self.direction)()
                        if moved:
                            self.surrounding_positions()
                            # current_session.world_space_access.del_world_space_item(self.prev_matrix_position)
                            # write new position in the buffer
                            current_session.world_space_access.write_to_world_space(
                                (self.matrix_position_x, self.matrix_position_y),
                                (self.red_color, self.green_color,
                                 self.blue_color), self.life_form_id)

                    self.direction = pre_grav_direction

                    logger.debug(f"Moved from gravity")

            # minus 1 from the time to move count until it hits 0, at which point the entity will change
            # direction from the "randomise direction" function being called
            if not self.linked_up:
                if self.time_to_move_count > 0:
                    self.time_to_move_count -= 1
                elif self.time_to_move_count <= 0:
                    self.time_to_move_count = self.time_to_move
                    self.randomise_direction()
            else:
                # if combining is enabled set to the direction of the linked entity, however the other entity may
                # have expired and weird things happen, and it may not be accessible from within the class holder
                # so just randomise direction and de-link
                try:
                    self.direction = LifeForm.lifeforms[self.linked_to].direction
                except KeyError:
                    self.linked_up = False
                    self.randomise_direction()

    def randomise_direction(self):
        """
        Select a random new direction for the life form that is not the direction it is
        already going. It also allows for a list of previously attempted directions to be passed in and excluded.
        """
        if self.direction not in self.attempted_directions:
            self.attempted_directions.add(self.direction)
        if self.preferred_direction not in self.attempted_directions:
            r = self.preferred_direction
        else:
            try:
                r = random.choice([d for d in current_session.directions if d not in self.attempted_directions])
                if r in self.attempted_directions:
                    raise Exception(f"Direction: {r} found in exclusion list: {self.attempted_directions}")

                self.direction = r
            except IndexError:
                r = 'still'
                self.out_of_moves = True

        logger.debug(f"New direction: {r} with exclusion list: {self.attempted_directions}")

        self.direction = r

    def linked(self, life_form_id):
        """
        Link the life form to another, to ensure that they try to move in the same direction.
        """
        self.linked_up = True
        self.linked_to = life_form_id

    def expire_entity(self):
        """
        Counts down a life forms time to live from its full lifetime assigned to it when a life forms time
        to live hits zero return True for deletion of the life forms class from the holder.
        """
        if self.time_to_live_count > 0:
            self.time_to_live_count -= (1 + current_session.radiation)
            return False
        elif self.time_to_live_count <= 0:
            return True

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

    def surrounding_positions(self):
        """
        Creates a list of all x, y points around the entity
        """

        self.positions_around_life_form = find_adjacent_positions(current_session.coord_map, (self.matrix_position_x,
                                                                                              self.matrix_position_y))

    def board_position_generator(self):
        """
        Get board positions for new entities, allows for collision detection, either choosing from across the whole
        board or in the immediate area around a life form (determined by the life_form_id variable passed in).
        """
        # check area around entity for other life forms
        if args.spawn_collision_detection:
            getattr(self, self.preferred_breed_direction)()

            preferred_spawn_point = self.adj_position

            data = current_session.world_space_access.get_from_world_space(preferred_spawn_point)

            if not data:
                chosen_free_coord = preferred_spawn_point
            else:
                collision_map = list(self.adj_position)

                while data:
                    try:
                        chosen_free_coord = collision_map.pop(random.randrange(len(collision_map)))
                        data = current_session.world_space_access.get_from_world_space(chosen_free_coord)
                    except IndexError:
                        # if no free space is found return None
                        return None
                    except ValueError:
                        # if no free space is found return None
                        return None

            logger.debug(f"Free space around the entity found: {chosen_free_coord}")
            # if no other entity is in this location return the co-ords
            return chosen_free_coord[0], chosen_free_coord[1]
        else:
            # with no collision detection enabled just choose a random spot
            positions = random.choice(self.positions_around_life_form)

            return positions[0], positions[1]

    def collision_detector(self):
        """
        Determine whether a life form is colliding with another currently on the board.
        """

        # check to see if the life form has reached the edge of the board vs its direction

        # using the direction of the current life form determine on next move if the life form were to collide with
        # another, if so return the id of the other life form
        if self.direction == 'move_right':
            self.get_position_right()
        elif self.direction == 'move_left':
            self.get_position_left()
        elif self.direction == 'move_down':
            self.get_position_down()
        elif self.direction == 'move_up':
            self.get_position_up()
        elif self.direction == 'move_down_and_right':
            self.get_position_down_and_right()
        elif self.direction == 'move_up_and_left':
            self.get_position_up_and_left()
        elif self.direction == 'move_down_and_left':
            self.get_position_down_and_left()
        elif self.direction == 'move_up_and_right':
            self.get_position_up_and_right()

        if not self.direction == 'still':
            if not self.adj_position:
                return True, None

            try:
                s_item_life_form_id = \
                    current_session.world_space_access.get_from_world_space(self.adj_position)[1]
            except TypeError:
                return False, None

            if s_item_life_form_id:
                return True, s_item_life_form_id

        return False, None

    def combine_entities(self, life_form_2):
        """
        If the aggression factor of both entities is within the combine_threshold range they will reach a stalemate and
        simply bounce off each other, unless combining is enabled - where they will combine to make a bigger life form.
        """
        if self.aggression_factor + self.combine_threshold > \
                LifeForm.lifeforms[life_form_2].aggression_factor > self.aggression_factor - self.combine_threshold:
            if args.combine_mode:
                logger.debug(f'Entity: {self.life_form_id} combined with: {life_form_2}')
                LifeForm.lifeforms[life_form_2].linked(life_form_id=self.life_form_id)
                LifeForm.lifeforms[life_form_2].direction = self.direction
            else:
                logger.debug('Neither entity killed')


def global_board_generator():
    # with collision detection determine if a spot on the board contains a life form

    if args.spawn_collision_detection:
        try:
            random_free_coord = current_session.free_board_positions.pop()

        except IndexError:

            # if no free space is found return None
            return None

        logger.debug(f"Free space around the entity found: {random_free_coord}")
        # if no other entity is in this location return the co-ords
        return random_free_coord[0], random_free_coord[1]
    else:
        # with no collision detection enabled just choose a random spot
        post_x_gen = random.randint(0, ScreenController.u_width_max)
        post_y_gen = random.randint(0, ScreenController.u_height_max)

        return post_x_gen, post_y_gen


def percentage(percent, whole):
    """
    Determine percentage of a whole number (not currently in use)
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


def fifty_fifty():
    """
    When a 50/50 chance needs to be calculated.
    """
    if random.random() < .5:
        return True
    return False


def main():
    frame_refresh_delay_ms = 1 / hat_buffer_refresh_rate
    """
    Main loop where all life form movement and interaction takes place
    """
    # wrap main loop into a try/catch to allow keyboard exit and cleanup
    first_run = True
    next_frame = time() + frame_refresh_delay_ms
    while True:
        # todo: add in a check to see if the buffer is ready to be written to before writing to it, will need to
        #  implement a buffer ready flag on the rasterizer side of things also
        # if time() > next_frame or not refresh_logic_link and current_session.world_space_access.buffer_ready:
        # for now this just checks whether the next frame time is ready or whether refresh logic is disabled
        # this allows the internal logic to operate faster than the refresh rate of the display, so it will run faster
        # but the display will always be behind resulting in entities looking like they are teleporting around
        if time() > next_frame or not refresh_logic_link:
            # check the list of entities has items within
            if LifeForm.lifeforms.values():
                # for time the current set of life forms is processed increase the layer for minecraft to set blocks
                # on by 1
                current_session.current_layer += 1
                # for each life_form_id in the list use the life_form_id of the life form to work from
                # replace with map()?
                for life_form in LifeForm.lifeforms.copy().values():
                    # call expiry function for current life form and update the list of life forms
                    # todo: keep an eye on this, sometimes it will load an expired entity here despite not existing
                    try:
                        expired = life_form.expire_entity()
                        if expired:
                            life_form.entity_remove()
                            continue
                    except KeyError:
                        logger.debug(f"Missing entity: {life_form.life_form_id}")
                        continue

                    current_session.current_life_form_amount = len(list(LifeForm.lifeforms.values()))
                    # if the current number of active life forms is higher than the previous record of concurrent
                    # life forms, update the concurrent life forms variable
                    if current_session.current_life_form_amount > current_session.highest_concurrent_lifeforms:
                        current_session.highest_concurrent_lifeforms = current_session.current_life_form_amount
                    status_check = life_form.movement()

                    # if life form is no longer alive, skip; due to the fact we copy the holder into a list to allow
                    # the holder to be modified it may loop through dead entities until the while loop above the for
                    # loop iterates again with the fresh holder
                    if status_check == "Dead":
                        continue
                    elif status_check == "Died":
                        life_form.entity_remove()
                        continue

                    life_form.get_stats()

                    # run a check here to ensure that an expired entity is not being processed, unless it is the
                    # last entity - as after expiry of the final entity it will still loop one last time and
                    # iterate over that final entity one last time
                    if life_form.life_form_id == current_session.last_removal:
                        if len(LifeForm.lifeforms.values()) > 1:
                            raise Exception(
                                f"Entity {life_form.life_form_id} that expired this loop has been processed again")

                    # some debug-like code to identify when a life form goes outside the LED board
                    if life_form.matrix_position_x < 0 or \
                            life_form.matrix_position_x > ScreenController.u_width_max:
                        raise Exception("Life form has exceeded x axis")
                    if life_form.matrix_position_y < 0 or \
                            life_form.matrix_position_y > ScreenController.u_height_max:
                        raise Exception("Life form has exceeded y axis")

            # if the main list of entities is empty then all have expired; the program displays final information
            # about the programs run and exits; unless retry mode is active, then a new set of entities are created
            # and the simulation starts fresh with the same initial configuration
            elif not LifeForm.lifeforms.values():
                if first_run:
                    random.shuffle(current_session.free_board_positions)
                    [class_generator(i) for i in range(args.life_form_total)]

                    first_run = False

                    continue

                elif current_session.retries:
                    current_session.highest_concurrent_lifeforms = 0
                    current_session.current_layer = 0
                    current_session.last_removal = -1
                    current_session.free_board_positions = list(current_session.coord_map)
                    random.shuffle(current_session.free_board_positions)

                    [class_generator(i) for i in range(args.life_form_total)]

                    continue
                else:
                    logger.info(
                        f'\n All Lifeforms have expired.\n Total life forms produced: '
                        f'{current_session.life_form_total_count}\n '
                        f'Max concurrent Lifeforms was: {current_session.highest_concurrent_lifeforms}\n')
                    break

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

    parser.add_argument('-dc', '--dna-chaos', action="store", dest="dna_chaos_chance", type=int,
                        default=initial_dna_chaos_chance,
                        help='Percentage chance of random DNA upon breeding of entities')

    parser.add_argument('-shs', '--simulator-hat-size', action="store", dest="custom_size_simulator", type=tuple,
                        default=hat_simulator_size,
                        help='Maximum possible time to move number for entities')

    parser.add_argument('-c', '--combine-mode', action="store_true", dest="combine_mode",
                        help='Enables life forms to combine into bigger ones')

    parser.add_argument('-mc', '--minecraft-mode', action="store_true", dest="mc_mode",
                        help='Enables Minecraft mode')

    parser.add_argument('-tr', '--trails', action="store_true", dest="trails_on",
                        help='Stops the HAT from being cleared, resulting in trails of entities')

    parser.add_argument('-dcd', '--disable_collision_detection', action="store_false",
                        dest="spawn_collision_detection",
                        help='Whether entities can spawn over each other or not')

    parser.add_argument('-g', '--gravity', action="store_true", dest="gravity",
                        help='Gravity enabled, still entities will fall to the floor')

    parser.add_argument('-rc', '--radiation_change', action="store_true", dest="radiation_change",
                        help='Whether to adjust radiation levels across the simulation or not')

    parser.add_argument('-r', '--radiation', action="store", dest="radiation", type=int, default=initial_radiation,
                        help='Radiation enabled, will increase random mutation chance and damage entities')

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
                              draw_trails=args.trails_on,
                              retries=args.retry_on,
                              highest_concurrent_lifeforms=args.life_form_total,
                              radiation=args.radiation,
                              dna_chaos_chance=args.dna_chaos_chance,
                              radiation_change=args.radiation_change)

    Thread(target=main, daemon=True).start()

    if not args.fixed_function:
        ScreenDrawer(output_controller=ScreenController,
                     buffer_refresh=hat_buffer_refresh_rate,
                     session_info=current_session,
                     exit_text='Program ended by user.\n Total life forms produced: ${life_form_total_count}\n Max '
                               'concurrent Lifeforms was: ${highest_concurrent_lifeforms}\n Last count of active '
                               'Lifeforms: ${current_life_form_amount}')
    else:
        while True:
            [ScreenController.draw_pixels(coord, (0, 0, 0)) for coord in
             current_session.coord_map]
            [ScreenController.draw_pixels(coord, pixel[0]) for coord, pixel in
             current_session.world_space_access.world_space.copy().items()]
            ScreenController.show()
