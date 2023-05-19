import warnings

import gsw
import numpy as np
import xarray as xr
import xgcm

def Jlammass_from_Qm_lamf_lam(Qm, lamf, lam):
    """
    Calculate lambda tendency associated with a mass flux.
    
    Parameters
    -----
    Qm : xarray.DataArray
        massflux (e.g., wfo)
    lamf : xarray.DataArray
        Scalar value of mass flux (e.g., tos, 0)
    lam : xarray.DataArray
        Scalar field of ocean value (e.g., thetao, so)
    """
    return Qm * (lamf - lam)

def hlamdot_from_Jlam(grid, Jlam, dim):
    """
    Calculation of hlamdot (cell-depth integral of scalar tendency)
    provided various forms of input (fluxes, tendencies, intensive, extensive)
    """
    # For convergence, need to reverse the sign
    dJlam = -grid.diff(Jlam, dim)
    if "Z_metrics" in list(vars(grid)):
        h = grid.Z_metrics["center"]
        h = h.where(h!=0.)
    else:
        h = grid.get_metric(dJlam, "Z")
    lamdot = dJlam/h
    hlamdot = h.fillna(0.)*lamdot.fillna(0.)
    return hlamdot

def calc_hlamdotmass(grid, datadict):
    """
    Wrapper functions for boundary flux.
    """
    hlamdotmass = datadict["boundary"]["flux"]
    # If boundary flux specified as mass rather than tracer flux
    if datadict["boundary"]["mass"]:
        scalar_i = grid.interp(
            datadict["scalar"]["array"],
            "Z",
            boundary="extend"
        ).chunk({grid.axes['Z'].coords['outer']: -1})
        Jlammass = Jlammass_from_Qm_lamf_lam(
            hlamdotmass,
            datadict["boundary"]["scalar_in_mass"],
            scalar_i
        )
        hlamdotmass = hlamdot_from_Jlam(
            grid,
            Jlammass,
            dim="Z"
        )
    return hlamdotmass

def hlamdot_from_Ldot_hlamdotmass(Ldot, hlamdotmass=None):
    """
    Advective surface flux
    """
    if hlamdotmass is not None:
        return Ldot + hlamdotmass.fillna(0)
    return Ldot

def hlamdot_from_lamdot_h(lamdot, h):
    return h * lamdot

def calc_hlamdot_tendency(grid, datadict):
    """
    Wrapper functions to determine h times lambda_dot (vertically extensive tendency)
    """

    if datadict["tendency"]["extensive"]:
        hlamdotmass = None

        if datadict["tendency"]["boundary"]:
            hlamdotmass = calc_hlamdotmass(grid, datadict)
            hlamdot = hlamdot_from_Ldot_hlamdotmass(
                hlamdot_from_Jlam(
                    grid,
                    datadict["tendency"]["array"],
                    dim="Z"
                ),
                hlamdotmass
            )
        else:
            hlamdot = hlamdot_from_Ldot_hlamdotmass(
                datadict["tendency"]["array"],
                hlamdotmass
            )
    else:
        hlamdot = hlamdot_from_lamdot_h(
            datadict["tendency"]["array"],
            grid.Z_metrics["center"]
        )
    return hlamdot

def bin_define(lmin, lmax, delta_l):
    """Specify the range and widths of the lambda bins"""
    return np.arange(lmin - delta_l / 2.0, lmax + delta_l / 2.0, delta_l)