import argparse
import json

def loadConfig(path):
  with open(path) as fp:
    cfg = json.load(fp)
    return cfg
  
if __name__== "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("-c", help="configuration file", default="etc/configs/config.sample.json")
  parser.add_argument("-d", help="measured data file", default="out")
  parser.add_argument("-o", help="output data file", default="etc/configs/config.sample.json.new")

  args = parser.parse_args()
   
cfg = loadConfig(args.c)
        
for idx, entry in enumerate(cfg['LENSES']):
  with open(args.d) as f:
    for line in f:
      if line.split(':')[0] == entry['label']:
        print line.split(':')[0] + " -> " + entry['label'] 
        new_data = line.split(line.split(':')[0] + ':')[1]
        cfg['LENSES'][idx]['data'] = json.loads(new_data)

with open(args.o, 'w') as outfile:  
    json.dump(cfg, outfile, indent=4, sort_keys=True)
