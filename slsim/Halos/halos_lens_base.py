import numpy as np
from lenstronomy.LensModel.lens_model import LensModel
from lenstronomy.Cosmo.lens_cosmo import LensCosmo
import warnings
from collections.abc import Iterable
from slsim.Halos.halos_ray_tracing import HalosRayTracing


def concentration_from_mass(z, mass, A=75.4, d=-0.422, m=-0.089):
    """Determine halo concentration from mass using Childs et al. 2018 model.

    This function calculates the concentration parameter of dark matter halos based on
    their masses, employing the concentration-mass relation presented in Childs et al.
    2018. This relation is applicable to both relaxed and unrelaxed halos, providing a
    broad utility for modeling halo properties across different cosmic structures.

    :param z: Redshift of the halo, influencing the concentration-mass relation.
    :param mass: Mass of the halo in solar masses, serving as the primary input for the
        concentration calculation.
    :param A: Pre-factor in the concentration-mass relation, defaulting to 75.4 as per
        the reference study.
    :param d: Exponent for the redshift term in the concentration-mass relation, with a
        default value of -0.422.
    :param m: Exponent for the mass term in the concentration-mass relation, set to
        -0.089 by default.
    :type z: float
    :type mass:  or array_like
    :type A: float, optional
    :type d: float, optional
    :type m: float, optional
    :return: The concentration parameter c_200 of the halo(s), providing a measure of
        the halo's density profile steepness.
    :rtype: float or array_like :note: The concentration parameter, defined as c_200, is
        crucial for understanding the density distribution within halos. It is bounded
        to be at least 1, ensuring physical realism in halo models. :reference: Childs
        et al. 2018, arXiv:1804.10199, doi:10.3847/1538-4357/aabf95
    """

    if isinstance(mass, (list, np.ndarray)) and len(mass) == 1:
        mass = mass[0]
    c_200 = A * ((1 + z) ** d) * (mass**m)
    c_200 = np.maximum(c_200, 1)
    return c_200
    # TODO: Make this able for list


