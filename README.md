# vs-enc-harness

A set of tools to make repetitive encoding tasks easier with VapourSynth. Mainly aimed at people who encode an episode
per week or more, all with the same exact routine.

## Getting Started
Getting off the ground with this probably won't require any complicated compiling, but will require some things, most of
which you probably already have if you have use for the tools in the first place.

### Requirements
* [Python3](https://www.python.org/downloads/) with [PyYAML](http://pyyaml.org/) installed
* [VapourSynth](http://www.vapoursynth.com)
* [MkvToolnix](https://mkvtoolnix.download)
* x264 - Windows builds available [here](komisar.gin.by) though other builds are probably also fine
* L-SMASH - Windows builds available [here](https://down.7086.in/x264_Yuuki/), only for mp4 output
* TSMuxer - Only for demuxing audio from transport streams. Only really tested with a fairly ancient version `¯\_(ツ)_/¯`
 
### Installation

These are just python scripts, so you can really cram them anywhere. Just make sure `encoder.yaml` and `videoutilities.py`
stay in the same folder as the scripts.

## Usage

### encoder.yaml

A (hopefully) human readable configuration file. The items in `Global:` are mostly required, with some only being
important to certain tools. To be specific, those are:
* `tsmuxer`: Only used by `ts_demux_audio.py`. If you aren't going to use that, you don't need to set this.
* `l-smash_bin_path`: Only used by `mux_mp4.py`. If you are only releasing matroska, you can skip this.
* `x264_extra_params`: This isn't used at all, and I should already have deleted it.
* `mkvextract`: Only used as part of `mux_mp4.py` with matroska inputs.

All paths should use forward slashes, even on windows.

Under series, the names themselves are arbitrary. This is just a method of organizing different settings. The options
under it are semi-arbitrary, in that the text before the first `_` corresponds to the *encode type* the settings are for.
Most, if not all of these are optional. They should all be, but I'm not positive enough to assert that yet.

* `*_depth_out`: Picks the encoder to use. Should be 8 or 10, but not enforced. Other numbers default to 10, not set defaults to 8.
* `*_requires_source`: Tells `encode_video.py` to halt immediately if `-i` is not set for the specified type, if yes. The line not specified means no.
* `*_mux_fonts`: Tells `mux_matroska.py` to attach the `Fonts:` to the output on yes. Omitting the line means no.
* `*_video_lang`: Language code for the video track, if supplied, as used by both `mux_matroska.py` and `mux_mp4.py`
* `*_audio_lang`: Language code for the audio track, if supplied, as used by both `mux_matroska.py` and `mux_mp4.py`
* `*_requires_subs`: Tells `encode_video.py` to halt immediately if `-s` is not set for the specified *type*.
* `*_prefix`: Adjusts the text set in `[]` at the front of the filename. This is actually probably required? Can be overriden at CLI though
* `*_suffix`: Adjusts the text after the episode number and version indicator (if any) of the filename
* `full_name`: Full name of whatever you're dealing with. The only option that does not vary by *encode type*.

The `Fonts:` section under a series is for font files to attach to matroska. If you are a fansubber who uses non-standard
fonts over and over, this is a good way to add them without thinking more than once.

$## encode_video.py

links vspipe to x264, and can handle some complex script arguments for variant encodes for you.
See **out-example.vpy** (which isn't yet committed, because I'm dumb) for an example of how that can be useful.

All of the optional arguments have fairly reasonable default values if not set, and for the cases where the configuration
yaml dictates that they should not be optional (this is user configurable) the script will boot you out before hitting the
vpy level. For instance, if you have an encode type called `sd` and set `sd_requires_subs: yes` for a series, `-s` will be
enforced. If it is set to no, or simply omitted, the process will go on with or without it.
```
usage: encode_video.py [-h] [-i VID_IN] [-d {8,10}] [--version] [-s SUBS]
                       [-c TC] [-q QPFILE] [-o VID_OUT] [--pretend]
                       series script_in enc_type

Commands to automate the crap out of encoding

positional arguments:
  series                Series name, corresponding to series top level in
                        encoder.yaml
  script_in             Name of vpy script with final processing commands
  enc_type              Which set of encoder commands to run?

optional arguments:
  -h, --help            show this help message and exit
  -i VID_IN, --source-video VID_IN
                        Lossless video filename
  -d {8,10}, --depth {8,10}
                        Use standard x264 or x264-10bit?
  --version             show program's version number and exit
  -s SUBS, --subtitles SUBS
                        Filename of ass script.
  -c TC, --tcfile TC    External timecodes file for HD/SD encodes.
  -q QPFILE, --qpfile QPFILE
                        QPFile to use.
  -o VID_OUT, --ouput VID_OUT
                        Filename to encode to.
  --pretend
```

