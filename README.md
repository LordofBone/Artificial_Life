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

Install and set up the Unicorn HAT:
[Unicorn HAT GitHub code](https://github.com/pimoroni/unicorn-hat)

You can also use this with the Unicorn HAT Mini:
[Unicorn HAT Mini GitHub code](https://learn.pimoroni.com/article/getting-started-with-unicorn-hat-mini)

Or even the Unicorn HAT HD:
[Unicorn HAT HD GitHub code](https://github.com/pimoroni/unicorn-hat-hd)

```

sudo pip install -r requirements.txt

```

### Running The Program

Run the program from the command line - for some reason I have found that it requires sudo to work with the HAT.
It will default to use the original Unicorn HAT, but if you add in the parameter '-uh' you can then specify between
SD, HD or MINI.

This will also run on a system without a physical HAT installed thanks to the 
[Unicorn HAT simulator](https://github.com/jayniz/unicorn-hat-sim) - although it does have some bugs at the moment.


```

sudo env PATH="$PATH" python artificial_life.py

```

Arguments that can be passed: 

```
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
  -ct COMBINE_THRESHOLD, --combine-threshold COMBINE_THRESHOLD
                        If a life form collides with another and both of their
                        aggression levels are within this range and combining
                        is enabled, they will combine (move together)
  -c, --combine-mode    Enables life forms to combine into bigger ones
  -mc, --minecraft-mode
                        Enables Minecraft mode
  -tr, --trails         Stops the HAT from being cleared, resulting in trails
                        of entities
  -g, --gravity         Gravity enabled, still entities will fall to the floor
  -rt, --retry          Whether the loop will automatically restart upon the
                        expiry of all entities
  -hm {SD,HD,MINI}, --hat-model {SD,HD,MINI}
                        Whether the program is using a Unicorn Mini HAT
  -l {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}, --log-level {CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET}
                        Logging level
```