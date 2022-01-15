import argparse
import logging
import random
import time

import unicornhat as unicorn
from mcpi.minecraft import Minecraft

from config.parameters import initial_lifeforms_count, speed, population_limit, max_time_to_live, max_aggression, \
    logging_level, breed_threshold, dna_chaos_chance, static_entity_chance, max_time_to_move

logger = logging.getLogger("alife-logger")

# unicorn hat setup
unicorn.set_layout(unicorn.AUTO)
unicorn.brightness(0.3)
unicorn.rotation(0)
u_width, u_height = unicorn.get_shape()

# the unicorn hat led addresses are 0 indexed so need to account for this
u_width_max = u_width - 1
u_height_max = u_height - 1


# the main class that handles each life forms initialisation, movement, colour, expiry and statistics
class LifeForm(object):

    # standard class initialisation
    def __init__(self, life_form_id, seed, seed2, seed3, start_x, start_y):
        self.life_form_id = life_form_id

        # when this function is called it gives the life form of the class instance its properties from the random
        # numbers inserted into it
        self.life_seed1 = seed
        self.life_seed2 = seed2
        self.life_seed3 = seed3
        # life seed 1 controls the random number generation for the red colour, maximum aggression factor starting
        # direction and maximum possible lifespan
        random.seed(self.life_seed1)
        self.red_color = random.randint(1, 255)
        self.max_aggression_factor = random.randint(1, max_aggro)
        self.direction_no = random.randint(1, 9)
        self.max_life = random.randint(1, max_ttl)
        # life seed 2 controls the random number generation for the green colour, aggression factor between 0 and the
        # maximum from above as well as the time the entity takes to change direction
        random.seed(self.life_seed2)
        self.green_color = random.randint(1, 255)
        self.aggression_factor = random.randint(0, self.max_aggression_factor)
        self.time_to_move = random.randint(1, max_move_limit)
        self.time_to_move_count = self.time_to_move
        # life seed 3 controls the random number generation for the green colour, and time to live between 0 and the
        # maximum from above
        random.seed(self.life_seed3)
        self.blue_color = random.randint(1, 255)
        self.time_to_live = random.randint(0, self.max_life)
        self.time_to_live_count = self.time_to_live
        self.moving_life_form_percent = random.randint(1, 100)
        if self.moving_life_form_percent < static_chance:
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

    # when called this function will display the statistics of the current life form in the main loop
    def get_stats(self):
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

    # this function will move the entity in its currently set direction (with 8 possible directions), if it hits the
    # edge of the board it will then assign a new random direction to go in, this function also handles the time to
    # move count which when hits 0 will select a new random direction for the entity regardless of whether it has hit
    # the edge of the board or another entity
    def movement(self):
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
                pass

            # minus 1 from the time to move count until it hits 0, at which point the entity will change direction from
            # the "randomise direction" function being called
            if self.time_to_move_count > 0:
                self.time_to_move_count -= 1
            elif self.time_to_move_count <= 0:
                self.time_to_move_count = self.time_to_move
                self.direction = self.randomise_direction()

    # when called this function with select a random new direction for the life form that is not the direction it is
    # already going
    def randomise_direction(self, exclusion_list=None):
        if exclusion_list is None:
            exclusion_list = []
        if self.direction not in exclusion_list:
            exclusion_list.append(self.direction)
        try:
            r = random.choice([d for d in range(1, 9) if i not in exclusion_list])
            self.direction = r
        except IndexError:
            r = False
        return r

    # this function counts down a life forms time to live from its full lifetime assigned to it when a life forms time
    # to live hits zero remove it from the list of life forms and set the colours to 0, 0, 0
    def expire_entity(self):
        if self.time_to_live_count > 0:
            self.time_to_live_count -= 1
            return False
        elif self.time_to_live_count <= 0:
            return True

    # function to call for erasing an entity from the board by fading it away as well as removing from the main list
    # for life forms
    def fade_entity(self):
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


# draw the position and colour of the current life form onto the board, if minecraft mode true, also set blocks
# relative to the player in the game world, adding 1 to the layer every iteration so that each time the current
# amount of entities is rendered it moves to another layer in minecraft, essentially building upwards
def draw_leds(x, y, r, g, b, current_layer):
    unicorn.set_pixel(x, y, r, g, b)
    if minecraft_mode:
        player_x, player_y, player_z = mc.player.getPos()
        random.seed(r + g + b)
        random_block = random.randint(1, 22)
        random.seed()
        mc.setBlock(player_x + x, player_y + 10 + current_layer, player_z + y, random_block)


