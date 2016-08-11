import os
import shlex
import subprocess
import sys
import tempfile
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
        print("Cannot load encoder.yaml, cannot continue.", file=sys.stderr)
        raise

    settings = all_settings['Global']
    try:
        settings.update(all_settings['Series'][series])
    except KeyError:
        err_str_1 = 'No entry for series "{0}" in encoder.yaml, the available options are: '.format(series)
        err_str_2 = ', '.join(all_settings['Series'])
        print(err_str_1+err_str_2, file=sys.stderr)
        raise 

    return settings
    
    
def load_global_settings():
    try:
        script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        yaml_loc = os.path.join(script_dir,"encoder.yaml")
        with open(yaml_loc) as y:
            all_settings = yaml.load(y)
    except IOError:
        print("Cannot load encoder.yaml, cannot continue.", file=sys.stderr)
        raise
        
    return all_settings['Global']
    
    
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
    
    
def get_arbitrary_vid_info(settings):
    vload_str = "import vapoursynth as vs\nc = vs.get_core()\nv_in = c.lsmas.LWLibavSource(src_vid, cache=1)\nv_in.set_output()"
    try:
        old_script = settings['script_in']
    except KeyError:
        old_script = None
    if os.sep in settings['vid_in']:
        settings['vid_in'] = os.path.normpath(settings['vid_in'])
    else:
        settings['vid_in'] = os.path.abspath(settings['vid_in'])
    try:
        vload = tempfile.NamedTemporaryFile('w+', delete=False)
        vload.write(vload_str)
        vload.close()
        if os.name == 'nt':
            settings['script_in'] = fix_windows_paths(vload.name)
        else:
            settings['script_in'] = vload.name
        finfo = get_vid_info(settings)
    finally:
        os.unlink(vload.name)
    settings['script_in'] = old_script
    return finfo

    
def fix_windows_paths(path_in):
    if path_in:
        return path_in.replace('\\', '/')

def display_windows_paths(cmd_in):
    return cmd_in.replace('/', '\\')
