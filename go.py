import itertools
import collections
import argparse
import json

import numpy as np
import pylab as plt
import pyzdde.zdde as pyz

from zemax_controller.MeritFunction import MeritFunction
from zemax_controller.Controller import Controller

def loadConfig(path):
  with open(path) as fp:
    cfg = json.load(fp)
    return cfg
  
def lookUpLensAxisDataFromConfig(cfg, lens, mount_position, axis_type='OPTICAL'):
  '''
    Look up lens axis data (decentres, tilts) from config given a lens name, 
    mount position and axis type.
  '''
  for conf in cfg['LENSES']:
    if conf['label'] == lens:
      for data in conf['data']:
        if data['mount_position'] == int(mount_position):
          for axis in data['axis']:
            if axis['axis_type'] == axis_type:
              return (float(axis['x_decentre']), 
                      float(axis['y_decentre']),
                      float(axis['x_tilt']),
                      float(axis['y_tilt']))
            
def lookUpLensEntryFromConfig(cfg, lens):
  '''
    Return lens entry from config given lens name.
  '''
  for conf in cfg['LENSES']:
    if conf['label'] == lens:
      return conf
    else:
      continue
    return None

class goErrorException(Exception):
  def __init__(self, message, error):
    super(Exception, self).__init__(message)
    self.errors = error

