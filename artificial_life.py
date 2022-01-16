import argparse
import logging
import random
import time

import unicornhat as unicorn
import unicornhathd as unicornhd
from unicornhatmini import UnicornHATMini

from mcpi.minecraft import Minecraft

from config.parameters import initial_lifeforms_count, speed, population_limit, max_time_to_live, max_aggression, \
    logging_level, breed_threshold, dna_chaos_chance, static_entity_chance, max_time_to_move, led_brightness, \
    combine_threshold, hat_model

logger = logging.getLogger("alife-logger")


class LifeForm(object):
    """
    The main class that handles each life forms initialisation, movement, colour, expiry and statistics.
    """

    def __init__(self, life_form_id, seed, seed2, seed3, start_x, start_y):
        """
        When class initialised it gives the life form its properties from the random numbers inserted into it,
        the life seeds are used to seed random number generators that then are used to generate the life form
        properties, this is so that the same results will come from the same life seeds and that the properties
        generated from them are non-linear i.e. higher life seed does not equal higher life span etc.
        """
        self.life_form_id = life_form_id

        # set linked status to False; when linked an entity will continue to move in the same direction as the entity
        # it is linked with essentially combining into one bigger entity
        self.linked_up = False
        self.linked_to = 0

        self.life_seed1 = seed
        self.life_seed2 = seed2
        self.life_seed3 = seed3
        # life seed 1 controls the random number generation for the red colour, maximum aggression factor starting
        # direction and maximum possible lifespan
        random.seed(self.life_seed1)
        self.red_color = random.randint(1, 255)
        self.max_aggression_factor = random.randint(1, args.max_aggro)
        self.direction_no = random.randint(1, 9)
        self.max_life = random.randint(1, args.max_ttl)
        # life seed 2 controls the random number generation for the green colour, aggression factor between 0 and the
        # maximum from above as well as the time the entity takes to change direction
        random.seed(self.life_seed2)
        self.green_color = random.randint(1, 255)
        self.aggression_factor = random.randint(0, self.max_aggression_factor)
        self.time_to_move = random.randint(1, args.max_moves)
        self.time_to_move_count = self.time_to_move
        # life seed 3 controls the random number generation for the green colour, and time to live between 0 and the
        # maximum from above
        random.seed(self.life_seed3)
        self.blue_color = random.randint(1, 255)
        self.time_to_live = random.randint(0, self.max_life)
        self.time_to_live_count = self.time_to_live
        self.moving_life_form_percent = random.randint(1, 100)
        if self.moving_life_form_percent < args.static_entity:
            self.moving_life_form = False
            self.direction = 9
        else:
            self.moving_life_form = True
            self.direction = self.direction_no
        # reset the global random seed
        random.seed()

        # set the starting location of the life form from the x and y positions
        self.matrix_position_x = start_x
        self.matrix_position_y = start_y

    def get_stats(self):
        """
        Display stats of life form.
        """
        logger.debug(f'ID: {self.life_form_id}')
        logger.debug(f'Seed 1: {self.life_seed1}')
        logger.debug(f'Seed 2: {self.life_seed2}')
        logger.debug(f'Seed 3: {self.life_seed3}')
        logger.debug(f'Direction: {self.direction}')
        logger.debug(f'Time to move total: {self.time_to_move}')
        logger.debug(f'Time to next move: {self.time_to_move_count}')
        logger.debug(f'Total lifetime: {self.time_to_live}')
        logger.debug(f'Time left to live: {self.time_to_live_count}')
        logger.debug(f'Aggression Factor: {self.aggression_factor}')
        logger.debug(f'Position X: {self.matrix_position_x}')
        logger.debug(f'Position Y: {self.matrix_position_y}')
        logger.debug(f'Color: R-{self.red_color} G-{self.green_color} B-{self.blue_color} \n')

    def movement(self):
        """
        Will move the entity in its currently set direction (with 8 possible directions), if it hits the
        edge of the board it will then assign a new random direction to go in, this function also handles the time to
        move count which when hits 0 will select a new random direction for the entity regardless of whether it has hit
        the edge of the board or another entity.
        """
        if self.moving_life_form:

            # if the edge of the board is not hit and direction is '1' then move the entity up the X axis by 1,
            # if it has hit the edge of the board its direction is randomised by the "randomise direction" function
            # being called for the entity
            if self.direction == 1:
                if self.matrix_position_x < u_width_max:
                    self.matrix_position_x += 1
                else:
                    self.direction = self.randomise_direction()

            # if the edge of the board is not hit and direction is '2' then move the entity down the X axis by 1,
            # if it has hit the edge of the board its direction is randomised by the "randomise direction" function
            # being called for the entity
            if self.direction == 2:
                if self.matrix_position_x > 0:
                    self.matrix_position_x -= 1
                else:
                    self.direction = self.randomise_direction()

            # if the edge of the board is not hit and direction is '3' then move the entity up the Y axis by 1,
            # if it has hit the edge of the board its direction is randomised by the "randomise direction" function
            # being called for the entity
            if self.direction == 3:
                if self.matrix_position_y < u_height_max:
                    self.matrix_position_y += 1
                else:
                    self.direction = self.randomise_direction()

            # if the edge of the board is not hit and direction is '4' then move the entity down the Y axis by 1,
            # if it has hit the edge of the board its direction is randomised by the "randomise direction" function
            # being called for the entity
            if self.direction == 4:
                if self.matrix_position_y > 0:
                    self.matrix_position_y -= 1
                else:
                    self.direction = self.randomise_direction()

            # if the edge of the board is not hit and direction is '5' then move the entity up the X and Y axis by 1,
            # if it has hit the edge of the board its direction is randomised by the "randomise direction" function
            # being called for the entity
            if self.direction == 5:
                if self.matrix_position_x < u_width_max and self.matrix_position_y < u_height_max:
                    self.matrix_position_x += 1
                    self.matrix_position_y += 1
                else:
                    self.direction = self.randomise_direction()

            # if the edge of the board is not hit and direction is '6' then move the entity down the X and Y axis by
            # 1, if it has hit the edge of the board its direction is randomised by the "randomise direction"
            # function being called for the entity
            if self.direction == 6:
                if self.matrix_position_x > 0 and self.matrix_position_y > 0:
                    self.matrix_position_x -= 1
                    self.matrix_position_y -= 1
                else:
                    self.direction = self.randomise_direction()

            # if the edge of the board is not hit and direction is '7' then move the entity down the X axis and up Y
            # axis by 1, if it has hit the edge of the board its direction is randomised by the "randomise direction"
            # function being called for the entity
            if self.direction == 7:
                if self.matrix_position_y < u_height_max and self.matrix_position_x > 0:
                    self.matrix_position_x -= 1
                    self.matrix_position_y += 1
                else:
                    self.direction = self.randomise_direction()

            # if the edge of the board is not hit and direction is '8' then move the entity up the X axis and down Y
            # axis by 1, if it has hit the edge of the board its direction is randomised by the "randomise direction"
            # function being called for the entity
            if self.direction == 8:
                if self.matrix_position_y > 0 and self.matrix_position_x < u_width_max:
                    self.matrix_position_x += 1
                    self.matrix_position_y -= 1
                else:
                    self.direction = self.randomise_direction()

            # if the direction is '9' do not move the entity
            elif self.direction == 9:
                if args.gravity:
                    if self.matrix_position_y < u_height_max:
                        self.matrix_position_y += 1
                else:
                    pass

            # minus 1 from the time to move count until it hits 0, at which point the entity will change direction from
            # the "randomise direction" function being called
            if not self.linked_up:
                if self.time_to_move_count > 0:
                    self.time_to_move_count -= 1
                elif self.time_to_move_count <= 0:
                    self.time_to_move_count = self.time_to_move
                    self.direction = self.randomise_direction()
            else:
                # if combining is enabled set to the direction of the linked entity, however the other entity may
                # have expired and weird things happen, and it may not be accessible from within the class holder
                # so just randomise direction and de-link
                try:
                    self.direction = holder[self.linked_to].direction
                except KeyError:
                    self.linked_up = False
                    self.direction = self.randomise_direction()

        elif args.gravity:
            if self.matrix_position_y < u_height_max:
                self.matrix_position_y += 1

    def randomise_direction(self, exclusion_list=None):
        """
        Select a random new direction for the life form that is not the direction it is
        already going. It also allows for a list of previously attempted directions to be passed in and excluded.
        """
        if exclusion_list is None:
            exclusion_list = []
        if self.direction not in exclusion_list:
            exclusion_list.append(self.direction)
        try:
            r = random.choice([d for d in range(1, 9) if d not in exclusion_list])
            self.direction = r
        except IndexError:
            r = False
        return r

    def linked(self, life_form_id):
        self.linked_up = True
        self.linked_to = life_form_id

    def expire_entity(self):
        """
        Counts down a life forms time to live from its full lifetime assigned to it when a life forms time
        to live hits zero return True for deletion of the life forms class from the holder.
        """
        if self.time_to_live_count > 0:
            self.time_to_live_count -= 1
            return False
        elif self.time_to_live_count <= 0:
            return True

    def fade_entity(self):
        """
        Erases an entity from the board by fading it away.
        """
        for c in range(0, 255):
            if self.red_color > 0:
                self.red_color -= 1
            if self.green_color > 0:
                self.green_color -= 1
            if self.blue_color > 0:
                self.blue_color -= 1
            unicorn.set_pixel(self.matrix_position_x, self.matrix_position_y, self.red_color, self.green_color,
                              self.blue_color)
            unicorn.show()
        del holder[self.life_form_id]


