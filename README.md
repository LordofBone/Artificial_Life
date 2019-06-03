## Artificial Life

This repository has the code for the Artificial Life project as described on the [314reactor.com](https://314reactor.com/2017/10/16/artificial-life-project/) blog. The goal of the project is to use a Raspberry Pi and a [Unicorn Pi Hat](https://shop.pimoroni.com/products/unicorn-hat) to simulate a set of artificial lifeforms. Features of the program include: 

* Create a number of artificial lifeforms that can move around a board and have colour/movement properties assigned to them via 3 random numbers; the ‘DNA’ of the life-form – and display them onto an easy-to-observe output.
* Have those artificial lifeforms be able to interact with each other to ‘breed’ and pass along their traits to offspring, as well as ‘kill’ each other to keep the population in check.
* Have random chance for ‘genetic chaos’ whereby instead of passing along a life-form’s properties to its offspring a random number is inserted into the offspring’s ‘DNA’.
* BONUS – plug the code into the Minecraft API and see what random patterns of blocks can be spawned from the artificial life-form’s movements and properties.


### Installation

A more detailed set of instructions is available on the blog post for this project. Basic instructions are: 

1. Install Raspbian on an Raspberry Pi. 
2. Clone the repository
3. Install the dependencies

```

sudo pip install -r requirements.txt

```

### Running The Program

Run the program from the command line. 

```

sudo python PiLife_Ready_1_ANNOTATED.py 1 2 1 10000 1000

```

The arguments, in order, specify the following: 

1. Number of life forms to start the program
2. Amount of seconds between program loops
3. Max number of lifeforms at any given time
4. Max time to live a life form can have
5. Max agression factor a life form can have