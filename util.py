import json

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
          
def loadConfig(path):
  with open(path) as fp:
    cfg = json.load(fp)
    return cfg