def draw_leds(x, y, r, g, b, current_layer):
    """
    Draw the position and colour of the current life form onto the board, if minecraft mode true, also set blocks
    relative to the player in the game world, adding 1 to the layer every iteration so that each time the current
    amount of entities is rendered it moves to another layer in minecraft, essentially building upwards.
    """
    try:
        unicorn.set_pixel(x, y, r, g, b)
    except IndexError:
        raise Exception(f"Set pixel did not like X:{x} Y:{y} R:{r} G:{g} B:{b}")
    # todo: improve this greatly
    if args.mc_mode:
        player_x, player_y, player_z = mc.player.getPos()
        random.seed(r + g + b)
        random_block = random.randint(1, 22)
        random.seed()
        mc.setBlock(player_x + x, player_y + 10 + current_layer, player_z + y, random_block)


def clear_leds():
    """
    Clear Unicorn HAT LEDs.
    """
    unicorn.clear()


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
    return random.randint(1, 1000000000000)


def thanos_snap():
    """
    Randomly kill half of the entities in existence on the board
    """
    # loop for 50% of all existing entities choosing at random to eliminate
    for x in range(int(len(holder) / 2)):
        vanished = random.choice(holder)
        # fade them away
        holder[vanished].fade_entity()
        time.sleep(0.1)
    logger.info("Perfectly balanced as all things should be")
    time.sleep(2)