# clear the unicorn hat leds
def clear_leds():
    unicorn.clear()


# function used for determining percentages of a whole number (deprecated)
def percentage(percent, whole):
    return int(round(percent * whole) / 100.0)


# function used for generating a random number to be used as a seed, this is used to generate all 3 life seeds
# resulting in 1.e+36 possible types of life form
def get_random():
    return random.randint(1, 1000000000000)


# function to randomly kill half of the entities in existence on the board
def thanos_snap():
    # loop for 50% of all existing entities choosing at random to eliminate
    for x in range(int(len(holder) / 2)):
        vanished = random.choice(holder)
        holder[vanished].fade_entity()
        time.sleep(0.1)
    logger.info("Perfectly balanced as all things should be")
    time.sleep(2)


# function used to determine whether a life form is colliding with another currently on the board
def collision_detector(life_form_id):
    # get the board positions for the current life form
    life_form_id_x = holder[life_form_id].matrix_position_x
    life_form_id_y = holder[life_form_id].matrix_position_y
    life_form_id_direction = holder[life_form_id].direction

    # for every item in the list of board positions perform a loop
    for item in list(holder):
        # split the items in the sub-list into separate variables for comparison
        s_item_life_form_id = item

        s_item_x = holder[s_item_life_form_id].matrix_position_x
        s_item_y = holder[s_item_life_form_id].matrix_position_y

        # if the x and y positions match that of a life form that is currently on the position list then return the
        # life_form_id of the life form it collided with
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

        elif life_form_id_direction == 9:
            return False

    return False


def class_generator(life_form_id):
    # assign all the life_form_ids into class instances for each life form for each life_form_id in the list of all
    # life form life_form_ids assign a random x and y number for the position on the board and create the new life
    # form with random seeds for each life seed generation
    generated_class = {
        life_form_id: LifeForm(life_form_id=life_form_id, seed=get_random(), seed2=get_random(), seed3=get_random(),
                               start_x=board_position_generator(collision_detection=True)[0],
                               start_y=board_position_generator(collision_detection=True)[1])}

    return generated_class


def board_position_generator(life_form_id=None, collision_detection=True, surrounding_area=False):
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

        if collision_detection:
            for item in list(holder):
                s_item_x = holder[item].matrix_position_x
                s_item_y = holder[item].matrix_position_y

                for pos in positions_around_life_form:
                    if not pos[0] == s_item_x and not pos[1] == s_item_y:
                        post_x_gen = pos[0]
                        post_y_gen = pos[1]

                        if post_x_gen > u_height_max or post_x_gen < 0:
                            continue

                        if post_y_gen > u_width_max or post_y_gen < 0:
                            continue

                        logger.debug(f"Free space around the entity found: X: {post_x_gen}, Y: {post_y_gen}")

                        return post_x_gen, post_y_gen

            return None
        else:
            positions = random.choice(positions_around_life_form)
            post_x_gen = positions[0]
            post_y_gen = positions[1]

            return post_x_gen, post_y_gen

    else:
        post_x_gen = random.randint(0, 7)
        post_y_gen = random.randint(0, 7)

        if collision_detection:
            x_list = [0, 1, 2, 3, 4, 5, 6, 7]
            y_list = [0, 1, 2, 3, 4, 5, 6, 7]

            random.shuffle(x_list)
            random.shuffle(y_list)

            try:
                for item in list(holder):
                    s_item_x = holder[item].matrix_position_x
                    s_item_y = holder[item].matrix_position_y
                    for x in x_list:
                        for y in y_list:
                            if not x == s_item_x and not y == s_item_y:
                                post_x_gen = x
                                post_y_gen = y
                                return post_x_gen, post_y_gen
            except NameError:
                return post_x_gen, post_y_gen
            return post_x_gen, post_y_gen

        else:
            return post_x_gen, post_y_gen


# for when a 50/50 chance needs to be calculated
def fifty_fifty():
    if random.random() < .5:
        return True
    return False


