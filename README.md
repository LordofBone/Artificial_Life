## Artificial Life

This repository has the code for the Artificial Life project as described on the 
[314reactor.com](https://314reactor.com/2017/10/16/artificial-life-project/) blog. 
The goal of the project is to use a Raspberry Pi and a [Unicorn Pi Hat](https://shop.pimoroni.com/products/unicorn-hat) 
to simulate a set of artificial lifeforms. Features of the program include: 

* Create a number of artificial lifeforms that can move around a board and have colour/movement properties assigned to 
* them via 3 random numbers; the ‘DNA’ of the life-form – and display them onto an easy-to-observe output.
* Have those artificial lifeforms be able to interact with each other to ‘breed’ and pass along their traits to offspring, 
* as well as ‘kill’ each other to keep the population in check.
* Have random chance for ‘genetic chaos’ whereby instead of passing along a life-form’s properties to its offspring a 
* random number is inserted into the offspring’s ‘DNA’.
* BONUS – plug the code into the Minecraft API and see what random patterns of blocks can be spawned from the 
* artificial life-form’s movements and properties.


### Installation

A more detailed set of instructions is available on the blog post for this project. Basic instructions are: 

1. Install Raspbian on a Raspberry Pi. 
2. Clone the repository
3. Install the dependencies

```

Install and setup the Unicorn HAT:
https://github.com/pimoroni/unicorn-hat

sudo pip install -r requirements.txt

```

### Running The Program

Run the program from the command line. 

```

sudo env PATH="$PATH" python artificial_life.py

```

Arguments that can be passed: 

  -ilc LIFE_FORM_TOTAL, --initial-lifeforms-count LIFE_FORM_TOTAL
                        Number of lifeforms to start with
  -s LOOP_SPEED, --speed LOOP_SPEED
                        Time for the loop delay, essentially the game-speed
                        (although, lower; faster)
  -p POP_LIMIT, --population-limit POP_LIMIT
                        Limit of the population at any one time
  -ttl MAX_TTL, --max-ttl MAX_TTL
                        Maximum time to live possible for life forms
  -ma MAX_AGGRO, --max-aggression MAX_AGGRO
                        Maximum aggression factor possible for life forms
  -dc DNA_CHAOS, --dna-chaos DNA_CHAOS
                        Percentage chance of random DNA upon breeding of
                        entities
  -se STATIC_ENTITY, --static-entity STATIC_ENTITY
                        Percentage chance of an entity being static
  -mt MAX_MOVES, --max-move-time MAX_MOVES
                        Maximum possible time to move number for entities
  -mc, --minecraft-mode
                        Enables Minecraft mode
  -tr, --trails         Stops the HAT from being cleared, resulting in trails
                        of entities
  -rt, --retry          Whether the loop will automatically restart upon the
                        expiry of all entities
  -l {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}, --log-level {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}
                        Logging level