def collision_detector(life_form_id):
    """
    Determine whether a life form is colliding with another currently on the board.
    """
    # get the board positions for the current life form
    life_form_id_x = holder[life_form_id].matrix_position_x
    life_form_id_y = holder[life_form_id].matrix_position_y
    life_form_id_direction = holder[life_form_id].direction

    # for every life form on the board loop through
    for item in list(holder):
        # split the items in the sub-list into separate variables for comparison
        s_item_life_form_id = item

        # get locations of the current entity
        s_item_x = holder[s_item_life_form_id].matrix_position_x
        s_item_y = holder[s_item_life_form_id].matrix_position_y

        # using the direction of the current life form determine on next move if the life form were to collide with
        # another, if so return the id of the other life form
        if life_form_id_direction == 1:
            if life_form_id_x + 1 == s_item_x and life_form_id_y == s_item_y:
                return s_item_life_form_id

        elif life_form_id_direction == 2:
            if life_form_id_x - 1 == s_item_x and life_form_id_y == s_item_y:
                return s_item_life_form_id

        elif life_form_id_direction == 3:
            if life_form_id_x == s_item_x and life_form_id_y + 1 == s_item_y:
                return s_item_life_form_id

        elif life_form_id_direction == 4:
            if life_form_id_x == s_item_x and life_form_id_y - 1 == s_item_y:
                return s_item_life_form_id

        elif life_form_id_direction == 5:
            if life_form_id_x + 1 == s_item_x and life_form_id_y + 1 == s_item_y:
                return s_item_life_form_id

        elif life_form_id_direction == 6:
            if life_form_id_x - 1 == s_item_x and life_form_id_y - 1 == s_item_y:
                return s_item_life_form_id

        elif life_form_id_direction == 7:
            if life_form_id_x - 1 == s_item_x and life_form_id_y + 1 == s_item_y:
                return s_item_life_form_id

        elif life_form_id_direction == 8:
            if life_form_id_x + 1 == s_item_x and life_form_id_y - 1 == s_item_y:
                return s_item_life_form_id

        # if direction is 9 then the life form is not moving and therefore is not going to collide with anything
        elif life_form_id_direction == 9:
            return False

    return False


