# -*- coding: utf-8 -*-
# cli.py

# Copyright (c) 2014-?, Matěj Týč
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# * Neither the name of the copyright holders nor the names of any
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
FFT based image registration. --- CLI frontend
"""

import sys
import argparse as ap

import imreg_dft as ird


def _float_tuple(st):
    vals = st.split(",")
    if len(vals) != 2:
        raise ap.ArgumentTypeError("'%s' are not two values delimited by comma"
                                   % st)
    try:
        vals = [float(val) for val in vals]
    except ValueError:
        raise ap.ArgumentTypeError("%s are not two float values" % vals)
    return vals


def main():
    parser = ap.ArgumentParser()
    parser.add_argument('template')
    parser.add_argument('image')
    parser.add_argument('--show', action="store_true", default=False,
                        help="Whether to show registration result")
    parser.add_argument('--lowpass', type=_float_tuple, action="append",
                        default=[], metavar="HI_THRESH,LOW_THRESH",
                        help="1,1 means no-op, 0.9,0.8 is a mild filter")
    parser.add_argument('--highpass', type=_float_tuple, action="append",
                        default=[], metavar="HI_THRESH,LOW_THRESH",
                        help="0,0 means no-op, 0.2,0.1 is a mild filter")
    parser.add_argument('--extend', type=int, metavar="PIXELS", default=0,
                        help="Extend images by the specified amount of pixels "
                        "before the processing (thus eliminating edge effects)")
    parser.add_argument('--order', type=int, default=1,
                        help="Interpolation order (1 = linear, 3 = cubic etc.)")
    parser.add_argument(
        '--filter-pcorr', type=int, default=0,
        help="Whether to filter during translation detection. Normally not "
        "needed, but when using low-pass filtering, you may need to increase "
        "filter radius (0 means no filtering, 4 should be enough)")
    parser.add_argument('--print-result', action="store_true", default=False,
                        help="")
    parser.add_argument(
        '--print-format', default="scale: %(scale)f\nangle: %(angle)f\nshift: "
        "%(tx)d, %(ty)d\n",
        help="Print a string (to stdout) in a given format. A dictionary "
        "containing the 'scale', 'angle', 'tx' and 'ty' keys will be "
        "passed for interpolation")
    parser.add_argument('--version', action="version",
                        version="imreg_dft %s" % ird.__version__,
                        help="Just print version and exit")
    args = parser.parse_args()
    print_format = args.print_format
    if not args.print_result:
        print_format = None

    opts = dict(
        order=args.order,
        filter_pcorr=args.filter_pcorr,
        extend=args.extend,
        low=args.lowpass,
        high=args.highpass,
        show=args.show,
        print_format=print_format,
    )
    run(args.template, args.image, opts)


def filter_images(ims, low, high):
    from imreg_dft import utils

    ret = [utils.filter(im, low, high) for im in ims]
    return ret


def apodize(ims, radius_ratio):
    import numpy as np
    from imreg_dft import utils

    ret = []
    # They might have different shapes...
    for im in ims:
        shape = im.shape

        bgval = np.median(im)
        bg = np.ones(shape) * bgval

        radius = radius_ratio * min(shape)
        apofield = utils.get_apofield(shape, radius)

        bg *= (1 - apofield)
        # not modifying inplace
        toapp = bg + im * apofield
        ret.append(toapp)
    return ret


def run(template, image, opts):
    import numpy as np
    from scipy import misc

    from imreg_dft import utils
    from imreg_dft import imreg

    ims = [misc.imread(fname, True) for fname in (template, image)]
    bigshape = np.array([im.shape for im in ims]).max(0)
    ims = [utils.extend_by(im, opts["extend"]) for im in ims]
    ims = filter_images(ims, opts["low"], opts["high"])
    # We think that im[0, 0] has the right value after apodization
    ims = [utils.embed_to(np.zeros(bigshape) + im[0, 0], im) for im in ims]

    im2, scale, angle, (t0, t1) = imreg.similarity(
        ims[0], ims[1], opts["order"], opts["filter_pcorr"])

    tform = dict(scale=scale, angle=angle, tx=t0, ty=t1)
    if opts["print_format"] is not None:
        sys.stdout.write(opts["print_format"] % tform)

    ims = [utils.unextend_by(im, opts["extend"]) for im in ims]
    im2 = utils.unextend_by(im2, opts["extend"])

    if opts["show"]:
        import pylab as pyl
        imreg.imshow(ims[0], ims[1], im2)
        pyl.show()


if __name__ == "__main__":
    main()
