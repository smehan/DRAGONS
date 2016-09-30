import math

from astrodata import astro_data_tag, astro_data_descriptor, simple_descriptor_mapping, keyword, TagSet
from ..gemini import AstroDataGemini
from .lookups import detector_properties, nominal_zeropoints, config_dict, read_modes

# NOTE: Temporary functions for test. gempy imports astrodata and
#       won't work with this implementation
from ..gmu import *

# TODO: not all those should be descriptors.  eg. HICOL. only central_wavelength is a real descriptor here.
# TODO: how does one assign a docstring to those that are indeed descriptors?
@simple_descriptor_mapping(
    bias = keyword("DETBIAS"),
    central_wavelength = keyword("GRATWAVE"),
    filter1 = keyword("FILTER1"),
    filter2 = keyword("FILTER2"),
    hicol = keyword("HICOL", on_ext=True),
    hirow = keyword("HIROW", on_ext=True),
    lnrs = keyword("LNRS"),
    lowcol = keyword("LOWCOL", on_ext=True),
    lowrow = keyword("LOWROW", on_ext=True),
    ndavgs = keyword("NDAVGS")
)
class AstroDataGnirs(AstroDataGemini):
    @staticmethod
    def _matches_data(data_provider):
        return data_provider.phu.get('INSTRUME', '').upper() == 'GNIRS'

    @astro_data_tag
    def _tag_instrument(self):
        return TagSet(['GNIRS'])

    @astro_data_tag
    def _type_dark(self):
        if self.phu.OBSTYPE == 'DARK':
            return TagSet(['DARK', 'CAL'], blocks=['IMAGE', 'SPECT'])

    @astro_data_tag
    def _type_arc(self):
        if self.phu.OBSTYPE == 'ARC':
            return TagSet(['ARC', 'CAL'])

    @astro_data_tag
    def _type_image(self):
        if self.phu.ACQMIR == 'In':
            return TagSet(['IMAGE'])

    @astro_data_tag
    def _type_mask(self):
        if 'Acq' not in self.phu.get('SLIT', ''):
            return TagSet(['MASK'], if_present=['ACQUISITION'])

    @astro_data_tag
    def _type_spect(self):
        if self.phu.ACQMIR == 'Out':
            tags = set(['SPECT'])
            slit = self.phu.get('SLIT', '').lower()
            grat = self.phu.get('GRATING', '')
            prism = self.phu.get('PRISM', '')
            if slit == 'IFU':
                tags.add('IFU')
            elif ('arcsec' in slit or 'pin' in slit) and 'mm' in grat:
                if 'MIR' in prism:
                    tags.add('LS')
                elif 'XD' in prism:
                    tags.add('XD')
            return TagSet(tags)

    @astro_data_tag
    def _type_flats(self):
        if self.phu.OBSTYPE == 'FLAT':
            if 'Pinholes' in self.phu.SLIT:
                return TagSet(['PINHOLE', 'CAL'], remove=['GCALFLAT'])
            else:
                return TagSet(['FLAT', 'CAL'])

    # TODO: write a function in the spirit of _parse_section for GNIRS *_section
    @astro_data_descriptor
    def data_section(self, pretty=False):
        """
        Returns the rectangular section that includes the pixels that would be
        exposed to light.  If pretty is False, a tuple of 0-based coordinates
        is returned with format (x1, x2, y1, y2).  If pretty is True, a keyword
        value is returned without parsing as a string.  In this format, the
        coordinates are generally 1-based.

        One tuple or string is return per extension/array.  If more than one
        array, the tuples/strings are return in a list.  Otherwise, the
        section is returned as a tuple or a string.

        Parameters
        ----------
        pretty : bool
         If True, return the formatted string found in the header.

        Returns
        -------
        tuple of integers or list of tuples
            Location of the pixels exposed to light using Python slice values.

        string or list of strings
            Location of the pixels exposed to light using an IRAF section
            format (1-based).

        """
        hirows = self.hirow()
        lowrows = self.lowrow()
        hicols = self.hicol()
        lowcols = self.lowcol()

        data_sections = []
        # NOTE: Rows are X and cols are Y? These Romans are crazy
        for hir, hic, lowr, lowc in zip(hirows, hicols, lowrows, lowcols):
            if pretty:
                item = "[{:d}:{:d},{:d}:{:d}]".format(lowr+1, hir+1, lowc+1, hic+1)
            else:
                item = [lowr, hir+1, lowc, hic+1]
            data_sections.append(item)

        if len(data_sections) == 1:
            return data_sections[0]

        return data_sections

    @astro_data_descriptor
    def array_section(self, pretty=False):
        """
        Returns the section covered by the array(s) relative to the detector
        frame.  For example, this can be the position of multiple amps read
        within a CCD.  If pretty is False, a tuple of 0-based coordinates
        is returned with format (x1, x2, y1, y2).  If pretty is True, a keyword
        value is returned without parsing as a string.  In this format, the
        coordinates are generally 1-based.

        One tuple or string is return per extension/array.  If more than one
        array, the tuples/strings are return in a list.  Otherwise, the
        section is returned as a tuple or a string.

        Parameters
        ----------
        pretty : bool
            If True, return the formatted string found in the header.

        Returns
        -------
        tuple of integers or list of tuples
            Position of extension(s) using Python slice values

        string or list of strings
            Position of extension(s) using an IRAF section format (1-based)

        """
        return data_section(self, pretty=pretty)

    @astro_data_descriptor
    def detector_section(self, pretty=False):
        """
        Returns the section covered by the detector relative to the whole
        mosaic of detectors.  If pretty is False, a tuple of 0-based coordinates
        is returned with format (x1, x2, y1, y2).  If pretty is True, a keyword
        value is returned without parsing as a string.  In this format, the
        coordinates are generally 1-based.

        One tuple or string is return per extension/array.  If more than one
        array, the tuples/strings are return in a list.  Otherwise, the
        section is returned as a tuple or a string.

        Parameters
        ----------
        pretty : bool
         If True, return the formatted string found in the header.

        Returns
        -------
        tuple of integers or list of tuples
            Position of the detector using Python slice values.

        string or list of strings
            Position of the detector using an IRAF section format (1-based).

        """
        return data_section(self, pretty=pretty)

    @astro_data_descriptor
    def disperser(self, stripID=False, pretty=False):
        """
        Returns the name of the disperser group as the name of the grating
        and of the prims joined with '&', unless the acquisition mirror is
        in the beam, then returns the string "MIRROR". The component ID can
        be removed with either 'stripID' or 'pretty' set to True.

        Parameters
        ----------
        stripID : bool
            If True, removes the component ID and returns only the name of
            the disperser.
        pretty : bool
            Same as for stripID.  Pretty here does not do anything more.

        Returns
        -------
        str
            The disperser group, as grism&prism, with or without the
            component ID.

        """
        if self.phu.get('ACQMIR') == 'In':
            return 'MIRROR'

        grating = self.grating(stripID=stripID, pretty=pretty)
        prism = self.prism(stripID=stripID, pretty=pretty)
        if prism.startswith('MIR'):
            return str(grating)
        else:
            return "{}&{}".format(grating, prism)

    @astro_data_descriptor
    def focal_plane_mask(self, stripID=False, pretty=False):
        """
        Returns the name of the focal plane mask group as the slit and the
        decker joined with '&', or as a shorter (pretty) version.
        The component ID can be removed with either 'stripID' or 'pretty'
        set to True.

        Parameters
        ----------
        stripID : bool
            If True, removes the component ID and returns only the name of
            the focal plane mask.
        pretty : bool
            If True, removes the component IDs and returns a short string
            representing broadly the setting.

        Returns
        -------
        str
            The name of the focal plane mask with or without the component ID.

        """
        slit = self.slit(stripID=stripID, pretty=pretty).replace('Acquisition', 'Acq')
        decker = self.decker(stripID=stripID, pretty=pretty).replace('Acquisition', 'Acq')

        # Default fpm value
        fpm = "{}&{}".format(slit, decker)
        if pretty:
            if "Long" in decker:
                fpm = slit
            elif "XD" in decker:
                fpm = "{}XD".format(slit)
            elif "IFU" in slit and "IFU" in decker:
                fpm = "IFU"
            elif "Acq" in slit and "Acq" in decker:
                fpm = "Acq"

        return fpm

    @astro_data_descriptor
    def gain(self):
        """
        Returns the gain used for the observation.  This is read from a
        lookup table using the read_mode and the well_depth.

        Returns
        -------
        float
            Gain used for the observation.

        """
        read_mode = self.read_mode()
        well_depth = self.well_depth_setting()

        return float(detector_properties[read_mode, well_depth].gain)

    @astro_data_descriptor
    def grating(self, stripID=False, pretty=False):
        """
        Returns the name of the grating used for the observation.
        The component ID can be removed with either 'stripID' or 'pretty'
        set to True.

        Parameters
        ----------
        stripID : bool
            If True, removes the component ID and returns only the name of
            the disperser.
        pretty : bool
            Same as for stripID.  Pretty here does not do anything more.

        Returns
        -------
        str
            The name of the grating with or without the component ID.

        """
        grating = self.phu.GRATING

        match = re.match("([\d/m]+)[A-Z]*(_G)(\d+)", grating)
        try:
            ret_grating = "{}{}{}".format(*match.groups())
        except AttributeError:
            ret_grating = grating

        if stripID or pretty:
            return removeComponentID(ret_grating)
        return ret_grating

    @astro_data_descriptor
    def group_id(self):
        """
        Returns a string representing a group of data that are compatible
        with each other.  This is used when stacking, for example.  Each
        instrument, mode of observation, and data type will have its own rules.

        Returns
        -------
        str
            A group ID for compatible data.

        """

        tags = self.tags
        if 'DARK' in tags:
            desc_list = 'read_mode', 'exposure_time', 'coadds'
        else:
            # The descriptor list is the same for flats and science frames
            desc_list = 'observation_id', 'filter_name', 'camera', 'read_mode'

        desc_list = desc_list + ('well_depth_setting', 'detector_section', 'disperser', 'focal_plane_mask')

        pretty_ones = set(['filter_name', 'disperser', 'focal_plane_mask'])

        collected_strings = []
        for desc in desc_list:
            method = getattr(self, desc)
            if desc in pretty_ones:
                result = method(pretty=True)
            else:
                result = method()
            collected_strings.append(str(result))

        return '_'.join(collected_strings)

    @astro_data_descriptor
    def nominal_photometric_zeropoint(self):
        """
        Returns the nominal photometric zeropoint for the observation.
        This value is obtained from a lookup table based on gain, the
        camera used, and the filter used.

        Returns
        -------
        float
            The nominal photometric zeropoint as a magnitude.

        """
        gain = self.gain()
        camera = self.camera()
        filter_name = self.filter_name(pretty=True)

        result = []
        for bunit in self.hdr.BUNIT:
            gain_factor = (2.5 * math.log10(gain)) if bunit == 'adu' else 0.0
            nz_key = (filter_name, camera)
            nom_phot_zeropoint = nominal_zeropoints[nz_key] - gain_factor
            result.append(nom_phot_zeropoint)

        return result

    @astro_data_descriptor
    def non_linear_level(self):
        """
        Returns the level at which the array becomes non-linear.  The
        return units are ADUs.  A lookup table is used and the value
        is based on read_mode, well_depth_setting, and saturation_level.

        Returns
        -------
        int
            Level in ADU at which the non-linear regime starts.

        """
        read_mode = self.read_mode()
        well_depth = self.well_depth_setting()

        limit = detector_properties[read_mode, well_depth].linearlimit

        return int(limit * self.saturation_level())

    @astro_data_descriptor
    def pixel_scale(self):
        """
        Returns the pixel scale in arc seconds.

        Returns
        -------
        float
            Pixel scale in arcsec.

        """
        camera = self.camera()

        if self.tags & set(['IMAGE', 'DARK']):
            # Imaging or darks
            match = re.match("^(Short|Long)(Red|Blue)_G\d+$", camera)
            try:
                cameratype = match.group(1)
                if cameratype == 'Short':
                    ret_pixel_scale = 0.15
                elif cameratype == 'Long':
                    ret_pixel_scale = 0.05
            except AttributeError:
                raise Exception('No camera match for imaging mode')
        else:
            # Spectroscopy mode
            prism = self.phu.PRISM
            decker = self.phu.DECKER
            disperser = self.phu.GRATING

            ps_key = (prism, decker, disperser, camera)
            ret_pixel_scale = float(config_dict[ps_key].pixscale)

        return ret_pixel_scale

    @astro_data_descriptor
    def prism(self, stripID=False, pretty=False):
        """
        Returns the name of the prism.  The component ID can be removed
        with either 'stripID' or 'pretty' set to True.

        Parameters
        ----------
        stripID : bool
            If True, removes the component ID and returns only the name of
            the prism.
        pretty : bool
            Same as for stripID.  Pretty here does not do anything more.

        Returns
        -------
        str
            The name of the prism with or without the component ID.

        """
        prism = self.phu.PRISM
        match = re.match("[LBSR]*\+*([A-Z]*_G\d+)", prism)
        # NOTE: The original descriptor has no provisions for not matching
        #       the RE... which will produce an exception down the road.
        #       Let's do it here (it will be an AttributeError, though)
        ret_prism = match.group(1)

        if stripID or pretty:
            ret_prism = removeComponentID(ret_prism)

        return ret_prism

    @astro_data_descriptor
    def ra(self):
        """
        Returns the Right Ascension of the center of the field in degrees.
        Uses the RA derived from the WCS, unless it is wildly different from
        the target RA stored in the headers (with telescope offset and in
        ICRS).  When that's the case the target RA is used.

        Returns
        -------
        float
            Right Ascension of the target in degrees.

        """
        wcs_ra = self.wcs_ra()
        tgt_ra = self.target_ra(offset=True, icrs=True)
        delta = abs(wcs_ra - tgt_ra)

        # wraparound?
        if delta > 180:
            delta = abs(delta - 360)
        delta = delta * 3600 # to arcsecs

        # And account for cos(dec) factor
        delta /= math.cos(math.radians(self.dec()))

        # If more than 1000" arcsec different, WCS is probably bad
        return (tgt_ra if delta > 1000 else wcs_ra)

    @astro_data_descriptor
    def dec(self):
        """
        Returns the Declination of the center of the field in degrees.
        Uses the Dec derived from the WCS, unless it is wildly different from
        the target Dec stored in the headers (with telescope offset and in
        ICRS).  When that's the case the target Dec is used.

        Returns
        -------
        float
            Declination of the target in degrees.

        """

        # In general, the GNIRS WCS is the way to go. But sometimes the DC
        # has a bit of a senior moment and the WCS is miles off (presumably
        # still has values from the previous observation or something. Who knows.
        # So we do a sanity check on it and use the target values if it's messed up
        wcs_dec = self.wcs_dec()
        tgt_dec = self.target_dec(offset=True, icrs=True)

        # wraparound?
        if delta > 180:
            delta = abs(delta - 360)
        delta = delta * 3600 # to arcsecs

        # If more than 1000" arcsec different, WCS is probably bad
        return (tgt_dec if delta > 1000 else wcs_dec)

    @astro_data_descriptor
    def read_mode(self):
        """
        Returns the read mode for the observation.  Uses a lookup table
        indexed on the number of non-destructive read pairs (LNRS) and
        the number of digital averages (NDAVGS)

        Returns
        -------
        str
            Read mode for the observation.

        """
        # Determine the number of non-destructive read pairs (lnrs) and the
        # number of digital averages (ndavgs) keywords from the global keyword
        # dictionary
        lnrs = self.lnrs()
        ndavgs = self.ndavgs()

        return read_modes.get((lnrs, ndavgs), "Invalid")

    @astro_data_descriptor
    def read_noise(self):
        """
        Returns the detector read noise, in electrons, for the observation.
        A lookup table indexed on read_mode and well_depth_setting is
        used to retrieve the read noise.

        Returns
        -------
        float
            Detector read noise in electrons.

        """
        # Determine the read mode and well depth from their descriptors
        read_mode = self.read_mode()
        well_depth = self.well_depth_setting()
        coadds = self.coadds()

        read_noise = detector_properties[(read_mode, well_depth)].readnoise

        return read_noise * math.sqrt(coadds)

    @astro_data_descriptor
    def saturation_level(self):
        """
        Returns the saturation level or the observation, in ADUs.
        A lookup table indexed on read_mode and well_depth_setting is used
        to retrieve the saturation level.

        Returns
        -------
        int
            Saturation level in ADUs.

        """
        gain = self.gain()
        coadds = self.coadds()
        read_mode = self.read_mode()
        well_depth = self.well_depth_setting()
        well = detector_properties[(read_mode, well_depth)].well

        return int(well * coadds / gain)

    @astro_data_descriptor
    def slit(self, stripID=False, pretty=False):
        """
        Returns the name of the slit mask.  The component ID can be removed
        with either 'stripID' or 'pretty' set to True.

        Parameters
        ----------
        stripID : bool
            If True, removes the component ID and returns only the name of
            the slit.
        pretty : bool
            Same as for stripID.  Pretty here does not do anything more.

        Returns
        -------
        str
            The name of the slit with or without the component ID.

        """

        slit = self.phu.SLIT.replace(' ', '')

        return (removeComponentID(slit) if stripID or pretty else slit)

    @astro_data_descriptor
    def well_depth_setting(self):
        """
        Returns the well depth setting used for the observation.
        For GNIRS, this is either 'Shallow' or 'Deep'.

        Returns
        -------
        str
            Well depth setting.

        """
        biasvolt = self.bias()

        if abs(0.3 - abs(biasvolt)) < 0.1:
            return "Shallow"
        elif abs(0.6 - abs(biasvolt)) < 0.1:
            return "Deep"
        else:
            return "Invalid"