def main(concurrent_lifeforms_max, life_form_total_count, draw_trails, retries, random_dna_chance,
         highest_concurrent_lifeforms=0,
         current_layer=0):
    base_starting_number = len(holder)

    # wrap main loop into a try: to catch keyboard exit
    try:
        while True:

            # clear unicorn hat leds and clear position list
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
                    # collided with if so
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

                        attempted_directions.append(direction_attempt)

                        # find a new direction until a free space is found, 9 attempts are made then the entity will
                        # sit still until it changes direction again
                        while collision_detected_again:
                            collision_detected_again = collision_detector(life_form_id=life_form_id)

                            direction_attempt = holder[life_form_id].randomise_direction(
                                exclusion_list=attempted_directions)

                            if not direction_attempt:
                                holder[life_form_id].direction = 9
                                break

                            attempted_directions.append(direction_attempt)

                        # if the aggression factor is below 850 the life form will attempt to breed with the one it
                        # collided with
                        if holder[life_form_id].aggression_factor < breed_threshold:
                            if holder[collision_detected].aggression_factor < breed_threshold:
                                # the breeding will attempt only if the current life form count is not above the
                                # population limit
                                if current_life_form_amount < concurrent_lifeforms_max:

                                    # generate 2 random numbers for x and y positions of the new entity
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
                                    # from either parent (40% chance each), or whether a new random life seed will
                                    # be inserted (20% chance), resulting in some genetic chaos to change
                                    # offspring randomly
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

                            # if the aggression factor of both entities is life_form_identical they will reach a
                            # stalemate and simply bounce off each other
                            elif holder[collision_detected].aggression_factor == holder[life_form_id].aggression_factor:
                                logger.debug('Neither entity killed')

                    # call the movement function for the life form
                    holder[life_form_id].movement()

                    holder[life_form_id].get_stats()

                    # call function to draw leds with the current life forms x and y and r g b data, as well as the
                    # current layer
                    draw_leds(holder[life_form_id].matrix_position_x, holder[life_form_id].matrix_position_y,
                              holder[life_form_id].red_color, holder[life_form_id].green_color,
                              holder[life_form_id].blue_color, current_layer)

            # if the main list of entities is empty then all have expired; the program displays final information 
            # about the programs run and exits 
            elif not holder:
                if retries:
                    highest_concurrent_lifeforms = 0
                    current_layer = 0

                    for n in range(base_starting_number):
                        holder.update(class_generator(n))

                    continue

                else:

                    logger.info(
                        f'\n All Lifeforms have expired.\n Total life forms produced: {life_form_total_count}\n Max '
                        f'concurrent Lifeforms was: {highest_concurrent_lifeforms}\n')
                    break

            logger.debug(f"Lifeforms: {life_form_total_count}")

            # show leds
            unicorn.show()

            # time to sleep before next loop iteration, controlled from argument above
            time.sleep(time_set)

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

    parser.add_argument('-mc', '--minecraft-mode', action="store_true", dest="mc_mode",
                        help='Enables Minecraft mode')

    parser.add_argument('-tr', '--trails', action="store_true", dest="trails_on",
                        help='Stops the HAT from being cleared, resulting in trails of entities')

    parser.add_argument('-rt', '--retry', action="store_true", dest="retry_on",
                        help='Whether the loop will automatically restart upon the expiry of all entities')

    parser.add_argument('-l', '--log-level', action="store", dest="log_level", type=str, default=logging_level,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], help='Logging level')

    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)

    # total number of lifeforms to start off with
    life_form_total = args.life_form_total

    # assign the loop delay with a second argument that can be passed into python
    time_set = args.loop_speed

    # assign the population limit of life forms with a third argument that can be passed into python
    pop_limit = args.pop_limit

    # assign the max time to live possible for life forms with a fourth argument that can be passed into python
    max_ttl = args.max_ttl

    # assign the aggression factor for life forms with a fifth argument that can be passed into python
    max_aggro = args.max_aggro

    dna_chance = args.dna_chaos

    static_chance = args.static_entity

    max_move_limit = args.max_moves

    # prevents clearing of leds to enable 'trails' of lifeforms
    trails = args.trails_on

    # control retries; so if every entity expires the loop will restart and try again
    retry = args.retry_on

    minecraft_mode = args.mc_mode
    if minecraft_mode:
        mc = Minecraft.create()
        mc.postToChat("PiLife Plugged into Minecraft!")

    holder = {}

    for i in range(life_form_total):
        holder.update(class_generator(i))

    main(concurrent_lifeforms_max=pop_limit, life_form_total_count=life_form_total, draw_trails=trails,
         retries=retry, random_dna_chance=dna_chance)