class HalosLensBase(object):
    """Manage lensing properties of Halos.

    Provides methods to compute lensing properties of Halos, such as their convergence and shear.

    :param halos_list: Table of Halos.
    :type halos_list: astropy.Table
    :param cosmo: Cosmology used for lensing computations. If not provided, default astropy cosmology is used. Optional.
    :type cosmo: astropy.Cosmology, optional
    :param sky_area: Total sky area (in steradians) over which Halos are distributed. Defaults to full sky (4pi steradians). Optional.
    :type sky_area: float, optional
    :param samples_number: Number of samples for statistical calculations. Defaults to 1000. Optional.
    :type samples_number: int, optional

    :ivar halos_list: Table of Halos.
    :ivar n_halos: Number of Halos in `halos_list`.
    :ivar sky_area: Total sky area in square degrees.
    :ivar halos_redshift_list: Redshifts of the Halos.
    :ivar mass_list: Masses of the Halos in solar masses.
    :ivar cosmo: Cosmology used for computations.
    :ivar param_lens_model: LensModel with a NFW profile for each halo.

    :raises ValueError: If the input parameters are out of expected ranges.

    .. note::
        This class needs external libraries such as lenstronomy for its computations.

    Methods
    -------
    enhance_halos_table_random_pos()
        Enhances the halos table with random positions.

    get_lens_model()
        Creates a lens model using provided halos and optional mass sheet correction.

    random_position()
        Generates and returns random positions in the sky using a uniform distribution.

    get_nfw_kwargs(z=None, mass=None, n_halos=None, param_lens_cosmo=None, c=None)
        Returns the angle at scale radius and observed bending angle at the scale radius for NFW profile.

    get_halos_lens_kwargs()
        Constructs and returns the list of keyword arguments for each halo in the lens model.

    filter_halos_by_redshift(zd, zs)
        Filters halos and mass corrections by redshift conditions and constructs lens data.

    _filter_halos_by_condition(zd, zs)
        Filters the halos based on redshift conditions relative to deflector and source redshifts.

    _filter_mass_correction_by_condition(zd, zs)
        Filters the mass corrections based on redshift conditions relative to deflector and source redshifts.

    _build_lens_data(halos, mass_correction, zd, zs)
        Constructs lens data based on the provided halos, mass corrections, and redshifts.

    _build_lens_cosmo_dict(combined_redshift_list, z_source)
        Constructs a dictionary mapping each redshift to its corresponding LensCosmo instance.

    _build_lens_model(combined_redshift_list, z_source, n_halos)
        Construct a lens model based on the provided combined redshift list, source redshift, and number of halos.

    _build_kwargs_lens(n_halos, n_mass_correction, z_halo, mass_halo, px_halo, py_halo, c_200_halos, lens_model_list, kappa_ext_list, lens_cosmo_list)
        Constructs the lens keyword arguments based on provided input parameters.

    get_lens_data_by_redshift(zd, zs)
        Retrieves lens data filtered by the specified redshift range.

    halos_get_convergence_shear(gamma12=False, diff=1.0, diff_method='square`, lens_kwargs=None, param_lens_model=None, zdzs=None)
        Computes the convergence and shear at the origin due to all Halos.

    compute_various_kappa_gamma_values(zd, zs)
        Compute the various convergence and shear values from the non-linear correction numbers.

    halos_get_kext_gext_values(zd, zs)
        Compute the non-linear external convergence and shear values from the Halos.

    halos_compute_kappa(diff=0.0000001, num_points=500, diff_method='square`, lens_kwargs=None, param_lens_model=None, mass_sheet=None, enhance_pos=True)
        Plots the convergence (:math:`\kappa`) across the lensed sky area.

    plot_halos_convergence(diff=0.0000001,
                               num_points=500,
                               diff_method="square",
                               mass_sheet=None,
                               enhance_pos=True)
                                       Compares and plots the convergence for different configurations of the mass sheet.

    enhance_halos_pos_to0()
        Sets the positions of all halos to 0.

    halos_various_halos_data(zd, zs)
        Computes various convergence (kappa) and shear (gamma) values for given deflector and source redshifts
    """

    # TODO: ADD test functions
    # TODO: Add documentation for all methods, CHANGE the documentation for all methods
    def __init__(
        self,
        halos_list,
        mass_correction_list=None,
        cosmo=None,
        sky_area=0.004 * np.pi,
        samples_number=1000,
        mass_sheet=True,
        z_source=5,
    ):
        """Initialize the HalosLens class.

        :param halos_list: Table containing details of halos, including their redshifts and masses.
        :type halos_list: table
        :param mass_correction_list: Table for mass correction, containing details like redshifts and external convergences. Defaults to {}. Ignored if `mass_sheet` is set to False.
        :type mass_correction_list: table, optional
        :param cosmo: Instance specifying the cosmological parameters for lensing computations. If not provided, the default astropy cosmology will be used.
        :type cosmo: astropy.Cosmology instance, optional
        :param sky_area: Total sky area in steradians over which halos are distributed. Defaults to full sky (4π steradians).
        :type sky_area: float, optional
        :param samples_number: Number of samples for statistical calculations. Defaults to 1000.
        :type samples_number: int, optional
        :param mass_sheet: Flag to decide whether to use the mass_sheet correction. If set to False, the mass_correction_list is ignored. Defaults to True.
        :type mass_sheet: bool, optional
        """

        if mass_correction_list is None:
            mass_correction_list = {}
            if mass_sheet:
                warnings.warn(
                    "Mass sheet correction is not applied but mass_sheet is set to True."
                )
                mass_sheet = False
        if not mass_sheet:
            mass_correction_list = {}
            self.n_correction = 0
            self.mass_sheet_correction_redshift = mass_correction_list.get("z", [])
            #            self.mass_first_moment = mass_correction_list.get("first_moment", [])
            self.mass_sheet_kappa = mass_correction_list.get("kappa", [])
        if mass_sheet:
            self.n_correction = len(mass_correction_list)
            self.mass_sheet_correction_redshift = mass_correction_list["z"]
            self.mass_sheet_kappa = mass_correction_list["kappa"]
        self.z_source = z_source
        self.halos_list = halos_list
        self.mass_correction_list = mass_correction_list
        self.mass_sheet = mass_sheet
        if np.isnan(halos_list["z"][0]) and len(halos_list) == 1:
            self.n_halos = 0
        else:
            self.n_halos = len(self.halos_list)
        self.sky_area = sky_area
        # if self.n_halos == 0:
        #     self.halos_redshift_list = []
        # else: (not righting this because of unpleaseant error dealing with redshift nan)
        #    self.halos_redshift_list = halos_list["z"]
        self.halos_redshift_list = halos_list["z"]
        self.mass_list = halos_list["mass"]
        self.samples_number = samples_number
        self._z_source_convention = 5
        # todo: z_source_convention set same with halos.py and yml
        if cosmo is None:
            warnings.warn(
                "No cosmology provided, instead uses astropy.cosmology import default_cosmology"
            )
            import astropy.cosmology as cosmology

            self.cosmo = cosmology.default_cosmology.get()
        else:
            self.cosmo = cosmo

        self.combined_redshift_list = np.concatenate(
            (self.halos_redshift_list, self.mass_sheet_correction_redshift)
        )

        self._lens_cosmo = None  # place-holder for lazy load
        self._lens_model = None  # same as above
        c_200 = [
            concentration_from_mass(z=zi, mass=mi)
            for zi, mi in zip(self.halos_redshift_list, self.mass_list)
        ]
        self.halos_list["c_200"] = c_200
        self.enhance_halos_table_random_pos()

        # TODO: Set z_source as an input parameter or other way

    @property
    def param_lens_cosmo(self):
        """Lazy-load param_lens_cosmo."""
        if self._lens_cosmo is None:
            self._lens_cosmo = [
                LensCosmo(
                    z_lens=self.combined_redshift_list[h],
                    z_source=self.z_source,
                    cosmo=self.cosmo,
                )
                for h in range(self.n_halos + self.n_correction)
            ]
        return self._lens_cosmo

    @property
    def param_lens_model(self):
        """Lazy-load param_lens_model."""
        if self._lens_model is None:  # Only compute if not already done
            self._lens_model = self.get_lens_model()
        return self._lens_model

    def enhance_halos_table_random_pos(self):
        """Put halos in random positions in the sky."""
        n_halos = self.n_halos
        if n_halos == 0:
            self.halos_list["px"] = 0.0
            self.halos_list["py"] = 0.0
        else:
            px, py = np.array([self.random_position() for _ in range(n_halos)]).T
            # Adding the computed attributes to the halos table
            self.halos_list["px"] = px
            self.halos_list["py"] = py

    def get_lens_model(self):
        """Create a lens model using provided halos and optional mass sheet correction.
        This method constructs a lens model based on the halos and (if specified) the
        mass sheet correction. The halos are modeled with the NFW profile, and the mass
        sheet correction is modeled using the CONVERGENCE profile.

        :return: A lens model instance equipped with the parameters and configurations
            suitable for halo lensing studies. This model serves as the foundation for
            conducting lensing simulations, enabling the calculation of lensing effects
            such as deflection angles, shear, and magnification.
        :rtype: LensModel :note:
        """
        if self.mass_sheet:
            if self.n_halos == 0:
                lens_model = LensModel(
                    lens_model_list=["NFW"] + ["CONVERGENCE"] * self.n_correction,
                    lens_redshift_list=self.combined_redshift_list,
                    cosmo=self.cosmo,
                    observed_convention_index=[],
                    multi_plane=True,
                    z_source=self.z_source,
                    z_source_convention=self._z_source_convention,
                )
            else:
                lens_model = LensModel(
                    lens_model_list=["NFW"] * self.n_halos
                    + ["CONVERGENCE"] * self.n_correction,
                    lens_redshift_list=self.combined_redshift_list,
                    cosmo=self.cosmo,
                    observed_convention_index=[],
                    multi_plane=True,
                    z_source=self.z_source,
                    z_source_convention=self._z_source_convention,
                )
        else:
            if self.n_halos == 0:
                lens_model = LensModel(
                    lens_model_list=["NFW"],
                    lens_redshift_list=self.halos_redshift_list,
                    cosmo=self.cosmo,
                    observed_convention_index=[],
                    multi_plane=True,
                    z_source=self.z_source,
                    z_source_convention=self._z_source_convention,
                )
            else:
                lens_model = LensModel(
                    lens_model_list=["NFW"] * self.n_halos,
                    lens_redshift_list=self.halos_redshift_list,
                    cosmo=self.cosmo,
                    observed_convention_index=[],
                    multi_plane=True,
                    z_source=self.z_source,
                    z_source_convention=self._z_source_convention,
                )
        return lens_model

    def random_position(self):
        """Generates and returns random positions in the sky using a uniform
        distribution.

        :returns: The generated random x and y coordinates inside the skyarea in arcsec.
        :rtype: (float, float)
        """

        phi = 2 * np.pi * np.random.random()
        upper_bound = np.sqrt(self.sky_area / np.pi)
        random_radius = 3600 * np.sqrt(np.random.random()) * upper_bound
        px = random_radius * np.cos(2 * phi)
        py = random_radius * np.sin(2 * phi)
        return px, py

    def get_nfw_kwargs(self, z=None, mass=None, n_halos=None, lens_cosmo=None, c=None):
        """Returns the angle at scale radius, observed bending angle at the scale
        radius, and positions of the Halos in the lens plane from physical mass and
        concentration parameter of an NFW profile.

        :returns:
            - **Rs_angle** (*numpy.ndarray*) -- Angle at scale radius (in units of arcsec).
            - **alpha_Rs** (*numpy.ndarray*) -- Observed bending angle at the scale radius (in units of arcsec). Arrays containing Rs_angle, alpha_Rs of all the Halos.
        """
        if n_halos is None:
            n_halos = self.n_halos
        if n_halos == 0:
            return [], []
        Rs_angle = []
        alpha_Rs = []
        if z is None:
            z = self.halos_redshift_list
        if mass is None:
            mass = self.mass_list
        assert len(z) == len(mass)
        if lens_cosmo is None:
            lens_cosmo = self.param_lens_cosmo
        if c is None:
            c = self.halos_list["c_200"]
        for h in range(n_halos):
            Rs_angle_h, alpha_Rs_h = lens_cosmo[h].nfw_physical2angle(M=mass[h], c=c[h])
            if isinstance(Rs_angle_h, Iterable):
                Rs_angle.extend(Rs_angle_h)
            else:
                Rs_angle.append(Rs_angle_h)

            if isinstance(alpha_Rs_h, Iterable):
                alpha_Rs.extend(alpha_Rs_h)
            else:
                alpha_Rs.append(alpha_Rs_h)

        Rs_angle = np.array(Rs_angle)
        Rs_angle = np.array(Rs_angle)
        return Rs_angle, alpha_Rs

    def get_halos_lens_kwargs(self):
        """Constructs and returns the list of keyword arguments for each halo to be used
        in the lens model for lenstronomy.

        :returns: kwargs_halos -- list of dicts. The list of dictionaries containing the
            keyword arguments for each halo.
        """

        if self.mass_sheet and self.n_correction > 0:
            Rs_angle, alpha_Rs = self.get_nfw_kwargs()
            #    first_moment = self.mass_first_moment
            #    kappa = self.kappa_ext_for_mass_sheet(self.mass_sheet_correction_redshift,
            #                                          self.param_lens_cosmo[-self.n_correction:], first_moment)
            kappa = self.mass_sheet_kappa
            ra_0 = [0] * self.n_correction
            dec_0 = [0] * self.n_correction
            kwargs_lens = [
                {
                    "Rs": Rs_angle[h],
                    "alpha_Rs": alpha_Rs[h],
                    "center_x": self.halos_list["px"][h],
                    "center_y": self.halos_list["py"][h],
                }
                for h in range(self.n_halos)
            ] + [
                {"kappa": kappa[h], "ra_0": ra_0[h], "dec_0": dec_0[h]}
                for h in range(self.n_correction)
            ]
        else:
            Rs_angle, alpha_Rs = self.get_nfw_kwargs()
            kwargs_lens = [
                {
                    "Rs": Rs_angle[h],
                    "alpha_Rs": alpha_Rs[h],
                    "center_x": self.halos_list["px"][h],
                    "center_y": self.halos_list["py"][h],
                }
                for h in range(self.n_halos)
            ]
        return kwargs_lens

    def filter_halos_by_redshift(self, zd, zs):
        """Filters halos and mass corrections by redshift conditions and constructs lens
        data.

        :param zd: Deflector redshift.
        :type zd: float
        :param zs: Source redshift. It should be greater than zd; otherwise, a ValueError is raised.
        :type zs: float
        :returns: A tuple containing lens data for three different conditions:
                  1. Between deflector and source redshift (ds).
                  2. From zero to deflector redshift (od).
                  3. From zero to source redshift (os).
        :rtype: tuple
        :raises ValueError: If the source redshift (zs) is less than the deflector redshift (zd).

        .. note::
            - Uses `_filter_halos_by_condition` to filter halos based on redshift conditions.
            - Uses `_filter_mass_correction_by_condition` to filter mass corrections based on redshift conditions.
            - Uses `_build_lens_data` to construct lens data for each condition.
        """

        halos_od, halos_ds, halos_os = self._filter_halos_by_condition(zd, zs)
        if zs < zd:
            raise ValueError(
                f"Source redshift {zs} cannot be less than deflector redshift {zd}."
            )
        (
            mass_correction_od,
            mass_correction_ds,
            mass_correction_os,
        ) = self._filter_mass_correction_by_condition(zd, zs)
        return (
            self._build_lens_data(halos_ds, mass_correction_ds, zd=zd, zs=zs),
            self._build_lens_data(halos_od, mass_correction_od, zd=0, zs=zd),
            self._build_lens_data(halos_os, mass_correction_os, zd=0, zs=zs),
        )

    def _filter_halos_by_condition(self, zd, zs):
        """Filters the halos based on redshift conditions relative to deflector and
        source redshifts.

        This internal method is designed to segregate halos into three categories:
        1. Between the deflector and source redshifts (ds).
        2. From zero redshift up to the deflector redshift (od).
        3. From zero redshift up to the source redshift (os).

        :param zd: Deflector redshift.
        :type zd: float
        :param zs: Source redshift.
        :type zs: float
        :returns: A tuple containing three DataFrames:
                  - halos_od (DataFrame): Halos with redshift less than the deflector redshift.
                  - halos_ds (DataFrame): Halos with redshift greater than or equal to the deflector redshift and less than the source redshift.
                  - halos_os (DataFrame): Halos with redshift less than the source redshift.
        :rtype: tuple

        .. note::
            This method assumes `self.halos_list` is a DataFrame containing a `z` column that represents the redshift of each halo.
        """

        halos_ds = self.halos_list[
            (self.halos_list["z"] >= zd) & (self.halos_list["z"] < zs)
        ]
        halos_od = self.halos_list[self.halos_list["z"] < zd]
        halos_os = self.halos_list[self.halos_list["z"] < zs]
        return halos_od, halos_ds, halos_os

    def _filter_mass_correction_by_condition(self, zd, zs):
        """Filters the mass corrections based on redshift conditions relative to
        deflector and source redshifts.

        This internal method segregates mass corrections into three categories:
        1. Between the deflector and source redshifts (ds).
        2. From zero redshift up to the deflector redshift (od).
        3. From zero redshift up to the source redshift (os).

        If `self.mass_correction_list` is {}, all returned values will be None.

        :param zd: Deflector redshift.
        :type zd: float
        :param zs: Source redshift.
        :type zs: float
        :return: A tuple containing:
                 - mass_correction_od (DataFrame or None): Mass corrections with redshift less than the deflector redshift.
                 - mass_correction_ds (DataFrame or None): Mass corrections with redshift greater than or equal to the deflector redshift and less than the source redshift.
                 - mass_correction_os (DataFrame or None): Mass corrections with redshift less than the source redshift.
        :rtype: tuple
        """

        if not self.mass_correction_list:
            return None, None, None
        mass_correction_ds = self.mass_correction_list[
            (self.mass_correction_list["z"] >= zd)
            & (self.mass_correction_list["z"] < zs)
        ]
        mass_correction_od = self.mass_correction_list[
            self.mass_correction_list["z"] < zd
        ]
        mass_correction_os = self.mass_correction_list[
            self.mass_correction_list["z"] < zs
        ]
        return mass_correction_od, mass_correction_ds, mass_correction_os

    def _build_lens_data(self, halos, mass_correction, zd, zs):
        """Constructs lens data based on the provided halos, mass corrections, and
        redshifts.

        :param halos: Contains information about the halos, including their redshift ('z`) and mass ('mass`).
        :type halos: DataFrame
        :param mass_correction: Contains information about the mass correction, including redshift ('z`) and kappa_ext ('kappa_ext`). If there's no mass correction, this can be None.
        :type mass_correction: DataFrame or None
        :param zd: Begin redshift.
        :type zd: float
        :param zs: End redshift.
        :type zs: float
        :returns: A tuple containing the constructed lens model based on the provided data, the list of lens cosmologies constructed from the combined redshift list, and the list of keyword arguments to define the lens model.
        :rtype: (object, list, list)
        :raises ValueError: - If source redshift (zs) is less than deflector redshift (zd).
                            - If any halo's redshift is smaller than the deflector redshift.
                            - If any halo's redshift is larger than the source redshift.

        .. note::
            The method consolidates halos and mass corrections to determine the redshift distribution of the lens model. It also takes into account certain conditions and constraints related to the redshifts of halos and the source.
        """

        n_halos = len(halos)
        n_mass_correction = (
            len(mass_correction)
            if mass_correction is not None and self.mass_sheet
            else 0
        )
        z_halo = halos["z"]
        mass_halo = halos["mass"]
        px_halo = halos["px"]
        py_halo = halos["py"]
        c_200_halos = halos["c_200"]

        if (
            (mass_correction is not None)
            and (len(mass_correction) > 0)
            and self.mass_sheet
        ):  # check
            z_mass_correction = mass_correction["z"]
            #    mass_first_moment = mass_correction["first_moment"]
            mass_correction_kappa = mass_correction["kappa"]
        else:
            z_mass_correction = []
            #    mass_first_moment = []
            mass_correction_kappa = []
        combined_redshift_list = np.concatenate((z_halo, z_mass_correction))
        # If this above code need to be changed, notice the change in the following code
        # including the lens_cosmo_dict one since it assume halos is in front of mass sheet
        if not combined_redshift_list.size:
            warnings.warn(
                f"No halos OR mass correction in the given redshift range from zd={zd} to zs={zs}."
            )
            return None, None, None
        if zs < zd:
            raise ValueError(
                f"Source redshift {zs} cannot be less than deflector redshift {zd}."
            )
        if min(combined_redshift_list) < zd:
            raise ValueError(
                f"Redshift of the farthest {min(combined_redshift_list)}"
                f" halo cannot be smaller than deflector redshift{zd}."
            )
        if max(combined_redshift_list) > zs:
            raise ValueError(
                f"Redshift of the closet halo {max(combined_redshift_list)} "
                f"cannot be larger than source redshift {zs}."
            )

        lens_cosmo_dict = self._build_lens_cosmo_dict(combined_redshift_list, zs)
        lens_model, lens_model_list = self._build_lens_model(
            combined_redshift_list, zs, n_halos
        )

        if (
            mass_correction is not None and len(mass_correction) > 0 and self.mass_sheet
        ):  # check
            #    kappa_ext_list = self.kappa_ext_for_mass_sheet(
            #        z_mass_correction, relevant_lens_cosmo_list, mass_first_moment
            #    )
            kappa_ext_list = mass_correction_kappa
        else:
            kappa_ext_list = []

        lens_cosmo_list = list(lens_cosmo_dict.values())
        kwargs_lens = self._build_kwargs_lens(
            n_halos,
            n_mass_correction,
            z_halo,
            mass_halo,
            px_halo,
            py_halo,
            c_200_halos,
            lens_model_list,
            kappa_ext_list,
            lens_cosmo_list,
        )
        return lens_model, lens_cosmo_list, kwargs_lens

    def _build_lens_cosmo_dict(self, combined_redshift_list, z_source):
        """Constructs a dictionary mapping each redshift to its corresponding LensCosmo
        instance.

        :param combined_redshift_list: List of redshifts representing the halos and mass
            corrections combined.
        :type combined_redshift_list: list or array-like
        :param z_source: Source redshift.
        :type z_source: float
        :returns: Dictionary mapping each redshift to its corresponding LensCosmo
            instance.
        :rtype: dict
        """

        return {
            z: LensCosmo(z_lens=z, z_source=z_source, cosmo=self.cosmo)
            for z in combined_redshift_list
        }

    def _build_lens_model(self, combined_redshift_list, z_source, n_halos):
        """Construct a lens model based on the provided combined redshift list, source
        redshift, and number of halos.

        The method generates a lens model list using `NFW` for halos and `CONVERGENCE` for any additional mass
        corrections present in the combined redshift list. The method ensures that the number of redshifts in the
        combined list matches the provided number of halos, and raises an error otherwise.

        :param combined_redshift_list: List of redshifts combining both halos and any additional mass corrections.
        :type combined_redshift_list: list or array-like
        :param z_source: The redshift of the source.
        :type z_source: float
        :param n_halos: The number of halos present in the combined redshift list.
        :type n_halos: int
        :returns: A tuple containing the constructed lens model based on the provided parameters and a list containing the lens model type (`NFW` or `CONVERGENCE`) for each redshift in the combined list.
        :rtype: (lenstronomy.LensModel, list of str)
        :raises ValueError: If the length of the combined redshift list does not match the specified number of halos.

        .. note::
            The order of the lens model list is constructed as:
            [`NFW`, `NFW`, ..., `CONVERGENCE`, `CONVERGENCE`, ...],
            where the number of `NFW` entries matches `n_halos` and the number of `CONVERGENCE` entries corresponds
            to any additional redshifts present in `combined_redshift_list`.
        """

        n_halos = n_halos

        if len(combined_redshift_list) - n_halos > 0:
            lens_model_list = ["NFW"] * n_halos + ["CONVERGENCE"] * (
                len(combined_redshift_list) - n_halos
            )
        elif len(combined_redshift_list) - n_halos < 0:
            raise ValueError(
                f"Combined redshift list shorter than number of halos."
                f"{len(combined_redshift_list)} < {n_halos}"
            )
        elif n_halos == len(combined_redshift_list) == 0:
            lens_model_list = ["NFW"] * 1
        else:
            lens_model_list = ["NFW"] * n_halos
        lens_model = LensModel(
            lens_model_list=lens_model_list,
            lens_redshift_list=combined_redshift_list,
            cosmo=self.cosmo,
            multi_plane=True,
            z_source=z_source,
            z_source_convention=self._z_source_convention,
        )
        return lens_model, lens_model_list

    def _build_kwargs_lens(
        self,
        n_halos,
        n_mass_correction,
        z_halo,
        mass_halo,
        px_halo,
        py_halo,
        c_200_halos,
        lens_model_list,
        kappa_ext_list,
        lens_cosmo_list,
    ):
        """Constructs the lens keyword arguments based on provided input parameters.

        Based on the provided numbers of halos and mass corrections, redshifts, masses, and lens models, this method
        assembles the lensing keyword arguments needed for the lens model. It caters for cases with and without
        `CONVERGENCE` in the lens model list.

        :param n_halos: Number of halos.
        :type n_halos: int
        :param n_mass_correction: Number of mass corrections.
        :type n_mass_correction: int
        :param z_halo: List of redshifts of halos.
        :type z_halo: list or array-like
        :param mass_halo: List of halo masses.
        :type mass_halo: list or array-like
        :param px_halo: List of x positions of halos.
        :type px_halo: list or array-like
        :param py_halo: List of y positions of halos.
        :type py_halo: list or array-like
        :param lens_model_list: List of lens models (`NFW`, `CONVERGENCE`, etc.).
        :type lens_model_list: list of str
        :param kappa_ext_list: List of external convergence values.
        :type kappa_ext_list: list or array-like
        :param lens_cosmo_list: List of param_lens_cosmo instances.
        :type lens_cosmo_list: list

        :returns: A list of dictionaries, each containing the keyword arguments for each lens model.
        :rtype: list of dict

        .. note::
            This method assumes the presence of a method `get_nfw_kwargs` in the current class that provides NFW parameters
            based on given redshifts and masses.
        """

        if n_halos == 0 and ("CONVERGENCE" not in lens_model_list):
            return None
        elif n_halos == 0 and ("CONVERGENCE" in lens_model_list):
            return [
                {"kappa": kappa_ext_list[h], "ra_0": 0, "dec_0": 0}
                for h in range(n_mass_correction)
            ]
        if n_halos != 0:
            assert len(z_halo) == len(lens_cosmo_list[:n_halos])
        Rs_angle, alpha_Rs = self.get_nfw_kwargs(
            z=z_halo,
            mass=mass_halo,
            n_halos=n_halos,
            lens_cosmo=lens_cosmo_list[:n_halos],
            c=c_200_halos,
        )
        # TODO: different param_lens_cosmo ( for halos and sheet )

        if "CONVERGENCE" in lens_model_list:
            return [
                {
                    "Rs": Rs_angle[i],
                    "alpha_Rs": alpha_Rs[i],
                    "center_x": px_halo[i],
                    "center_y": py_halo[i],
                }
                for i in range(n_halos)
            ] + [
                {"kappa": kappa_ext_list[h], "ra_0": 0, "dec_0": 0}
                for h in range(n_mass_correction)
            ]

        return [
            {
                "Rs": Rs_angle[i],
                "alpha_Rs": alpha_Rs[i],
                "center_x": px_halo[i],
                "center_y": py_halo[i],
            }
            for i in range(n_halos)
        ]

    def get_lens_data_by_redshift(self, zd, zs):
        """Retrieves lens data filtered by the specified redshift range.

        Given a range of redshifts defined by zd and zs, this function filters halos
        and returns the corresponding lens models, lens cosmologies, and lens keyword arguments
        for three categories: `ds`, `od`, and `os`. ('ds` stands for deflector-source, `od` stands for
        observer-deflector, and `os` stands for observer-source.)

        :param zd: The deflector redshift. It defines the lower bound of the redshift range.
        :type zd: float
        :param zs: The source redshift. It defines the upper bound of the redshift range.
        :type zs: float
        :return: A dictionary with three keys: `ds`, `od`, and `os`. Each key maps to a sub-dictionary containing:
                 - `param_lens_model`: The lens model for the corresponding category.
                 - `param_lens_cosmo`: The lens cosmology for the corresponding category.
                 - `kwargs_lens`: The lens keyword arguments for the corresponding category.
        :rtype: dict

        .. note::
            lens_model_ds = lens_data['ds`]['param_lens_model`]
            lens_cosmo_ds = lens_data['ds`]['param_lens_cosmo`]
            kwargs_lens_ds = lens_data['ds`]['kwargs_lens`]
             ... and similarly for `od` and `os` data
        """

        ds_data, od_data, os_data = self.filter_halos_by_redshift(zd, zs)

        lens_model_ds, lens_cosmo_ds, kwargs_lens_ds = ds_data
        lens_model_od, lens_cosmo_od, kwargs_lens_od = od_data
        lens_model_os, lens_cosmo_os, kwargs_lens_os = os_data

        return {
            "ds": {
                "param_lens_model": lens_model_ds,
                "param_lens_cosmo": lens_cosmo_ds,
                "kwargs_lens": kwargs_lens_ds,
            },
            "od": {
                "param_lens_model": lens_model_od,
                "param_lens_cosmo": lens_cosmo_od,
                "kwargs_lens": kwargs_lens_od,
            },
            "os": {
                "param_lens_model": lens_model_os,
                "param_lens_cosmo": lens_cosmo_os,
                "kwargs_lens": kwargs_lens_os,
            },
        }

    def halos_get_convergence_shear(
        self,
        same_from_class=True,
        gamma12=False,
        diff=1.0,
        diff_method="square",
        kwargs=None,
        lens_model=None,
        zdzs=None,
    ):
        if self.n_halos == 0:
            is_nan = np.isnan(self.halos_list["z"])
            if is_nan:
                if gamma12:
                    return 0.0, 0.0, 0.0
                else:
                    return 0.0, 0.0
        if kwargs is None:
            kwargs = self.get_halos_lens_kwargs()
        if lens_model is None:
            lens_model = self.param_lens_model
        HRT = HalosRayTracing(lens_model, kwargs)
        return HRT.get_convergence_shear(
            gamma12=gamma12,
            diff=diff,
            diff_method=diff_method,
            kwargs=kwargs,
            lens_model=lens_model,
            zdzs=zdzs,
            same_from_class=same_from_class,
        )

    def compute_various_kappa_gamma_values(self, zd, zs):
        if self.n_halos == 0:
            is_nan = np.isnan(self.halos_list["z"])
            if is_nan:
                return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0

        lens_data = self.get_lens_data_by_redshift(zd, zs)
        HRT = HalosRayTracing(lens_kwargs=None, lens_model=None)
        return HRT.nonlinear_correction_kappa_gamma_values(
            lens_data=lens_data, zd=zd, zs=zs
        )

    def halos_get_kext_gext_values(self, zd, zs):
        lens_data = self.get_lens_data_by_redshift(zd, zs)
        HRT = HalosRayTracing(lens_kwargs=None, lens_model=None)
        return HRT.get_kext_gext_values(lens_data=lens_data, zd=zd, zs=zs)

    def halos_compute_kappa(
        self,
        diff=0.0000001,
        num_points=500,
        diff_method="square",
        mass_sheet_bool=None,
        enhance_pos=False,
    ):

        sky_area = self.sky_area
        kwargs = self.get_halos_lens_kwargs()
        lens_model = self.param_lens_model
        if mass_sheet_bool is not None:
            self.mass_sheet = mass_sheet_bool

        HRT = HalosRayTracing(lens_model, kwargs)
        kappa_image, kappa_values = HRT.compute_kappa(
            sky_area=sky_area,
            diff=diff,
            num_points=num_points,
            diff_method=diff_method,
            kwargs=kwargs,
            lens_model=lens_model,
        )
        if enhance_pos:
            self.enhance_halos_table_random_pos()
        return kappa_image, kappa_values

    def plot_halos_convergence(
        self,
        diff=0.0000001,
        num_points=500,
        diff_method="square",
        mass_sheet=None,
        enhance_pos=True,
    ):

        sky_area = self.sky_area
        original_mass_sheet = self.mass_sheet

        try:
            if mass_sheet is not None:
                self.mass_sheet = mass_sheet
            kwargs = self.get_halos_lens_kwargs()
            self._lens_model = None
            lens_model = self.param_lens_model
            HRT = HalosRayTracing(lens_model, kwargs)
            HRT.plot_convergence(
                sky_area=sky_area,
                diff=diff,
                num_points=num_points,
                diff_method=diff_method,
                kwargs=kwargs,
                lens_model=lens_model,
            )
        finally:
            self.mass_sheet = original_mass_sheet
            if enhance_pos:
                self.enhance_halos_table_random_pos()

    def halos_compare_plot_convergence(
        self,
        diff=0.0000001,
        diff_method="square",
    ):

        print("mass_sheet=False")

        # mass_sheet=False
        self.plot_halos_convergence(
            diff=diff,
            diff_method=diff_method,
            mass_sheet=False,
            enhance_pos=False,
        )
        print("mass_sheet=True")
        self.plot_halos_convergence(
            diff=diff,
            diff_method=diff_method,
            mass_sheet=True,
            enhance_pos=False,
        )

    def enhance_halos_pos_to0(self):
        n_halos = self.n_halos
        px = np.array([0 for _ in range(n_halos)]).T
        py = np.array([0 for _ in range(n_halos)]).T
        # Adding the computed attributes to the halos table
        self.halos_list["px"] = px
        self.halos_list["py"] = py

    def halos_various_halos_data(self, zd, zs):
        lens_data = self.get_lens_data_by_redshift(zd, zs)
        HRT = HalosRayTracing(lens_kwargs=[], lens_model=[])
        return HRT.various_halos_data(lens_data=lens_data, zd=zd, zs=zs)
