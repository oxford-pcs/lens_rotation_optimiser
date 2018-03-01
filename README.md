# rotation_optimiser

Find the optimal configuration for a series of rotatable lenses in a barrel 
given their measured mount decentres, tilts and lens radii/thicknesses.

## Dependencies
- Zemax
- PyZDDE
- zController

## Overview

This program has been designed to be used on the output of the rotation analysis 
script included in the sibling repository, `measure_lens_alignment`.

Each possible rotational configuration of the full lens system is considered, 
and the merit function value calculated for each. The system with the lowest 
merit function is then chosen as the optimal solution.

## Setting up the configuration file

The configuration JSON file "config.json" contains, amongst other things, the 
necessary contextual information for the program to work. It contains the three 
main keys:

- GENERAL, 
- SYSTEM, and
- LENSES

**GENERAL** contains general information required for the program to run, 
e.g. file paths.

**SYSTEM** contains information specific to the optical system.

Each entry in **LENSES** defines a lens and contains the following keys:

- the starting surface number defining the lens (**start\_surface\_number**)
- the ending surface number defining the lens (**end\_surface\_number**)
- a lens label, e.g. "L1" for lens 1 (**label**)
- the minimum air gap between the lens and the next surface (**min\_air\_gap**)
- the maximum air gap between the lens and the next surface (**max\_air\_gap**)
- lens data (**data**)

Each **data** entry should contain two fields, **mount\_position** and **axis**. 
The first field should be a single integer number uniquely identifying the 
rotation of the lens ring. Typically this will be a number between 1 and 6. 
The second field is a list containing the decentres 
(**[xy?]\_decentre**), tilts (**[xy?]\_tilt**) and axis type (**axis\_type**). 
An axis type should be one of either "OPTICAL" or "MECHANICAL". 

Data entries should be generated using the `measure_lens_alignment` package 
using the -j flag. They can then be installed using the 
`install_measured_data.py` script by passing in a template `config.json` file.

## Running

The main execution loop is in go.py, e.g.

`python go.py -o SPOT -n -1`