def class_generator(life_form_id):
    """
    Assign all the life_form_ids into class instances for each life form for each life_form_id in the list of all
    life form life_form_ids assign a random x and y number for the position on the board and create the new life
    form with random seeds for each life seed generation.
    """
    generated_class = {
        life_form_id: LifeForm(life_form_id=life_form_id, seed=get_random(), seed2=get_random(), seed3=get_random(),
                               start_x=board_position_generator(collision_detection=True)[0],
                               start_y=board_position_generator(collision_detection=True)[1])}

    return generated_class


def board_position_generator(life_form_id=None, collision_detection=True, surrounding_area=False):
    """
    Get board positions for new entities, allows for collision detection, either choosing from across the whole board
    or in the immediate area around a life form (determined by the life_form_id variable passed in).
    """
    if surrounding_area:
        # get a list of all points around the entity
        positions_around_life_form = [
            [holder[life_form_id].matrix_position_x - 1, holder[life_form_id].matrix_position_y + 1],
            [holder[life_form_id].matrix_position_x, holder[life_form_id].matrix_position_y + 1],
            [holder[life_form_id].matrix_position_x + 1, holder[life_form_id].matrix_position_y + 1],
            [holder[life_form_id].matrix_position_x - 1, holder[life_form_id].matrix_position_y],
            [holder[life_form_id].matrix_position_x + 1, holder[life_form_id].matrix_position_y],
            [holder[life_form_id].matrix_position_x - 1, holder[life_form_id].matrix_position_y - 1],
            [holder[life_form_id].matrix_position_x, holder[life_form_id].matrix_position_y - 1],
            [holder[life_form_id].matrix_position_x + 1, holder[life_form_id].matrix_position_y - 1]]

        # check area around entity for other life forms using above list
        if collision_detection:
            for item in list(holder):
                s_item_x = holder[item].matrix_position_x
                s_item_y = holder[item].matrix_position_y

                for pos in positions_around_life_form:
                    if not pos[0] == s_item_x and not pos[1] == s_item_y:
                        post_x_gen = pos[0]
                        post_y_gen = pos[1]

                        # if free space found is outside the board try another location
                        if post_x_gen > u_height_max or post_x_gen < 0:
                            continue
                        if post_y_gen > u_width_max or post_y_gen < 0:
                            continue

                        logger.debug(f"Free space around the entity found: X: {post_x_gen}, Y: {post_y_gen}")

                        # if no other entity is in this location return the co-ords
                        return post_x_gen, post_y_gen
            # if no free space is found return None
            return None
        else:
            # with no collision detection enabled just choose a random spot
            positions = random.choice(positions_around_life_form)
            post_x_gen = positions[0]
            post_y_gen = positions[1]

            return post_x_gen, post_y_gen

    else:
        # if surrounding area of entity not enabled then choose from anywhere on the board
        post_x_gen = random.randint(0, 7)
        post_y_gen = random.randint(0, 7)

        # with collision detection determine if a spot on the board contains a life form
        if collision_detection:
            # assemble lists of possible x and y positions
            x_list = [0, 1, 2, 3, 4, 5, 6, 7]
            y_list = [0, 1, 2, 3, 4, 5, 6, 7]

            # shuffle them so they can be iterated through randomly
            random.shuffle(x_list)
            random.shuffle(y_list)

            # loop through all entity classes to determine locations
            try:
                for item in list(holder):
                    s_item_x = holder[item].matrix_position_x
                    s_item_y = holder[item].matrix_position_y
                    for x in x_list:
                        for y in y_list:
                            if not x == s_item_x and not y == s_item_y:
                                # if this location on the board does not contain an entity replace the previously
                                # randomly generated co-ords with the currently selected position and return them
                                post_x_gen = x
                                post_y_gen = y
                                return post_x_gen, post_y_gen
            # if this is the first entity being created then return random positions as there is nothing to loop
            # through and therefore nothing on the board to collide with
            except NameError:
                return post_x_gen, post_y_gen
            # if all else fails just return the previously generated random x, y co-ords
            return post_x_gen, post_y_gen
        # if no collision detection just return random x, y co-ords
        else:
            return post_x_gen, post_y_gen


