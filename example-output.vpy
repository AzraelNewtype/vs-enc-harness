import sys
import vapoursynth as vs

core = vs.get_core()

if 'src_vid' not in globals():
    sys.exit("You didn't supply a source mp4")
else:
    v_in = core.lsmas.LibavSMASHSource(src_vid)

if 'type' not in globals():
    sys.exit("You failed to supply a type to vspipe")
else:
    if type == b'hd':
        v_out = v_in
    if type == b'wr':
        v_out = core.resize.Bilinear(v_in, 854, 480, format=vs.YUV420P8, dither_type="none")
        v_out = core.scxvid.Scxvid(v_out, log="foo.stats", use_slices=True)
    if type == b'sd':
        v_out = core.resize.Bicubic(v_in, 854, 480, filter_param_a=-.5,filter_param_b=.25, 
                                format=vs.YUV420P8, dither_type="ordered", matrix_in_s="709",
                                matrix_s="470bg")
        
    if 'subtitles' in globals():
        v_out = core.assvapour.AssRender(v_out, subtitles)
    v_out.set_output(0)