#!/usr/bin/env python3

import argparse
import glob
import os
import re
import shlex
import subprocess
import sys
import tempfile


try:
    import yaml
except ImportError:
    sys.exit("You need to install PyYaml for this to work.")


class Opts(object):
    pass


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


def encode_wr(settings, ep_num, prefix, temp_name):
    cut_audio(settings, ep_num)
    #print(temp_name)
    if temp_name:
        make_chapters(settings, ep_num, temp_name, False)
        if settings["mp4chapters"]:
            make_chapters(settings, ep_num, temp_name, True)
    prepare_mode_avs(ep_num, "WR", "")
    try:
        tc_str = "--tcfile-in {0}".format(settings["tc"])
    except KeyError:
        tc_str = ""
    cmd = ("{0} {3} --qpfile {1}.qpfile --acodec copy --audiofile "
          "{1}_aud.mka -o {2}{1}wr.mkv {1}/{1}.WR.avs {4} --chapter "
          "{1}.xml".
          format(settings["x264_8"], ep_num, prefix, settings["wr_opts"],
                 tc_str))
    split_and_blind_call(cmd)


def get_vid_info(settings, ep_num, mode):
    info = [0, 0, 0, 0]
    a, tempYUV = tempfile.mkstemp()
    os.close(a)
    avs_name = "{0}/{0}.{1}.avs".format(ep_num, mode)
    frames_cmd = '"{0}"'.format(os.path.normpath(settings["avs2yuv"]))
    frames_cmd += ' -raw -frames 1 "{1}" -o "{0}"'.format(tempYUV, avs_name)

    #print(frames_cmd)
    proc = subprocess.Popen(frames_cmd, shell=True, stdout=subprocess.PIPE,
                            universal_newlines=True, stderr=subprocess.STDOUT)
    proc.wait()
    p = re.compile ('.+: ([0-9]+)x([0-9]+), ([0-9]+/[0-9]+) fps, ([0-9]+) frames')
    for line in proc.stdout:
        m = p.search(line)
        if m:
            os.unlink(tempYUV)
            return [m.group(1), m.group(2), m.group(3), m.group(4)]
    os.unlink(tempYUV)
    sys.exit('Error: Could not count number of frames.')


def encode_sd(settings, ep_num, group):
    prepare_mode_avs(ep_num, "SD", settings["script"])

    input_avs = '{0}/{0}.SD.avs'.format(ep_num)
    if settings['sd_depth_out'] == 10:
        enc = settings["x264_10"]
    else:
        enc = settings["x264_8"]

    if settings["ver"]:
        name_ep_num = "{0}v{1}".format(ep_num, settings["ver"])
    else:
        name_ep_num = ep_num


    if settings['external_mp4_muxer']:
        audio_str = ''
        out_name = '{0}sd.mp4'.format(ep_num)
    else:
        audio_str = "--acodec copy --audiofile {0}_aud.mka".format(ep_num)
        out_name = "out/[{0}] {1} - {2}SD.mp4".format(group, settings["full_name"], name_ep_num)

    if os.path.exists("{0}ch.txt".format(ep_num)) and not settings['external_mp4_muxer']:
        chaps = "--chapter {0}ch.txt".format(ep_num)
    else:
        chaps = ""

    if os.path.exists("{0}.qpfile".format(ep_num)):
        qp_str = "--qpfile {0}.qpfile".format(ep_num)
    else:
        qp_str = ""

    try:
        fps_str = " --tcfile-in {0}".format(settings["tc"])
    except KeyError:
        fps_str = ""

    if settings['sd_depth_in'] > 8 or settings['pipe_8']:
        wrapped = avs2yuv_wrap(settings, ep_num, 'SD', enc, input_avs, fps_str,
                     settings['sd_depth_in'])
        encoder_source = wrapped['wrapped_cmd']
        shell = True
    else:
        encoder_source = '{0} {1}{2}'.format(enc, input_avs, fps_str)
        shell = False

    cmd = '{0} {2} {4} {5} {3} -o "{1}"'.format(encoder_source, out_name,
                                                settings["sd_opts"].strip(),
                                                chaps, qp_str, audio_str)
    #sys.exit(cmd)
    split_and_blind_call(cmd, False, shell)


