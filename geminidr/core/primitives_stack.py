#
#                                                                  gemini_python
#
#                                                            primitives_stack.py
# ------------------------------------------------------------------------------
import astrodata
from astrodata.fits import windowedOp

import numpy as np
from astropy import table
from functools import partial
from copy import deepcopy

from gempy.gemini import gemini_tools as gt
from gempy.library.nddops import NDStacker

from geminidr import PrimitivesBASE
from . import parameters_stack

from recipe_system.utils.decorators import parameter_override

# ------------------------------------------------------------------------------
@parameter_override
class Stack(PrimitivesBASE):
    """
    This is the class containing all of the primitives for stacking.
    """
    tagset = None

    def __init__(self, adinputs, **kwargs):
        super(Stack, self).__init__(adinputs, **kwargs)
        self._param_update(parameters_stack)

    def alignAndStack(self, adinputs=None, **params):
        """
        This primitive calls a set of primitives to perform the steps
        needed for alignment of frames to a reference image and stacking.
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))

        # Return entire list if only one object (which would presumably be the
        # adinputs, or return the input list if we can't stack
        if len(adinputs) <= 1:
            log.stdinfo("No alignment or correction will be performed, since "
                        "at least two input AstroData objects are required "
                        "for alignAndStack")
            return adinputs
        else:
            adinputs = self.matchWCSToReference(adinputs, **self._inherit_params(params, 'matchWCSToReference'))
            adinputs = self.resampleToCommonFrame(adinputs, **self._inherit_params(params, 'resampleToCommonFrame'))
            if params["save"]:
                self.writeOutputs(adinputs)
            adinputs = self.stackFrames(adinputs, **self._inherit_params(params, 'stackFrames'))
        return adinputs

    def stackFlats(self, adinputs=None, **params):
        """Default behaviour is just to stack images as normal"""
        params["zero"] = False
        return self.stackFrames(adinputs, **params)

    def stackFrames(self, adinputs=None, **params):
        """
        This primitive will stack each science extension in the input dataset.
        New variance extensions are created from the stacked science extensions
        and the data quality extensions are propagated through to the final
        file.

        Parameters
        ----------
        suffix: str
            suffix to be added to output files
        apply_dq: bool
            apply DQ mask to data before combining?
        nhigh: int
            number of high pixels to reject
        nlow: int
            number of low pixels to reject
        operation: str
            combine method
        reject_method: str
            type of pixel rejection (passed to gemcombine)
        zero: bool
            apply zero-level offset to match background levels?
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))
        timestamp_key = self.timestamp_keys["stackFrames"]
        sfx = params["suffix"]
        memory = params["memory"]
        if memory is not None:
            memory = int(memory * 1000000000)

        zero = params["zero"]
        scale = params["scale"]
        apply_dq = params["apply_dq"]
        separate_ext = params["separate_ext"]
        statsec = params["statsec"]
        reject_method = params["reject_method"]
        if statsec:
            statsec = tuple([slice(int(start)-1, int(end))
                             for x in reversed(statsec.strip('[]').split(','))
                             for start, end in [x.split(':')]])

        if len(adinputs) <= 1:
            log.stdinfo("No stacking will be performed, since at least two "
                        "input AstroData objects are required for stackFrames")
            return adinputs

        # Perform various checks on inputs
        for ad in adinputs:
            if not "PREPARED" in ad.tags:
                raise IOError("{} must be prepared" .format(ad.filename))

        if len(set(len(ad) for ad in adinputs)) > 1:
            raise IOError("Not all inputs have the same number of extensions")
        if len(set([ext.nddata.shape for ad in adinputs for ext in ad])) > 1:
            raise IOError("Not all inputs images have the same shape")

        # Determine the average gain from the input AstroData objects and
        # add in quadrature the read noise
        gains = [ad.gain() for ad in adinputs]
        read_noises = [ad.read_noise() for ad in adinputs]

        assert all(gain is not None for gain in gains), "Gain problem"
        assert all(rn is not None for rn in read_noises), "RN problem"

        # Compute gain and read noise of final stacked images
        nexts = len(gains[0])
        gain_list = [np.mean([gain[i] for gain in gains])
                     for i in range(nexts)]
        read_noise_list = [np.sqrt(np.sum([rn[i]*rn[i] for rn in read_noises]))
                                     for i in range(nexts)]

        num_img = len(adinputs)
        num_ext = len(adinputs[0])
        zero_offsets = np.zeros((num_ext, num_img), dtype=np.float32)
        scale_factors = np.ones_like(zero_offsets)

        # Try to determine how much memory we're going to need to stack and
        # whether it's necessary to flush pixel data to disk first
        # Also determine kernel size from offered memory and bytes per pixel
        bytes_per_ext = []
        for ext in adinputs[0]:
            bytes = 0
            # Count _data twice to handle temporary arrays
            for attr in ('_data', '_data', '_uncertainty'):
                item = getattr(ext.nddata, attr)
                if item is not None:
                    # A bit of numpy weirdness in the difference between normal
                    # python types ("float32") and numpy types ("np.uint16")
                    try:
                        bytes += item.dtype.itemsize
                    except TypeError:
                        bytes += item.dtype().itemsize
                    except AttributeError:  # For non-lazy VAR
                        bytes += item._array.dtype.itemsize
            bytes += 2  #  mask always created
            bytes_per_ext.append(bytes * np.multiply.reduce(ext.nddata.shape))

        if memory is not None and (num_img * max(bytes_per_ext) > memory):
            adinputs = self.flushPixels(adinputs)

        # Compute the scale and offset values by accessing the memmapped data
        # so we can pass those to the stacking function
        # TODO: Should probably be done better to consider only the overlap
        # regions between frames
        if scale or zero:
            levels = np.empty((num_img, num_ext), dtype=np.float32)
            for i, ad in enumerate(adinputs):
                for index in range(num_ext):
                    nddata = (ad[index].nddata.window[:] if statsec is None
                              else ad[i][index].nddata.window[statsec])
                    #levels[i, index] = np.median(nddata.data)
                    levels[i, index] = gt.measure_bg_from_image(nddata, value_only=True)
            if scale and zero:
                log.warning("Both scale and zero are set. Setting scale=False.")
                scale = False
            if separate_ext:
                # Target value is corresponding extension of first image
                if scale:
                    scale_factors = (levels[0] / levels).T
                else:  # zero=True
                    zero_offsets = (levels[0] - levels).T
            else:
                # Target value is mean of all extensions of first image
                target = np.mean(levels[0])
                if scale:
                    scale_factors = np.tile(target / np.mean(levels, axis=1),
                                              num_ext).reshape(num_ext, num_img)
                else:  # zero=True
                    zero_offsets = np.tile(target - np.mean(levels, axis=1),
                                           num_ext).reshape(num_ext, num_img)
            if scale and np.min(scale_factors) < 0:
                log.warning("Some scale factors are negative. Not scaling.")
                scale_factors = np.ones_like(scale_factors)
                scale = False
            if scale and np.any(np.isinf(scale_factors)):
                log.warning("Some scale factors are infinite. Not scaling.")
                scale_factors = np.ones_like(scale_factors)
                scale = False
            if scale and np.any(np.isnan(scale_factors)):
                log.warning("Some scale factors are undefined. Not scaling.")
                scale_factors = np.ones_like(scale_factors)
                scale = False

        if reject_method == "varclip" and any(ext.variance is None
                                              for ad in adinputs for ext in ad):
            log.warning("Rejection method 'varclip' has been chosen but some"
                        "extensions have no variance. 'sigclip' will be used"
                        "instead.")
            reject_method = "sigclip"

        stack_function = NDStacker(combine=params["operation"],
                                   reject=reject_method,
                                   log=self.log, **params)

        # NDStacker uses DQ if it exists; if we don't want that, delete the DQs!
        if not apply_dq:
            [setattr(ext, 'mask', None) for ad in adinputs for ext in ad]

        ad_out = astrodata.create(adinputs[0].phu)
        for index, (extver, sfactors, zfactors) in enumerate(zip(adinputs[0].hdr.get('EXTVER'),
                                                          scale_factors, zero_offsets)):
            status = ("Combining EXTVER {}.".format(extver) if num_ext > 1 else
                      "Combining images.")
            if scale:
                status += " Applying scale factors."
                numbers = sfactors
            elif zero:
                status += " Applying offsets."
                numbers = zfactors
            log.stdinfo(status)
            if ((scale or zero) and (index == 0 or separate_ext)):
                for ad, value in zip(adinputs, numbers):
                    log.stdinfo("{:40s}{:10.3f}".format(ad.filename, value))

            shape = adinputs[0][index].nddata.shape
            if memory is None:
                kernel = shape
            else:
                # Chop the image horizontally into equal-sized chunks to process
                # This uses the minimum number of steps and uses minimum memory
                # per step.
                oversubscription = (bytes_per_ext[index] * num_img) // memory + 1
                kernel = ((shape[0] + oversubscription - 1) // oversubscription,) + shape[1:]
            with_uncertainty = True  # Since all stacking methods return variance
            with_mask = apply_dq and not any(ad[index].nddata.window[:].mask is None
                                             for ad in adinputs)
            result = windowedOp(partial(stack_function, scale=sfactors, zero=zfactors),
                                [ad[index].nddata for ad in adinputs],
                                kernel=kernel, dtype=np.float32,
                                with_uncertainty=with_uncertainty, with_mask=with_mask)
            ad_out.append(result)
            log.stdinfo("")

        # Propagate REFCAT as the union of all input REFCATs
        refcats = [ad.REFCAT for ad in adinputs if hasattr(ad, 'REFCAT')]
        if refcats:
            out_refcat = table.unique(table.vstack(refcats,
                                metadata_conflicts='silent'), keys='Cat_Id')
            out_refcat['Cat_Id'] = list(range(1, len(out_refcat)+1))
            ad_out.REFCAT = out_refcat

        # Set AIRMASS to be the mean of the input values
        try:
            airmass_kw = ad_out._keyword_for('airmass')
            mean_airmass = np.mean([ad.airmass() for ad in adinputs])
        except:  # generic implementation failure (probably non-Gemini)
            pass
        else:
            ad_out.phu.set(airmass_kw, mean_airmass, "Mean airmass for the exposure")

        # Set GAIN to the average of input gains. Set the RDNOISE to the
        # sum in quadrature of the input read noises.
        for ext, gain, rn in zip(ad_out, gain_list, read_noise_list):
            ext.hdr.set('GAIN', gain, self.keyword_comments['GAIN'])
            ext.hdr.set('RDNOISE', rn, self.keyword_comments['RDNOISE'])
        # Stick the first extension's values in the PHU
        ad_out.phu.set('GAIN', gain_list[0], self.keyword_comments['GAIN'])
        ad_out.phu.set('RDNOISE', read_noise_list[0], self.keyword_comments['RDNOISE'])

        # Add suffix to datalabel to distinguish from the reference frame
        ad_out.phu.set('DATALAB', "{}{}".format(ad_out.data_label(), sfx),
                   self.keyword_comments['DATALAB'])

        # Add other keywords to the PHU about the stacking inputs
        ad_out.orig_filename = ad_out.phu.get('ORIGNAME')
        ad_out.phu.set('NCOMBINE', len(adinputs), self.keyword_comments['NCOMBINE'])
        for i, ad in enumerate(adinputs, start=1):
            ad_out.phu.set('IMCMB{:03d}'.format(i), ad.phu.get('ORIGNAME', ad.filename))

        # Timestamp and update filename and prepare to return single output
        gt.mark_history(ad_out, primname=self.myself(), keyword=timestamp_key)
        ad_out.update_filename(suffix=sfx, strip=True)

        return [ad_out]

    def stackSkyFrames(self, adinputs=None, **params):
        """
        This primitive stacks the AD frames sent to it with object masking.

        Parameters
        ----------
        suffix: str
            suffix to be added to output files
        apply_dq: bool
            apply DQ mask to data before combining?
        dilation: int
            dilation radius for expanding object mask
        mask_objects: bool
            mask objects from the input frames?
        nhigh: int
            number of high pixels to reject
        nlow: int
            number of low pixels to reject
        operation: str
            combine method
        reject_method: str
            type of pixel rejection (passed to gemcombine)
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))
        #timestamp_key = self.timestamp_keys["stackSkyFrames"]

        # Not what stackFrames does when both are set
        stack_params = self._inherit_params(params, 'stackFrames',
                                            pass_suffix=True)
        if stack_params["scale"] and stack_params["zero"]:
            log.warning("Both the scale and zero parameters are set. "
                        "Setting zero=False.")
            stack_params["zero"] = False

        # Need to deepcopy here to avoid changing DQ of inputs
        dilation=params["dilation"]
        if params["mask_objects"]:
            # Purely cosmetic to avoid log reporting unnecessary calls to
            # dilateObjectMask
            if dilation > 0:
                adinputs = self.dilateObjectMask(adinputs, dilation=dilation)
            adinputs = self.addObjectMaskToDQ([deepcopy(ad) for ad in adinputs])

        #if scale or zero:
        #    ref_bg = gt.measure_bg_from_image(adinputs[0], value_only=True)
        #    for ad in adinputs[1:]:
        #        this_bg = gt.measure_bg_from_image(ad, value_only=True)
        #        for ext, this, ref in zip(ad, this_bg, ref_bg):
        #            if scale:
        #                ext *= ref / this
        #            elif zero:
        #                ext += ref - this
        adinputs = self.stackFrames(adinputs, **stack_params)
        return adinputs
