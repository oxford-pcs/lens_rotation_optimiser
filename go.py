import itertools
import collections
import json
import argparse

import numpy as np
import pylab as plt
import pyzdde.zdde as pyz

from MeritFunction import MeritFunction
from Controller import Controller

def lookUp(lens, mount_position, axis_type='OPTICAL'):
  for conf in cfg['LENS']:
    if conf['label'] == lens:
      for data in conf['data']:
        if data['mount_position'] == int(mount_position):
          for axis in data['axis']:
            if axis['axis_type'] == axis_type:
              return (float(axis['x_decentre']), 
                      float(axis['y_decentre']),
                      float(axis['x_tilt']),
                      float(axis['y_tilt']))


def go(args, cfg):
  zmx_link = pyz.createLink() # DDE link object
  zcontroller = Controller(zmx_link)
  
  zcontroller.loadFile(cfg['GENERAL']['zmx_file'])
  
  # first, we label all lens surfaces with the corresponding 
  # comments so we can find them later when the numbering changes.
  #
  for entry in cfg['LENS']:
    for surf in range(entry['start_surface_number'], entry['end_surface_number']+1):
      zcontroller.setComment(int(surf), str(entry['label']), append=True)    

  # add tilts and decentres, keep track of coordinate breaks and dummy surface 
  # numbers that we will need to change later. note that the offset will only 
  # be correct if the zcontroller lens numbers are monotonically increasing. #FIXME
  offset = 0
  coordinate_break_surface_numbers = {}
  dummy_surface_numbers = {}
  for entry in cfg['LENS']:
    start_surface_number = entry['start_surface_number'] + offset
    end_surface_number = entry['end_surface_number'] + offset
    label = str(entry['label'])
    # initialise the relevant tilt/decentre coordinate breaks
    cb1, cb2, dummy = zcontroller.addTiltAndDecentre(start_surface_number, 
                                                   end_surface_number, 
                                                   x_decentre=0.,
                                                   y_decentre=0., 
                                                   x_tilt=0., 
                                                   y_tilt=0.)
    coordinate_break_surface_numbers[label] = int(cb1)
    dummy_surface_numbers[label] = int(dummy)
    offset = offset + 2 + (end_surface_number-start_surface_number)
    
  # set the thickness surfaces as variable
  for k, v in dummy_surface_numbers.iteritems():
    zcontroller.setThicknessSolveVariable(v)
    
  mf_spot_path = cfg['GENERAL']['mf_dir'] + "SPOT.MF"
  mf_wave_path = cfg['GENERAL']['mf_dir'] + "WAVE.MF"
  if args.mf:
    # next, we make a default SPOT merit function
    MF = MeritFunction(zmx_link, zcontroller, cfg['GENERAL']['zpl_path'], 
                      cfg['GENERAL']['zpl_filename'])
    MF.createDefaultMF()    
      
    # delete the comment, add air gap constraints, dummy surface holds the gap 
    # information now (post tilt and decentre)
    #
    ins_row_number = MF.getRowNumberFromMFContents('BLNK', 'No air or glass constraints.')
    zcontroller.delMFOperand(ins_row_number)
      
    for entry in cfg['LENS']:
      MF.setAirGapConstraints(ins_row_number, dummy_surface_numbers[entry['label']], 
                              entry['min_air_gap'], entry['max_air_gap'])
    zcontroller.saveMF(mf_spot_path)
 
    # next, we make a default WAVE merit function
    MF = MeritFunction(zmx_link, zcontroller, cfg['GENERAL']['zpl_path'], 
                      cfg['GENERAL']['zpl_filename'])
    MF.createDefaultMF(data=0)    
      
    # delete the comment, add air gap constraints, dummy surface holds the gap 
    # information now (post tilt and decentre)
    #
    ins_row_number = MF.getRowNumberFromMFContents('BLNK', 'No air or glass constraints.')
    zcontroller.delMFOperand(ins_row_number)
      
    for entry in cfg['LENS']:
      MF.setAirGapConstraints(ins_row_number, dummy_surface_numbers[entry['label']], 
                              entry['min_air_gap'], entry['max_air_gap'])
    zcontroller.saveMF(mf_wave_path)

  # Finally, we can go through the various permutations of tilts/decentres and 
  # evaluate the MF for each
  zcontroller.loadMF(mf_spot_path)
  lens_configurations = []
  nLenses = 0
  for lens in cfg['LENS']:
    nLenses+=1
    for data in lens['data']:
      lens_configurations.append(str(lens['label']) + '_' + str(data['mount_position']))
   
  a = [x for x in itertools.combinations(lens_configurations, nLenses)]
  nodup = []
  for entry in a:
    counter=collections.Counter([b.split('_')[0] for b in entry])
    if counter.most_common(1)[0][1] == 1:
      nodup.append(entry)

  mf_values = []
  for index, entry in enumerate(nodup):
    for configuration in entry:
      lens = configuration.split('_')[0]
      mount_position = configuration.split('_')[1]
      x_dc, y_dc, x_tilt, y_tilt = lookUp(lens, mount_position)
    
      zcontroller.setSurfaceDecentreX(coordinate_break_surface_numbers[lens], x_dc)
      zcontroller.setSurfaceDecentreY(coordinate_break_surface_numbers[lens], y_dc)
      zcontroller.setSurfaceTiltX(coordinate_break_surface_numbers[lens], x_tilt)
      zcontroller.setSurfaceTiltY(coordinate_break_surface_numbers[lens], y_tilt)
    
    zcontroller.DDEToLDE()   
    mf_value = zcontroller.optimise(nCycles=0) # not optimising
    mf_values.append(mf_value)
    print index, mf_value
    
  best_index = np.argmin(mf_values)
    
  plt.plot(mf_values, 'kx')
  plt.show()
  for configuration in nodup[best_index]:
    lens = configuration.split('_')[0]
    mount_position = configuration.split('_')[1]
    x_dc, y_dc, x_tilt, y_tilt = lookUp(lens, mount_position)
    print lens, mount_position, lookUp(lens, mount_position)

    zcontroller.setSurfaceDecentreX(coordinate_break_surface_numbers[lens], x_dc)
    zcontroller.setSurfaceDecentreY(coordinate_break_surface_numbers[lens], y_dc)
    zcontroller.setSurfaceTiltX(coordinate_break_surface_numbers[lens], x_tilt)
    zcontroller.setSurfaceTiltY(coordinate_break_surface_numbers[lens], y_tilt)
  zcontroller.DDEToLDE() 
  print zcontroller.optimise(nCycles=0) # not optimising

  '''mf_value = zcontroller.optimise(nCycles=2)  
  mf_value = zcontroller.optimise(nCycles=-1)
  print mf_value, '\t',  zcontroller.getThickness(20), '\t',  zcontroller.getThickness(25), '\t',  zcontroller.getThickness(30), '\t',  zcontroller.getThickness(35), '\t',  zcontroller.getThickness(41)
  mf_value = zcontroller.optimise(nCycles=10000)
  print mf_value, '\t',  zcontroller.getThickness(20), '\t',  zcontroller.getThickness(25), '\t',  zcontroller.getThickness(30), '\t',  zcontroller.getThickness(35), '\t',  zcontroller.getThickness(41)
  zcontroller.DDEToLDE()'''
  
  pyz.closeLink()
  
if __name__== "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-c", help="configuration file", default="config.json")
  parser.add_argument("-n", help="number of optimise iterations", default=0)
  parser.add_argument("-mf", help="make merit functions", action='store_true')
  args = parser.parse_args()
  
  with open(args.c) as fp:
    cfg = json.load(fp)
    
  go(args, cfg)
  
      