def encode_hd(settings, ep_num, group):
    prepare_mode_avs(ep_num, "HD", "")
    input_avs = "{0}/{0}.HD.avs".format(ep_num)
    if settings['hd_depth_out'] == 10:
        enc = settings["x264_10"]
    else:
        enc = settings["x264_8"]

    shell = False
    if settings['hd_depth_in'] > 8 or settings['pipe_8']:
        try:
            fps_str = "--tcfile-in {0}".format(settings["tc"])
        except KeyError:
            fps_str = None
        wrapped = avs2yuv_wrap(settings, ep_num, "HD", enc, input_avs, fps_str,
                               settings['hd_depth_in'])
        encoder_source = wrapped['wrapped_cmd']
        res = wrapped['res']
        shell = True
    else:
        frame_info = get_vid_info(settings, ep_num, 'HD')
        # We can't get to this state unless it's 8-bit input, reply is gospel
        res = "{0}x{1}".format(frame_info[0], frame_info[1])
        encoder_source = "{0} {1}".format(enc, input_avs)

    hd_opts = settings["hd_opts"].rstrip()
    cmd = "{0} {2} --qpfile {1}.qpfile -o {1}_vid.mkv".format(encoder_source, ep_num, hd_opts)
    split_and_blind_call(cmd, False, shell)
    return mux_hd_raw(ep_num, group, res)

    
def split_and_blind_call(cmd, is_python=False, is_shell=False):
    if is_shell:
        cmd = cmd.replace('/','\\\\')
    args = shlex.split(cmd)
    #print(' '.join(args))
    if is_python:
        args.insert(0, sys.executable)
    f = subprocess.Popen(args, shell=is_shell)
    f.wait()


def preprin(foo):
    """Name inspired by precure. I don't imagine keeping this around into production,
       but until that happens (lol) it's sometimes nice to have this?"""
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(foo)


if __name__ == "__main__":
    #Build the menu.
    parser = argparse.ArgumentParser(description="Commands to automate the crap out of encoding")
    parser.add_argument('series', help="Series name, corresponding to series top level in encoder.yaml")
    parser.add_argument('vid_in', help="Lossless video filename")
    parser.add_argument('enc_type', choices=["sd", "hd", "wr", "fhd"], help="Which set of encoder commands to run?")
    parser.add_argument('-d', '--depth', dest='enc_depth', type=int, choices=[8,10], help="Use standard x264 or x264-10bit?")
    parser.add_argument('--version', action='version', version='0.1')
    parser.add_argument('-s', '--script', dest="script", help="Filename of ass script. Replaces [[script]] in out template.")
    parser.add_argument('-c', '--tcfile', dest="tc", help="External timecodes file for HD/SD encodes.")
    args = parser.parse_args(namespace=Opts)

    #Grab the settings from the yaml based on input
    settings = load_settings(Opts.series)

    settings["ver"] = Opts.ver

    if Opts.tc:
        settings["tc"] = Opts.tc
    
    if Opts.epnum < 10:
        epnum = "0" + str(Opts.epnum)
    else:
        epnum = str(Opts.epnum)
    if not Opts.script:
        settings["script"] = ""
    else:
        settings["script"] = Opts.script
    if Opts.enc_type == "wr":
        if settings["default_template"] and not temp_name:
            temp_name = settings["default_template"]
        if not Opts.prefix and settings["wr_prefix"]:
            prefix = settings["wr_prefix"]
        encode_wr(settings, epnum, prefix, temp_name)
    elif Opts.enc_type == "hd":
        depth_checks("hd_depth_in", "HD source", "-d {8,10,16}", settings, Opts.source_depth)
        depth_checks("hd_depth_out", "HD encode", "-D {8,10}", settings, Opts.enc_depth)
        if not Opts.prefix and settings["hd_prefix"]:
            prefix = settings["hd_prefix"]
        encode_hd(settings, epnum, prefix)
    elif Opts.enc_type == "sd":
        depth_checks("sd_depth_in", "SD source", "-d {8,10,16}", settings, Opts.source_depth)
        depth_checks("sd_depth_out", "SD encode", "-D {8,10}", settings, Opts.enc_depth)
        if not Opts.prefix and settings["sd_prefix"]:
            prefix = settings["sd_prefix"]
        encode_sd(settings, epnum, prefix)
    elif Opts.enc_type == "fhd":
        sys.exit("Congratulations, you've specified a valid mode with no corresponding code.")
    else:
        sys.exit("You specified an invalid encode type. The options are 'wr', 'hd', 'fhd', or 'sd'.")
