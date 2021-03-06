#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Convert ERA-Interim Sea-level pressure to Inverse Barometer Effect (IBE).

Reads an Era-Interim (NetCDF) mean sea level product in Pa, msl(t,y,x),
and generates a (HDF5) IBE product in meters.

Example:
    slp2ibe.py SLP_antarctica_3h_19900101_20171031.nc

Notes:
    The sea level increases (decreases) by approximately 1 cm when air
    pressure decreases (increases) by approximately 1 mbar. The inverse
    barometer correction (IBE) that must be subtracted from the sea surface
    height is simply given by:

        h_ibe = (-1/rho g) * (P - P_ref)

    where Pref is the global "mean" pressure (reference pressure) over the
    ocean (rho is sea water density and g gravity). For most applications,
    Pref is assumed to be a constant (e.g., 1013.3 mbar).

    Dorandeu and Le Traon (1999), https://goo.gl/Sb8XcE

    Our correction is defined as:

        h_ibe(x,y,t) = (-1/rho g) * [P(x,y,t) - P_ref(x,y)]

    where P_ref(x,y) is the climatological mean at each location.

    The IBE correction should be applied as:

        h_cor = h - h_ibe

References:
    https://link.springer.com/chapter/10.1007/978-3-662-04709-5_88

Test:
    To test if the downloaded MSLP data is correct, uncomment the 'Test'
    section in the code and compare the plots with the ones provided.

Download:
    Download the latest Era-Int MSLP and generate a new IBE product.
    See how on ibe/README.txt and ibe/geteraint.py.

"""
import sys

import h5py
import numpy as np
from netCDF4 import Dataset

# Default sea-level pressure file (Era-Interim)
# This can be passed as command-line arg.
SLPFILE = "SLP_antarctica_3h_19900101_20170331.nc"

# Default variable names in the IBE NetCDF file
XIBE = "longitude"
YIBE = "latitude"
TIBE = "time"
ZIBE = "msl"


def slp_to_ibe(P, rho=1028.0, g=9.80665, P_ref=None):
    """
    Convert sea-level pressure [Pa] to inverse barometer correction [m].

        h_ibe(x,y,t) = -1/(rho g) (P(x,y,t) - P_ref(x,y))

    Args:
        P: pressure at sea level [Pa = kg/m.s2]; P(t,y,x).
        rho: density of sea water [kg/m3].
        g: gravity [m/s2].
        P_ref: reference pressure, the climatological mean: P_ref(y,x).
            If P_ref is not None (e.g. the mean global pressure is given:
            1013.25 * 100 [Pa]), then P_ref = const.
    """
    P_ref = np.nanmean(P, axis=0)  # P = P(t,y,x)
    h_ibe = (-1 / (rho * g)) * (P - P_ref[np.newaxis, :, :])  # m

    return h_ibe


def main():

    infile = sys.argv[1] if sys.argv[1:] else SLPFILE

    # Read NetCDF
    print("loading SLP file ...")
    ds = Dataset(infile, "r")

    lon = ds.variables[XIBE][:]  # [deg]
    lat = ds.variables[YIBE][:]  # [deg]
    time = ds.variables[TIBE][:]  # [hours since 1900-01-01 00:00:0.0]
    msl = ds.variables[ZIBE]  # [:]  # msl(t,y,x) [Pa]; WARNING: data too big!

    # NOTE: Do not apply these! The netCDF4 module applies it at read time!
    scale = getattr(ds["msl"], "scale_factor")
    offset = getattr(ds["msl"], "add_offset")
    missing = getattr(ds["msl"], "missing_value")

    # --- Test ----------------------------------------------
    # Subset region for testing (inclusive)
    # Do not load full data into memory

    if 0:

        # Filter time
        time = time / 8760.0 + 1900  # hours since 1900 -> years

        # Plot
        # import pandas as pd
        import matplotlib.pyplot as plt

        find_nearest = lambda arr, val: (np.abs(arr - val)).argmin()

        # Larsen-C Ice Shelf plot
        j = find_nearest(lon, (297.5 - 360))
        i = find_nearest(lat, -67.5)

        p = msl[:, i, j]
        p = (-1 / (1028.0 * 9.80665)) * (p - np.mean(p))  # m
        t = (time - 2007) * 365 - 26  # 26 Leap days from 1900 to 2007

        plt.figure()
        plt.plot(t, p, linewidth=2)
        plt.title("Larsen-C Ice Shelf (297.5, -67.5)")
        plt.xlabel("Days of year 2007")
        plt.ylabel("Inverse Barometer Effect (m)")
        plt.xlim(324.753, 388.66)
        plt.ylim(-0.3, 0.4)

        # Brunt Ice Shelf plot
        j = find_nearest(lon, (333.3 - 360))
        i = find_nearest(lat, -75.6)

        p = msl[:, i, j]
        p = (-1 / (1028.0 * 9.80665)) * (p - np.mean(p))  # m
        t = (time - 2000) * 365 - 25  # 25 Leap days from 1900 to 2000

        plt.figure()
        plt.plot(t, p, linewidth=2)
        plt.title("Brunt Ice Shelf (333.3, -75.6)")
        plt.xlabel("Days of year 2000")
        plt.ylabel("Inverse Barometer Effect (m)")
        plt.xlim(100, 160)
        plt.ylim(-0.3, 0.2)

        plt.show()
        sys.exit()

    print("variables:", ds.variables)
    print("Resolution:")
    print("delta lon (deg):", np.diff(lon))
    print("delta lat (deg):", np.diff(lat))
    print("delta time (hours):", np.diff(time))
    print("time steps:", time)
    print("msl pressure:", msl)
    print("scale_factor:", scale)
    print("add_offset:", offset)
    print("missing_value:", missing)

    # Convert sea-level pressure to inverse barometer correction
    print("converting SLP to IBE ...")
    ibe = slp_to_ibe(msl)

    # Save data
    outfile = infile.replace("SLP_", "IBE_").replace(".nc", ".h5")

    with h5py.File(outfile, "w") as f:
        kw = {"chunks": True, "compression": "gzip", "compression_opts": 9}
        f.create_dataset("lon", data=lon, **kw)
        f.create_dataset("lat", data=lat, **kw)
        f.create_dataset("time", data=time, **kw)
        f.create_dataset("ibe", data=ibe, **kw)

    print("Output file:", outfile)


if __name__ == "__main__":
    main()
