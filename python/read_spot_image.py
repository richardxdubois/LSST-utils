import numpy as np
from astropy.io import fits
from bokeh.plotting import figure, output_file, show
import argparse


class get_spot_image():

    def __init__(self):

        self.amp_ordering = [15, 14, 13, 12, 11, 10, 9, 8, 0, 1, 2, 3, 4, 5, 6, 7]
        self.ccd_image = None
        self.amp = None

        self.image_fig = figure(title="amp image", height=1000, width=1000,
                                tooltips=[("x", "$x"), ("y", "$y"), ("value", "@image")])

        return

    def get_image(self, fname=None, amp=None):
        # see LSSTTD-437 for treatment of bias using bias files, not (only) the overscan region.

        self.amp = amp
        hdulist = fits.open(fname)
        ccd_image = None

        seg = self.amp_ordering[amp-1] + 1

        channel = hdulist[seg].header["CHANNEL"]
        extname = hdulist[seg].header["EXTNAME"]
        print("amp, seg, channel = ", amp, seg, channel, extname)

        allpixeldata = hdulist[seg].data
        pixeldata = allpixeldata[1:2002, 11:522]
        bias = np.array(allpixeldata[1:2002, 513:562])

        pedestal = np.mean(bias.flatten())
        bias_sub = bias.flatten() - pedestal

        sigma = np.std(bias_sub)

        self.ccd_image = pixeldata - pedestal
        if self.amp > 8:
            self.ccd_image = np.flip(self.ccd_image, 0)
            self.ccd_image = np.flip(self.ccd_image, 1)
        return

    def show_image(self):

        shape = np.shape(self.ccd_image)
        y0 = 0
        x0 = (self.amp-1)*shape[1]
        if self.amp > 8:
            x0 = (self.amp-9)*shape[1]
            y0 = shape[0]

        self.image_fig.image(image=[self.ccd_image], x=x0, y=y0, level="image", palette="Spectral11", dw=shape[1],
                             dh=shape[0])
        output_file("spot_image.html", title="spot image")


if __name__ == "__main__":

    # Command line arguments
    parser = argparse.ArgumentParser(description='Find archived data in the LSST  data Catalog. These include CCD test stand and vendor data files.')

    parser.add_argument('-i', '--input',
                        default="/Volumes/External_SSD_Deb/LSST/Data/spots_images/MC_C_20191101_000215_R12_S22.fits",
                        help="input file name (default=%(default)s)")
    parser.add_argument("-a", "--amp", default=7, help="amp number (default=%(default)s)")
    parser.add_argument("--all", default="yes", help="so all amps (default=%(default)s)")

    args = parser.parse_args()

    f_split = args.input.split(".")[0].split("_")
    ccd_name = f_split[-2] + "_" + f_split[-1]

    sI = get_spot_image()
    for amp in range(1, 17):

        if args.all == "no" and amp != int(args.amp):
            continue

        sI.get_image(fname=args.input, amp=amp)
        sI.show_image()
    if args.all == "no":
        sI.ccd_image.title.text = ccd_name + "amp " + str(sI.amp)
    else:
        sI.image_fig.title.text = ccd_name
    show(sI.image_fig)
