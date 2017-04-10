# optimise_camera

This repository contains code to optimise the prototype camera barrel, taking into the measured offsets, tilts and lens radii/thicknesses.

## Setting up the configuration file

The configuration JSON file "config.json" contains, amongst other things, the necessary contextual information for the program to work. It 
contains two main keys:

- GENERAL, and
- LENSES

**GENERAL** contains general information required for the program to run, e.g. file paths.

Each entry in **LENSES** defines a lens and contains the following keys:

- the starting surface number defining the lens (**start\_surface\_number**)
- the ending surface number defining the lens (**end\_surface\_number**)
- a lens label, e.g. "L1" for lens 1 (**label**)
- the minimum air gap between the lens and the next surface (**min\_air\_gap**)
- the maximum air gap between the lens and the next surface (**max\_air\_gap**)
- lens data (**data**)

Each **data** entry should contain two fields, **mount\_position** and **axis**. The first field should be a single integer number uniquely 
identifying the rotation of the lens ring. Typically this will be a number between 1 and 6. The second field is a list containing the decentres 
(**[xy?]\_decentre**), tilts (**[xy?]\_tilt**) and axis type (**axis\_type**). An axis type should be one of either "OPTICAL" or "MECHANICAL".
