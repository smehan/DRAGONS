#
#                                                                  gemini_python
#
#                                                              primitives_ccd.py
# ------------------------------------------------------------------------------
from gempy.gemini import gemini_tools as gt

from geminidr import PrimitivesBASE
from .parameters_ccd import ParametersCCD

from recipe_system.utils.decorators import parameter_override
# ------------------------------------------------------------------------------
@parameter_override
class CCD(PrimitivesBASE):
    """
    This is the class containing all of the primitives used for generic CCD
    reduction.
    """
    tagset = None

    def __init__(self, adinputs, **kwargs):
        super(CCD, self).__init__(adinputs, **kwargs)
        self.parameters = ParametersCCD

    def biasCorrect(self, adinputs=None, **params):
        self.getProcessedBias(adinputs)
        adinputs = self.subtractBias(adinputs, **params)
        return adinputs

    def overscanCorrect(self, adinputs=None, **params):
        adinputs = self.subtractOverscan(adinputs, **params)
        adinputs = self.trimOverscan(adinputs, **params)
        return adinputs

    def subtractBias(self, adinputs=None, **params):
        """
        The subtractBias primitive will subtract the science extension of the
        input bias frames from the science extension of the input science
        frames. The variance and data quality extension will be updated, if
        they exist.

        Parameters
        ----------
        suffix: str
            suffix to be added to output files
        bias: str/list of str
            bias(es) to subtract
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))
        timestamp_key = self.timestamp_keys[self.myself()]

        bias_list = params["bias"] if params["bias"] else [
            self._get_cal(ad, 'processed_bias') for ad in adinputs]

        # Provide a bias AD object for every science frame
        for ad, bias in zip(*gt.make_lists(adinputs, bias_list, force_ad=True)):
            if ad.phu.get(timestamp_key):
                log.warning("No changes will be made to {}, since it has "
                            "already been processed by subtractBias".
                            format(ad.filename))
                continue

            if bias is None:
                if 'qa' in self.context:
                    log.warning("No changes will be made to {}, since no "
                                "bias was specified".format(ad.filename))
                    continue
                else:
                    raise IOError('No processed bias listed for {}'.
                                  format(ad.filename))

            try:
                gt.check_inputs_match(ad, bias, check_filter=False)
            except ValueError:
                bias = gt.clip_auxiliary_data(ad, bias, aux_type='cal',
                                    keyword_comments=self.keyword_comments)
                # An Error will be raised if they don't match now
                gt.check_inputs_match(ad, bias, check_filter=False)

            log.fullinfo('Subtracting this bias from {}:\n{}'.
                         format(ad.filename, bias.filename))
            ad.subtract(bias)

            # Record bias used, timestamp, and update filename
            ad.phu.set('BIASIM', bias.filename, self.keyword_comments['BIASIM'])
            gt.mark_history(ad, primname=self.myself(), keyword=timestamp_key)
            ad.filename = gt.filename_updater(adinput=ad, suffix=params["suffix"],
                                              strip=True)
        return adinputs

    def subtractOverscan(self, adinputs=None, **params):
        """No-op since we only have a GMOS-specific version"""
        return adinputs

    def trimOverscan(self, adinputs=None, **params):
        """
        The trimOverscan primitive trims the overscan region from the input
        AstroData object and updates the headers.

        Parameters
        ----------
        suffix: str
            suffix to be added to output files
        """
        log = self.log
        log.debug(gt.log_message("primitive", self.myself(), "starting"))
        timestamp_key = self.timestamp_keys[self.myself()]
        sfx = params["suffix"]

        for ad in adinputs:
            if ad.phu.get(timestamp_key) is not None:
                log.warning('No changes will be made to {}, since it has '
                            'already been processed by trimOverscan'.
                            format(ad.filename))
                continue

            ad = gt.trim_to_data_section(ad,
                                    keyword_comments=self.keyword_comments)

            # Set keyword, timestamp, and update filename
            ad.phu.set('TRIMMED', 'yes', self.keyword_comments['TRIMMED'])
            gt.mark_history(ad, primname=self.myself(), keyword=timestamp_key)
            ad.filename = gt.filename_updater(adinput=ad, suffix=sfx, strip=True)
        return adinputs
