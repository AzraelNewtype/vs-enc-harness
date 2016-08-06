import os
import shlex
import subprocess
import sys
try:
    import yaml
except ImportError:
    sys.exit("You need to install PyYaml for this to work.")


def preprin(foo):
    """Debug printing. It's not worth importing always, and lazier to type as needed."""
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(foo)
    
def load_settings(series):
    try:
        script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        yaml_loc = os.path.join(script_dir,"encoder.yaml")
        with open(yaml_loc) as y:
            all_settings = yaml.load(y)
    except IOError:
        sys.exit("Cannot load encoder.yaml, cannot continue.")

    settings = all_settings['Global']
    try:
        settings.update(all_settings['Series'][series])
    except KeyError:
        print('No entry for series "{0}" in encoder.yaml, the available options are:'.format(series))
        for series in all_settings['Series']:
            print(series)
        raise SystemExit

    return settings
    
def get_vid_info(settings):
    type = settings['type']
    info_cmd =  '{0} -i -a "type={1}" -a "src_vid={2}" {3} -'.format(
        settings['vspipe'], type, settings['vid_in'], settings['script_in'])
    iargs = shlex.split(info_cmd)
    finfo_raw = subprocess.check_output(iargs)
    finfo_raw = finfo_raw.decode('utf-8')
    finfo_lines = finfo_raw.split('\n')
    finfo = {}
    for line in finfo_lines:
        parts = line.split(": ")
        if len(parts) > 1:
            finfo[parts[0]] = parts[1]
    return finfo