def go(args, cfg):
  zmx_link = pyz.createLink()
  zcontroller = Controller(zmx_link)
  
  print "Loading file " + cfg['GENERAL']['zmx_file']
  zcontroller.loadZemaxFile(cfg['GENERAL']['zmx_file'])
  
  # Label all lens surfaces with comments for easier identification.
  print "Adding surface comments."
  for lens in cfg['LENSES']:
    for surf in range(lens['start_surface_number'], 
                      lens['end_surface_number']+1):
      zcontroller.setSurfaceComment(int(surf), str(lens['label']), append=True)    
      
  # Set variable solves for detector, if requested.
  #
  # distance
  if cfg['SYSTEM']['variable_detector_surface_distance']:
    print "Setting detector distance as variable."
    zcontroller.setSurfaceThicknessSolveVariable(
      cfg['SYSTEM']['detector_surface_number'])
    
  # decentre
  if cfg['SYSTEM']['variable_detector_surface_decentre']:
    print "Setting detector decentre as variable."
    zcontroller.setSolveCoordBreakDecentres(
      cfg['SYSTEM']['detector_surface_number'],
      solve_type=1)
    
  # tilt
  if cfg['SYSTEM']['variable_detector_surface_tilt']:
    print "Setting detector tilt as variable."
    zcontroller.setSolveCoordBreakTilts(
      cfg['SYSTEM']['detector_surface_number'],
      solve_type=1)  
    
  # Add tilts and decentres.
  # 
  # Need to keep track of the first coordinate break surfaces and dummy surface
  # numbers. 
  # The former contains information pertaining to the tilts and decentres, the 
  # latter the air gap spacing.
  #
  
  # First make sure that the lenses in the config file are in monotonically 
  # increasing order.
  #
  lenses = {}
  for lens in cfg['LENSES']:
    lenses[lens['label']] = int(lens['start_surface_number'])
  lenses_sorted = sorted(lenses, key=lenses.get)

  # Now add the required surfaces.
  #
  offset = 0  # how much we need to offset the surface number
  coordinate_break_surface_numbers = {} # tilts, decentres
  dummy_surface_numbers = {}            # air gaps
  print "Adding coordinate breaks."
  for lens in lenses_sorted:
    this_lens_entry = lookUpLensEntryFromConfig(cfg, lens)
    start_surface_number = this_lens_entry['start_surface_number'] + offset
    end_surface_number = this_lens_entry['end_surface_number'] + offset
    label = str(this_lens_entry['label'])
    z_pivot = float(this_lens_entry['z_pivot'])
    
    # Initialise the relevant tilt/decentre coordinate breaks
    #
    # cb1 = coord changing surface number, 
    # cb2 = return surface number (PICKUP), 
    # dummy = air gap surface number.
    #
    cb1, cb2, dummy = zcontroller.addTiltAndDecentreAboutPivot(
      start_surface_number, 
      end_surface_number, 
      z_pivot,
      x_c=0.,
      y_c=0., 
      x_tilt=0., 
      y_tilt=0.)
    coordinate_break_surface_numbers[label] = int(cb1)
    dummy_surface_numbers[label] = int(dummy)
    offset = offset + 3 + (end_surface_number-start_surface_number)
    
  # Set variable solves for lenses, if requested.
  #
  # air gaps
  if cfg['SYSTEM']['variable_air_gaps']:
    print "Setting air gaps as variable."
    for k, v in dummy_surface_numbers.iteritems():
      zcontroller.setSurfaceThicknessSolveVariable(v)
    
  # decentres
  if cfg['SYSTEM']['variable_lens_decentres']:
    print "Setting lens decentres as variable."
    for k, v in coordinate_break_surface_numbers.iteritems():
      zcontroller.setSolveCoordBreakDecentres(v, solve_type=1)
  # tilts
  if cfg['SYSTEM']['variable_lens_tilts']:
    print "Setting lens tilts as variable."
    for k, v in coordinate_break_surface_numbers.iteritems():
      zcontroller.setSolveCoordBreakTilts(v, solve_type=1)
      
  # Next we make the Merit Functions, if requested. If not, the existing merit 
  # functions at the predefined locations below will be used.
  #
  MF = MeritFunction(zmx_link, zcontroller, cfg['GENERAL']['zpl_path'], 
                    cfg['GENERAL']['zpl_filename'])
  if args.o == 'SPOT':
    print "Creating merit function for optimising SPOT SIZE."
    MF.createDefaultMF()         # optimise for SPOT SIZE
  elif args.o == 'WAVE':
    print "Creating merit function for optimising WAVEFRONT."
    MF.createDefaultMF(data=0)   # optimise for WAVEFRONT
  else:
    raise goErrorException("Couldn't recognise optimiser argument.", 1)
    
  # Delete the air gap comment, add new constraints and save it.
  ins_row_number = MF.getRowNumberFromMFContents('BLNK', 'No air or glass \
                                                 constraints.')
  MF.delMFOperand(ins_row_number)
  print "Setting air gap constraints."
  for lens in cfg['LENSES']:
    MF.setAirGapConstraints(ins_row_number, 
                            dummy_surface_numbers[lens['label']], 
                            lens['min_air_gap'], lens['max_air_gap'])

  # Finally, we can go through the various combinations of tilts/decentres and 
  # optimise (optional) and evaluate the MF for each.
  #
  # First step of this process is to get all possible combinations of the 
  # lenses in the barrel
  #
  lens_configurations = []
  n_lenses = 0
  for lens in cfg['LENSES']:
    n_lenses+=1
    for data in lens['data']:
      lens_configurations.append(str(lens['label']) + '_' + 
                                 str(data['mount_position']))
  all_mount_combinations = [x for x in itertools.combinations(
    lens_configurations, 
    n_lenses)]
  
  # Then we remove entries where a lens has been used more than once
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
  combinations = []
  for index, combination in enumerate(all_mount_combinations_nodup):
    for entry in combination:
      lens = entry.split('_')[0]
      mount_position = entry.split('_')[1]
      x_dc, y_dc, x_tilt, y_tilt = lookUpLensAxisDataFromConfig(cfg, 
                                                                lens, 
                                                                mount_position)
      
      # Set the corresponding decentres and tilts, if requested.
      if cfg['SYSTEM']['use_decentres']:
        zcontroller.setCoordBreakDecentreX(
          coordinate_break_surface_numbers[lens], 
          x_dc)
        zcontroller.setCoordBreakDecentreY(
          coordinate_break_surface_numbers[lens], 
          y_dc)
      if cfg['SYSTEM']['use_tilts']:
        zcontroller.setCoordBreakTiltX(coordinate_break_surface_numbers[lens], 
                                       x_tilt)
        zcontroller.setCoordBreakTiltY(coordinate_break_surface_numbers[lens], 
                                       y_tilt)
    
    zcontroller.DDEToLDE()   
    mf_value = zcontroller.doOptimise(nCycles=args.n)
    mf_values.append(mf_value)
    combinations.append(combination)
    
    print "Combination number:\t" + str(index) 
    print "Combination:\t\t" + ', '.join(combination)
    print "MF value:\t\t" + str(round(mf_value,4))
    print
    
  best_mf_index = np.argmin(mf_values)
  print "Best merit function index:\t" + str(best_mf_index)
  print "Best merit function value:\t" + str(mf_values[best_mf_index])
  print "Best combination:\t\t" + ', '.join(combinations[best_mf_index])
  
  # Plot result if requested.
  if args.p:
    plt.plot(mf_values, 'kx')
    plt.xlabel("Iteration number")
    plt.ylabel("MF value")
    plt.show()
    
  # Update the LDE with the best configuration.
  for configuration in all_mount_combinations_nodup[best_mf_index]:
    lens = configuration.split('_')[0]
    mount_position = configuration.split('_')[1]
    x_dc, y_dc, x_tilt, y_tilt = lookUpLensAxisDataFromConfig(cfg, 
                                                              lens, 
                                                              mount_position)

    if cfg['SYSTEM']['use_decentres']:
      zcontroller.setCoordBreakDecentreX(coordinate_break_surface_numbers[lens], 
                                         x_dc)
      zcontroller.setCoordBreakDecentreY(coordinate_break_surface_numbers[lens], 
                                         y_dc)
    if cfg['SYSTEM']['use_tilts']:
      zcontroller.setCoordBreakTiltX(coordinate_break_surface_numbers[lens], 
                                     x_tilt)
      zcontroller.setCoordBreakTiltY(coordinate_break_surface_numbers[lens], 
                                     y_tilt)
  zcontroller.DDEToLDE() 
  zcontroller.doOptimise(nCycles=args.n)
  
  pyz.closeLink()
  
if __name__== "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-c", help="configuration file", default="config.sample.json.new")
  parser.add_argument("-o", help="optimise for spot size or wavefront? (SPOT||WAVE)", default='SPOT')
  parser.add_argument("-n", help="number of optimise iterations. (0=auto, -1=none)", default=-1, type=int)
  parser.add_argument("-p", help="plot?", action='store_true')
  
  args = parser.parse_args()
   
  go(args, loadConfig(args.c))
  
      