def fifty_fifty():
    """
    When a 50/50 chance needs to be calculated.
    """
    if random.random() < .5:
        return True
    return False


def combine_entities(life_form_1, life_form_2):
    """
    If the aggression factor of both entities is within the combine_threshold range they will reach a stalemate and
    simply bounce off each other, unless combining is enabled - where they will combine to make a bigger life form.
    """
    if holder[life_form_1].aggression_factor + args.combine_threshold > \
            holder[life_form_2].aggression_factor > \
            holder[life_form_1].aggression_factor - args.combine_threshold:
        if args.combine_mode:
            logger.debug(f'Entity: {life_form_1} combined with: {life_form_2}')
            holder[life_form_2].linked(life_form_id=life_form_1)
            holder[life_form_2].direction = holder[life_form_1].direction
        else:
            logger.debug('Neither entity killed')


def main(concurrent_lifeforms_max, life_form_total_count, draw_trails, retries, random_dna_chance,
         highest_concurrent_lifeforms=0, current_layer=0):
    """
    Main loop where all life form movement and interaction takes place
    """
    # wrap main loop into a try/catch to allow keyboard exit and cleanup
    try:
        while True:

            # clear unicorn hat leds unless draw_trails is True
            if not draw_trails:
                clear_leds()

            # check the list of entities has items within
            if holder:
                # for time the current set of life forms is processed increase the layer for minecraft to set blocks
                # on by 1
                current_layer += 1

                # for each life_form_id in the list use the life_form_id of the life form to work from
                for life_form_id in list(holder):
                    # call expiry function for current life form and update the list of life forms
                    # todo: keep an eye on this, sometimes it will load an expired entity here despite not existing
                    try:
                        expired = holder[life_form_id].expire_entity()
                    except KeyError:
                        logger.debug(f"Missing entity: {life_form_id}")
                        continue
                    if expired:
                        del holder[life_form_id]
                        continue

                    # check for any collisions with any other entities and return the life_form_id of an entity
                    # collided with
                    collision_detected = collision_detector(life_form_id=life_form_id)
                    # get the count of total life forms currently active
                    current_life_form_amount = len(holder)
                    # if the current number of active life forms is higher than the previous record of concurrent
                    # life forms, update the concurrent life forms variable
                    if current_life_form_amount > highest_concurrent_lifeforms:
                        highest_concurrent_lifeforms = current_life_form_amount

                    # if there has been a collision with another entity it will attempt to interact with the other
                    # entity
                    if collision_detected:
                        logger.debug(f'Collision detected: {life_form_id} collided with {collision_detected}')

                        attempted_directions = []

                        # call to randomise direction function for the entity
                        direction_attempt = holder[life_form_id].randomise_direction()

                        collision_detected_again = collision_detector(life_form_id=life_form_id)

                        # storing previously attempted directions so that the same direction is not tried again
                        attempted_directions.append(direction_attempt)

                        # find a new direction until a free space is found, if nowhere around the life form is clear
                        # it will go to a still state until it attempts to change direction again
                        while collision_detected_again:
                            logger.debug(
                                f'Collision detected again: {life_form_id} collided with {collision_detected_again}, '
                                f'with previously tried directions: {attempted_directions}')
                            collision_detected_again = collision_detector(life_form_id=life_form_id)

                            direction_attempt = holder[life_form_id].randomise_direction(
                                exclusion_list=attempted_directions)

                            if not direction_attempt:
                                holder[life_form_id].direction = 9
                                break

                            attempted_directions.append(direction_attempt)

                        # if the aggression factor is below the configured threshold the life form will attempt to
                        # breed with the one it collided with
                        if holder[life_form_id].aggression_factor < breed_threshold:
                            # the other entity also needs to have its aggression factor below the breed threshold
                            if holder[collision_detected].aggression_factor < breed_threshold:
                                combine_entities(life_form_1=life_form_id, life_form_2=collision_detected)
                                # the breeding will attempt only if the current life form count is not above the
                                # population limit
                                if current_life_form_amount < concurrent_lifeforms_max:

                                    # find a place for the new entity to spawn around the current parent life form
                                    try:
                                        post_x_gen, post_y_gen = board_position_generator(surrounding_area=True,
                                                                                          collision_detection=True,
                                                                                          life_form_id=life_form_id)
                                    except TypeError:
                                        logger.debug("No space available for a spawn of a new life form")
                                        continue

                                    # increase the life form total by 1
                                    life_form_total_count += 1

                                    # the below assigns all 3 life seeds with the potential to take the life seed
                                    # from either parent (50% chance each), or whether a new random life seed will be
                                    # inserted (chance determined by parameter), resulting in some genetic chaos to
                                    # change offspring randomly
                                    dna_transfer_capsule = {'transfer_dna_1': 0, 'transfer_dna_2': 0,
                                                            'transfer_dna_3': 0}

                                    for key, values in dna_transfer_capsule.items():

                                        dna_chaos = random.randint(1, 100)
                                        if dna_chaos <= random_dna_chance:
                                            dna_transfer_capsule[key] = get_random()
                                        else:
                                            if key == 'transfer_dna_1':
                                                dna_parent = fifty_fifty()
                                                if dna_parent:
                                                    dna_transfer_capsule[key] = holder[life_form_id].life_seed1
                                                else:
                                                    dna_transfer_capsule[key] = holder[collision_detected].life_seed1
                                            elif key == 'transfer_dna_2':
                                                dna_parent = fifty_fifty()
                                                if dna_parent:
                                                    dna_transfer_capsule[key] = holder[life_form_id].life_seed2
                                                else:
                                                    dna_transfer_capsule[key] = holder[collision_detected].life_seed2
                                            elif key == 'transfer_dna_3':
                                                dna_parent = fifty_fifty()
                                                if dna_parent:
                                                    dna_transfer_capsule[key] = holder[life_form_id].life_seed3
                                                else:
                                                    dna_transfer_capsule[key] = holder[collision_detected].life_seed3

                                    h_update = {life_form_total_count: LifeForm(life_form_id=life_form_total_count,
                                                                                seed=dna_transfer_capsule[
                                                                                    'transfer_dna_1'],
                                                                                seed2=dna_transfer_capsule[
                                                                                    'transfer_dna_2'],
                                                                                seed3=dna_transfer_capsule[
                                                                                    'transfer_dna_3'],
                                                                                start_x=post_x_gen,
                                                                                start_y=post_y_gen)}

                                    holder.update(h_update)

                                # if the current amount of life forms on the board is at the population limit or above
                                # then do nothing
                                elif current_life_form_amount >= concurrent_lifeforms_max:
                                    logger.debug(f"Max life form limit: {concurrent_lifeforms_max} reached")
                            else:
                                # if the life form has bumped into another life form that is above the breed
                                # threshold, the other life form will now start moving in the same direction as the
                                # current life form
                                holder[collision_detected].direction = holder[life_form_id].direction

                        # if the entities' aggression factor is above 850 it will attempt to kill the entity it has 
                        # collided with instead of breed 
                        elif holder[life_form_id].aggression_factor > breed_threshold:
                            # if the other entities' aggression factor is lower it will be killed and removed from the
                            # main loops list of entities 
                            if holder[collision_detected].aggression_factor < holder[life_form_id].aggression_factor:
                                logger.debug('Other entity killed')

                                holder[life_form_id].time_to_live_count += holder[collision_detected].time_to_live_count

                                del holder[collision_detected]

                            # if the other entities' aggression factor is higher it will be killed the current entity 
                            # it will be removed from the main loops list of entities 
                            elif holder[collision_detected].aggression_factor > holder[life_form_id].aggression_factor:
                                logger.debug('Current entity killed')

                                holder[collision_detected].time_to_live_count += holder[life_form_id].time_to_live_count

                                del holder[life_form_id]

                                continue

                            elif holder[collision_detected].aggression_factor == holder[life_form_id].aggression_factor:
                                logger.debug('Entities matched, flipping coin')

                                if fifty_fifty():
                                    logger.debug('Current entity killed')
                                    holder[collision_detected].time_to_live_count += holder[
                                        life_form_id].time_to_live_count

                                    del holder[life_form_id]

                                    continue
                                else:
                                    logger.debug('Other entity killed')

                                    holder[life_form_id].time_to_live_count += holder[
                                        collision_detected].time_to_live_count

                                    del holder[collision_detected]

                    holder[life_form_id].movement()

                    holder[life_form_id].get_stats()

                    draw_leds(holder[life_form_id].matrix_position_x, holder[life_form_id].matrix_position_y,
                              holder[life_form_id].red_color, holder[life_form_id].green_color,
                              holder[life_form_id].blue_color, current_layer)

            # if the main list of entities is empty then all have expired; the program displays final information 
            # about the programs run and exits; unless retry mode is active, then a new set of entities are created
            # and the simulation starts fresh with the same initial configuration
            elif not holder:
                if retries:
                    highest_concurrent_lifeforms = 0
                    current_layer = 0

                    for n in range(args.life_form_total):
                        holder.update(class_generator(n))

                    continue
                else:
                    logger.info(
                        f'\n All Lifeforms have expired.\n Total life forms produced: {life_form_total_count}\n Max '
                        f'concurrent Lifeforms was: {highest_concurrent_lifeforms}\n')
                    break

            logger.debug(f"Lifeforms: {life_form_total_count}")

            unicorn.show()

            time.sleep(args.loop_speed)

    # upon keyboard interrupt display information about the program run before exiting
    except KeyboardInterrupt:
        logger.info(f'Program ended by user.\n Total life forms produced: {life_form_total_count}\n Max concurrent '
                    f'Lifeforms was: {highest_concurrent_lifeforms}\n Last count of active'
                    f' Lifeforms: {life_form_total_count}')
        GPIO.cleanup()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Artificial Life')

    parser.add_argument('-ilc', '--initial-lifeforms-count', action="store", dest="life_form_total", type=int,
                        default=initial_lifeforms_count,
                        help='Number of lifeforms to start with')

    parser.add_argument('-s', '--speed', action="store", dest="loop_speed", type=int,
                        default=speed,
                        help='Time for the loop delay, essentially the game-speed (although, lower; faster)')

    parser.add_argument('-p', '--population-limit', action="store", dest="pop_limit", type=int,
                        default=population_limit,
                        help='Limit of the population at any one time')

    parser.add_argument('-ttl', '--max-ttl', action="store", dest="max_ttl", type=int,
                        default=max_time_to_live,
                        help='Maximum time to live possible for life forms')

    parser.add_argument('-ma', '--max-aggression', action="store", dest="max_aggro", type=int,
                        default=max_aggression,
                        help='Maximum aggression factor possible for life forms')

    parser.add_argument('-dc', '--dna-chaos', action="store", dest="dna_chaos", type=int,
                        default=dna_chaos_chance,
                        help='Percentage chance of random DNA upon breeding of entities')

    parser.add_argument('-se', '--static-entity', action="store", dest="static_entity", type=int,
                        default=static_entity_chance,
                        help='Percentage chance of an entity being static')

    parser.add_argument('-mt', '--max-move-time', action="store", dest="max_moves", type=int,
                        default=max_time_to_move,
                        help='Maximum possible time to move number for entities')

    parser.add_argument('-ct', '--combine-threshold', action="store", dest="combine_threshold", type=int,
                        default=combine_threshold,
                        help='If a life form collides with another and both of their aggression levels are within '
                             'this range and combining is enabled, they will combine (move together)')

    parser.add_argument('-c', '--combine-mode', action="store_true", dest="combine_mode",
                        help='Enables life forms to combine into bigger ones')

    parser.add_argument('-mc', '--minecraft-mode', action="store_true", dest="mc_mode",
                        help='Enables Minecraft mode')

    parser.add_argument('-tr', '--trails', action="store_true", dest="trails_on",
                        help='Stops the HAT from being cleared, resulting in trails of entities')

    parser.add_argument('-g', '--gravity', action="store_true", dest="gravity",
                        help='Gravity enabled, still entities will fall to the floor')

    parser.add_argument('-rt', '--retry', action="store_true", dest="retry_on",
                        help='Whether the loop will automatically restart upon the expiry of all entities')

    parser.add_argument('-hm', '--hat-model', action="store", dest="hat_edition", type=str, default=hat_model,
                        choices=['SD', 'HD', 'MINI'], help='Whether the program is using a Unicorn Mini HAT')

    parser.add_argument('-l', '--log-level', action="store", dest="log_level", type=str, default=logging_level,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], help='Logging level')

    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    if args.hat_edition == "MINI":
        # unicorn hat mini setup
        unicorn = UnicornHATMini()
        unicorn.set_brightness(led_brightness)
        unicorn.set_rotation(0)
        u_width, u_height = unicorn.get_shape()
        # the unicorn hat led addresses are 0 indexed so need to account for this, there appears to be some weird bug
        # with the unicorn hat mini code that requires width to be offset by 2 but height by nothing
        u_width_max = u_width - 2
        u_height_max = u_height - 1
    elif args.hat_edition == "SD":
        # unicorn hat + unicorn hat hd setup
        unicorn.set_layout(unicorn.AUTO)
        unicorn.brightness(led_brightness)
        unicorn.rotation(0)
        u_width, u_height = unicorn.get_shape()
        # the unicorn hat led addresses are 0 indexed so need to account for this
        u_width_max = u_width - 1
        u_height_max = u_height - 1
    elif args.hat_edition == "HD":
        # unicorn hat + unicorn hat hd setup
        unicorn = unicornhd
        unicorn.set_layout(unicorn.AUTO)
        unicorn.brightness(led_brightness)
        unicorn.rotation(0)
        u_width, u_height = unicorn.get_shape()
        # the unicorn hat led addresses are 0 indexed so need to account for this
        u_width_max = u_width - 1
        u_height_max = u_height - 1

    # setup Minecraft connection if mc_mode is True
    if args.mc_mode:
        mc = Minecraft.create()
        mc.postToChat("PiLife Plugged into Minecraft!")

    holder = {}

    # generate life form classes
    for i in range(args.life_form_total):
        holder.update(class_generator(i))

    main(concurrent_lifeforms_max=args.pop_limit, life_form_total_count=args.life_form_total,
         draw_trails=args.trails_on,
         retries=args.retry_on, random_dna_chance=args.dna_chaos)
