import itertools
import collections
import argparse

import numpy as np
import pylab as plt
import pyzdde.zdde as pyz

from MeritFunction import MeritFunction
from Controller import Controller
from util import *

class goErrorException(Exception):
  def __init__(self, message, error):
    super(Exception, self).__init__(message)
    self.errors = error

def go(args, cfg):
  zmx_link = pyz.createLink() # DDE link object
  zcontroller = Controller(zmx_link)
  
  zcontroller.loadFile(cfg['GENERAL']['zmx_file'])
  
  # First, label all lens surfaces with comments for easier identification.
  print "Adding surface comments."
  for lens in cfg['LENSES']:
    for surf in range(lens['start_surface_number'], lens['end_surface_number']+1):
      zcontroller.setComment(int(surf), str(lens['label']), append=True)    

  # Add tilts and decentres.
  # 
  # Need to keep track of the first coordinate break surfaces and dummy surface numbers. 
  # The former contains information pertaining to the tilts and decentres, the latter the 
  # air gap spacing.
  #
  
  # First make sure that the lenses in the config file are in monotonically increasing 
  # order.
  #
  lenses = {}
  for lens in cfg['LENSES']:
    lenses[lens['label']] = int(lens['start_surface_number'])
  lenses_sorted = sorted(lenses, key=lenses.get)

  # Now add the required surfaces.
  #
  offset = 0  # this variable keeps track of how much we need to offset the surface number
  coordinate_break_surface_numbers = {} # tilts, decentres
  dummy_surface_numbers = {}            # air gaps
  print "Adding coordinate breaks."
  for lens in lenses_sorted:
    this_lens_entry = lookUpLensEntryFromConfig(cfg, lens)
    start_surface_number = this_lens_entry['start_surface_number'] + offset
    end_surface_number = this_lens_entry['end_surface_number'] + offset
    label = str(this_lens_entry['label'])
    
    # Initialise the relevant tilt/decentre coordinate breaks
    #
    # cb1 = coord changing surface number, 
    # cb2 = return surface number (PICKUP), 
    # dummy = air gap surface number.
    #
    cb1, cb2, dummy = zcontroller.addTiltAndDecentre(start_surface_number, 
                                                   end_surface_number, 
                                                   x_decentre=0.,
                                                   y_decentre=0., 
                                                   x_tilt=0., 
                                                   y_tilt=0.)
    coordinate_break_surface_numbers[label] = int(cb1)
    dummy_surface_numbers[label] = int(dummy)
    offset = offset + 2 + (end_surface_number-start_surface_number)
    
  # Set the thickness of the dummy surfaces as variable if requested.
  if args.va:
    print "Setting air gaps as variable."
    for k, v in dummy_surface_numbers.iteritems():
      zcontroller.setSurfaceAsThicknessSolveVariable(v)
  
  # Next we make the Merit Functions, if requested. If not, the existing merit functions 
  # at the predefined locations below will be used.
  #
  MF = MeritFunction(zmx_link, zcontroller, cfg['GENERAL']['zpl_path'], 
                    cfg['GENERAL']['zpl_filename'])
  if args.mfo == 'SPOT':
    print "Creating merit function for optimising SPOT SIZE."
    MF.createDefaultMF()         # optimise for SPOT SIZE
  elif args.mfo == 'WAVE':
    print "Creating merit function for optimising WAVEFRONT."
    MF.createDefaultMF(data=0)   # optimise for WAVEFRONT
  else:
    raise goErrorException("Couldn't recognise optimiser argument.", 1)
    
  # Delete the air gap comment, add new constraints and save it.
  ins_row_number = MF.getRowNumberFromMFContents('BLNK', 'No air or glass constraints.')
  MF.delMFOperand(ins_row_number)
  print "Setting air gap constraints."
  for lens in cfg['LENSES']:
    MF.setAirGapConstraints(ins_row_number, dummy_surface_numbers[lens['label']], 
                            lens['min_air_gap'], lens['max_air_gap'])

  # Finally, we can go through the various combinations of tilts/decentres and 
  # optimise (optional) and evaluate the MF for each.
  #
  # First step of this process is to get all combinations, including those that have 
  # multiple entries for the same lens.
  #
  lens_configurations = []
  n_lenses = 0
  for lens in cfg['LENSES']:
    n_lenses+=1
    for data in lens['data']:
      lens_configurations.append(str(lens['label']) + '_' + str(data['mount_position']))
  all_mount_combinations = [x for x in itertools.combinations(lens_configurations, 
                                                              n_lenses)]
  
  # Then we remove these duplicates.
  #
  all_mount_combinations_nodup = []
  for comb in all_mount_combinations:
    counter=collections.Counter([entry.split('_')[0] for entry in comb])
    if counter.most_common(1)[0][1] == 1:
      all_mount_combinations_nodup.append(comb)

  # And optimise/evaluate the MF for each.
  #
  print "Beginning optimisation/evaluation of merit functions."
  mf_values = []
  for index, combination in enumerate(all_mount_combinations_nodup):
    for entry in combination:
      lens = entry.split('_')[0]
      mount_position = entry.split('_')[1]
      x_dc, y_dc, x_tilt, y_tilt = lookUpLensAxisDataFromConfig(cfg, 
                                                                lens, 
                                                                mount_position)
      
      # Set the corresponding decentres and tilts.
      zcontroller.setCoordBreakDecentreX(coordinate_break_surface_numbers[lens], x_dc)
      zcontroller.setCoordBreakDecentreY(coordinate_break_surface_numbers[lens], y_dc)
      zcontroller.setCoordBreakTiltX(coordinate_break_surface_numbers[lens], x_tilt)
      zcontroller.setCoordBreakTiltY(coordinate_break_surface_numbers[lens], y_tilt)
    
    zcontroller.DDEToLDE()   
    mf_value = zcontroller.optimise(nCycles=args.n) # not optimising
    mf_values.append(mf_value)
    
    print "Combination number:\t" + str(index) 
    print "Combination:\t\t" + ', '.join(combination)
    print "MF value:\t\t" + str(round(mf_value,4))
    print
    
  best_mf_index = np.argmin(mf_values)
  print "Best merit function index:\t" + str(best_mf_index)
  print "Best merit function value:\t" + str(mf_values[best_mf_index])
  
  # Plot result if requested.
  if args.p:
    plt.plot(mf_values, 'kx')
    plt.xlabel("Iteration number")
    plt.ylabel("MF value")
    plt.show()
    
  # Update the LDE with the best configuration.
  for configuration in nodup[best_mf_index]:
    lens = configuration.split('_')[0]
    mount_position = configuration.split('_')[1]
    x_dc, y_dc, x_tilt, y_tilt = lookUpLensAxisDataFromConfig(lens, mount_position)

    zcontroller.setCoordBreakDecentreX(coordinate_break_surface_numbers[lens], x_dc)
    zcontroller.setCoordBreakDecentreY(coordinate_break_surface_numbers[lens], y_dc)
    zcontroller.setCoordBreakTiltX(coordinate_break_surface_numbers[lens], x_tilt)
    zcontroller.setCoordBreakTiltY(coordinate_break_surface_numbers[lens], y_tilt)
  zcontroller.DDEToLDE() 
  zcontroller.optimise(nCycles=args.n)
  
  pyz.closeLink()
  
if __name__== "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-c", help="configuration file", default="config.json")
  parser.add_argument("-n", help="number of optimise iterations. (0=auto, -1=none)", default=-1)
  parser.add_argument("-p", help="plot?", action='store_true')
  parser.add_argument("-mfo", help="optimise for spot size or wavefront? (SPOT||WAVE)", default='SPOT')
  parser.add_argument("-va", help="set air gaps variable?", action='store_true')

  args = parser.parse_args()
   
  go(args, loadConfig(args.c))
  
      

