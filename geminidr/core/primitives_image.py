#
#                                                                  gemini_python
#
#                                                            primitives_image.py
# ------------------------------------------------------------------------------
import numpy as np
from copy import deepcopy

from gempy.gemini import gemini_tools as gt
from gempy.library import astrotools as at

from .primitives_register import Register
from .primitives_resample import Resample
from . import parameters_image

from recipe_system.utils.decorators import parameter_override
# ------------------------------------------------------------------------------
@parameter_override
class Image(Register, Resample):
    """
    This is the class containing the generic imaging primitives.
    """
    tagset = set(["IMAGE"])

    def __init__(self, adinputs, **kwargs):
        super(Image, self).__init__(adinputs, **kwargs)
        self._param_update(parameters_image)

    def fringeCorrect(self, adinputs=None, **params):
        """
        Correct science frames for the effects of fringing, using a fringe
        frame. The fringe frame is obtained either from a specified parameter,
        or the "fringe" stream, or the calibration database. This is basically
        a bookkeeping wrapper for subtractFringe(), which does all the work.

        Parameters
        ----------
        suffix: str
            suffix to be added to output files
        fringe: list/str/AstroData/None
            fringe frame(s) to subtract
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))
        timestamp_key = self.timestamp_keys[self.myself()]

        # Exit now if nothing needs a correction, to avoid an error when the
        # calibration search fails. If images with different exposure times
        # are used, some frames may not require a correction (but the calibration
        # search will succeed), so still need to check individual inputs later.
        if not any(self._needs_fringe_correction(ad) for ad in adinputs):
            log.stdinfo("No input images require a fringe correction.")
            return adinputs

        fringe = params["fringe"]
        scale = params["scale"]
        if fringe is None:
            try:
                fringe_list = self.streams['fringe']
                assert len(fringe_list) == 1
                scale = False
                log.stdinfo("Using fringe frame in 'fringe' stream. "
                            "Setting scale=False")
            except (KeyError, AssertionError):
                self.getProcessedFringe(adinputs)
                fringe_list = self._get_cal(adinputs, "processed_fringe")
        else:
            fringe_list = fringe

        # Usual stuff to ensure that we have an iterable of the correct length
        # for the scale factors regardless of what the input is
        scale_factor = params["scale_factor"]
        try:
            factors = iter(scale_factor)
        except TypeError:
            factors = iter([scale_factor] * len(adinputs))
        else:
            # In case a single-element list was passed
            if len(scale_factor) == 1:
                factors = iter(scale_factor * len(adinputs))

        # Get a fringe AD object for every science frame
        for ad, fringe in zip(*gt.make_lists(adinputs, fringe_list, force_ad=True)):
            if ad.phu.get(timestamp_key):
                log.warning("No changes will be made to {}, since it has "
                            "already been processed by subtractFringe".
                            format(ad.filename))
                continue

            # Check the inputs have matching filters, binning, and shapes
            try:
                gt.check_inputs_match(ad, fringe)
            except ValueError:
                fringe = gt.clip_auxiliary_data(adinput=ad, aux=fringe,
                                                aux_type="cal")
                gt.check_inputs_match(ad, fringe)

            if scale:
                factor = next(factors)
                if factor is None:
                    factor = self._calculate_fringe_scaling(ad, fringe)
                log.stdinfo("Scaling fringe frame by factor {:.3f} before "
                            "subtracting from {}".format(factor, ad.filename))
                # Since all elements of fringe_list might be references to the
                # same AD, need to make a copy before multiplying
                fringe_copy = deepcopy(fringe)
                fringe_copy.multiply(factor)
                ad.subtract(fringe_copy)
            else:
                ad.subtract(fringe)

            # Timestamp and update header and filename
            ad.phu.set("FRINGEIM", fringe.filename, self.keyword_comments["FRINGEIM"])
            gt.mark_history(ad, primname=self.myself(), keyword=timestamp_key)
            ad.update_filename(suffix=params["suffix"], strip=True)
        return adinputs

    def makeFringe(self, adinputs=None, **params):
        """
        This primitive performs the bookkeeping related to the construction of
        a GMOS fringe frame. The pixel manipulation is left to makeFringeFrame

        Parameters
        ----------
        subtract_median_image: bool
            subtract a median image before finding fringes?
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))

        # Exit without doing anything if any of the inputs are inappropriate
        if not all(self._needs_fringe_correction(ad) for ad in adinputs):
            return adinputs
        if len(set(ad.filter_name(pretty=True) for ad in adinputs)) > 1:
            log.warning("Mismatched filters in input; not making fringe frame")
            return adinputs

        # Fringing on Cerro Pachon is generally stronger than on Maunakea.
        # A SExtractor mask alone is usually sufficient for GN data, but GS
        # data need to be median-subtracted to distinguish fringes from objects
        fringe_params = self._inherit_params(params, "makeFringeFrame", pass_suffix=True)

        # Detect sources in order to get an OBJMASK. Doing it now will aid
        # efficiency by putting the OBJMASK-added images in the list.
        # NB. If we're subtracting the median image, detectSources() has to
        # be run again anyway, so don't do it here.
        # NB2. We don't want to edit adinputs at this stage
        fringe_adinputs = adinputs if fringe_params["subtract_median_image"] else [ad if
                        any(hasattr(ext, 'OBJMASK') for ext in ad)
                        else self.detectSources([ad])[0] for ad in adinputs]

        # Add this frame to the list and get the full list (QA only)
        if "qa" in self.mode:
            self.addToList(fringe_adinputs, purpose='forFringe')
            fringe_adinputs = self.getList(purpose='forFringe')

        if len(fringe_adinputs) < 3:
            log.stdinfo("Fewer than 3 frames provided as input. "
                        "Not making fringe frame.")
            return adinputs

        # We have the required inputs to make a fringe frame
        fringe = self.makeFringeFrame(fringe_adinputs, **fringe_params)
        # Store the result and put the output in the "fringe" stream
        self.storeProcessedFringe(fringe)
        self.streams.update({'fringe': fringe})

        # We now return *all* the input images that required fringe correction
        # so they can all be fringe corrected
        return fringe_adinputs

    def makeFringeFrame(self, adinputs=None, **params):
        """
        Make a fringe frame from a list of images.

        Parameters
        ----------
        suffix: str
            suffix to be added to output files
        subtract_median_image: bool
            if True, create and subtract a median image before object
            detection as a first-pass fringe removal

        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))

        if len(adinputs) < 3:
            log.stdinfo('Fewer than 3 frames provided as input. '
                        'Not making fringe frame.')
            return []

        adinputs = self.correctBackgroundToReference([deepcopy(ad) for ad in adinputs],
                                            suffix='_bksub', remove_background=True,
                                                     separate_ext=False)

        # If needed, construct a median image and subtract from all frames to
        # do a first-order fringe removal and hence better detect real objects
        if params["subtract_median_image"]:
            median_image = self.stackFrames(adinputs, scale=False,
                            zero=False, operation="median",
                            reject_method="minmax", nlow=0, nhigh=1)
            if len(median_image) > 1:
                raise ValueError("Problem with creating median image")
            median_image = median_image[0]
            for ad in adinputs:
                ad.subtract(median_image)
            adinputs = self.detectSources(adinputs,
                        **self._inherit_params(params, "detectSources"))
            for ad in adinputs:
                ad.add(median_image)

        # Add object mask to DQ plane and stack with masking
        # separate_ext is irrelevant unless (scale or zero) but let's be explicit
        adinputs = self.stackSkyFrames(adinputs, mask_objects=True, separate_ext=False,
                                       scale=False, zero=False,
                    **self._inherit_params(params, "stackSkyFrames", pass_suffix=True))
        if len(adinputs) > 1:
            raise ValueError("Problem with stacking fringe frames")

        return adinputs

    def scaleByIntensity(self, adinputs=None, **params):
        """
        This primitive scales the inputs so they have the same intensity as
        the reference input (first in the list), which is untouched. Scaling
        can be done by mean or median and a statistics section can be used.

        Parameters
        ----------
        suffix: str
            suffix to be added to output files
        scaling: str ["mean"/"median"]
            type of scaling to use
        section: str/None
            section of image to use for statistics "x1:x2,y1:y2"
        separate_ext: bool
            if True, scale extensions independently?
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))

        scaling = params["scaling"]
        section = params["section"]
        separate_ext = params["separate_ext"]

        if len(adinputs) < 2:
            log.stdinfo("Scaling has no effect when there are fewer than two inputs")
            return adinputs

        # Do some housekeeping to handle mutually exclusive parameter inputs
        if separate_ext and len(set([len(ad) for ad in adinputs])) > 1:
            log.warning("Scaling by extension requested but inputs have "
                        "different sizes. Turning off.")
            separate_ext = False

        section = at.section_str_to_tuple(section)

        # I'm not making the assumption that all extensions are the same shape
        # This makes things more complicated, but more general
        targets = [np.nan] * len(adinputs[0])
        for ad in adinputs:
            all_data = []
            for index, ext in enumerate(ad):
                extver = ext.hdr['EXTVER']
                if section is None:
                    x1, y1 = 0, 0
                    y2, x2 = ext.data.shape
                else:
                    x1, x2, y1, y2 = section
                data = ext.data[y1:y2, x1:x2]
                if data.size:
                    mask = None if ext.mask is None else ext.mask[y1:y2, x1:x2]
                else:
                    log.warning("Section does not intersect with data for {}:{}."
                                " Using full frame.".format(ad.filename, extver))
                    data = ext.data
                    mask = ext.mask
                if mask is not None:
                    data = data[mask == 0]

                if not separate_ext:
                    all_data.extend(data.ravel())

                if separate_ext or index == len(ad)-1:
                    if separate_ext:
                        value = getattr(np, scaling)(data)
                        log.fullinfo("{}:{} has {} value of {}".format(ad.filename,
                                                            extver, scaling, value))
                    else:
                        value = getattr(np, scaling)(all_data)
                        log.fullinfo("{} has {} value of {}".format(ad.filename,
                                                                    scaling, value))
                    if np.isnan(targets[index]):
                        targets[index] = value
                    else:
                        factor = targets[index] / value
                        log.fullinfo("Multiplying by {}".format(factor))
                        if separate_ext:
                            ext *= factor
                        else:
                            ad *= factor

            ad.update_filename(suffix=params["suffix"], strip=True)
        return adinputs

    def _needs_fringe_correction(self, ad):
        """
        Helper method used by fringeCorrect() to determine whether the passed
        AD requires a fringe correction. By default, it is assumed that any
        frame sent to fringeCorrect() does require such a correction, so the
        top-level method simply returns True.

        Parameters
        ----------
        ad: AstroData
            input AD object

        Returns
        -------
        <bool>: does this image need a correction?
        """
        return True

    def _calculate_fringe_scaling(self, ad, fringe):
        """
        Helper method to determine the amount by which to scale a fringe frame
        before subtracting from a science frame. Returns that factor.

        The scaling is determined by minimizing the pixel-to-pixel variance of
        the output frame. If the science frame is S and the fringe frame F,
        then the scaling factor is x where Var(S-xF) is minimized. Doing some
        maths, it can be shown that

            n*Sum(SF) - Sum(S)*Sum(F)  where n is the number of pixels used
        x = -------------------------  and the sums are performed over the
             n*Sum(FF) - (Sum(F))**2   pixels (only good, non-object pixels)

        This works reasonably well for images that are flat, where the pixel-
        to-pixel variation is driven by the fringes and not large-scale
        variations. GMOSImage has a more specific algorithm that uses control
        pairs marking specific parts of the fringe pattern, and this is
        works better, but requires preparatory work setting up those pairs.

        Parameters
        ----------
        ad: AstroData
            input AD object
        fringe: AstroData
            fringe frame

        Returns
        -------
        <float>: scale factor to match fringe to ad
        """
        sum_sci = 0.
        sum_fringe = 0.
        sum_cross = 0.
        sum_fringesq = 0.
        npix = 0

        for ext, fr_ext in zip(ad, fringe):
            # Mask bad pixels in either DQ, and OBJMASK
            mask = (getattr(ext, 'OBJMASK', None) if ext.mask is None else
                    ext.mask | getattr(ext, 'OBJMASK', 0))
            if mask is None:
                mask = fr_ext.mask
            elif fr_ext.mask is not None:
                mask |= fr_ext.mask
            if mask is None:
                good = np.ones_like(ext, dtype=bool)
            else:
                good = (mask == 0)

            sum_sci += np.sum(ext.data[good])
            sum_fringe += np.sum(fr_ext.data[good])
            sum_cross += np.sum(ext.data[good] * fr_ext.data[good])
            sum_fringesq += np.sum(fr_ext.data[good]**2)
            npix += np.sum(good)

        scaling = (npix * sum_cross - sum_sci * sum_fringe) / (npix * sum_fringesq - sum_fringe**2)
        return scaling
