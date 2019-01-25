#!/usr/bin/env python3
from __future__ import print_function
import glob
import sys
import numpy as np
import datetime as dt
import os
import gdal
import osr
import netCDF4
import re
import argparse
import pytz


def utctimestamp(dtobj):
    """Calculate a UNIX timestamp for a given datetime object. Localizes the datetime object to UTC if necessary.

    Warning: Dates without timezone info are considered to be UTC.

    :param dtobj: a datetime object
    :return: UNIX timestamp as integer seconds since 1970-01-01 00:00:00 UTC
    """

    # if dtobj has no timezone, we assume it to be UTC
    if dtobj.tzinfo is None:
        dtobj = pytz.utc.localize(dtobj)

    if sys.version_info >= (3, 3):
        return dtobj.timestamp()

    return (dtobj - dt.datetime(1970, 1, 1, 0, 0, 0, 0, pytz.UTC)).total_seconds()

def create_nc(path, dest_file):



def create_timestack(src_dir, dest_file,
                     update_existing = False, verbose = False):
    """Create a time series in NetCDF format from Sentinel-1 scenes.

    Create a time series from Sentinel-1 GeoTiff scenes in <src_dir> and write
    it into NetCDF file <dest_file>. If the destination file already exists, it
    is overwritten by default. To change this behaviour, set <update_existing>
    to True. The scenes are assumed to have the same size and their CRS is
    EPSG:4326.

    :param src_dir: a directory containing Sentinel-1 scenes in GeoTiff format
    :param dest_file: a filepath for the destination NetCDF file
    :param update_existing: set to True, to have the destination file updated
                            if it exists; default value: False
    :param verbose: set to True to get more verbose output; default value:
                    False
    :return: 0 on success, 1 on error
    """
    const_polarizations = ['vv', 'vh', 'hv', 'hh']
    const_orb_flags = {'A': 0b0, 'D': 0b1}

    src_dir = os.path.abspath(src_dir)
    if not os.path.exists(src_dir):
        raise FileNotFoundError
    if not os.path.isdir(src_dir):
        raise NotADirectoryError

    # get all GeoTiffs in a list with full paths
    scene_list = glob.glob(src_dir + os.sep + '*.tif')

    if len(scene_list) == 0:
        print("No scenes to process, exiting.", file=sys.stderr)
        return 1

    print("Found {0} scenes to process.".format(len(scene_list)))

    # compiling regex pattern for orbit code
    orbit_pattern = re.compile('S1[AB]__IW___([AD])')
    # compiling regex pattern for dates of the format %Y%m%hT%H%M%S,
    # used in the following command and further down
    date_pattern = re.compile('(\\d{8}T\\d{6})')
    # compiling regex pattern for matching polarization abbreviations
    pol_pattern = re.compile('(' + '|'.join(const_polarizations).upper() + ')')
    # when reading in scenes, combination of both patterns is necessary
    filename_pattern = re.compile(orbit_pattern.pattern + '_' + date_pattern.pattern + '_' + pol_pattern.pattern)

    # sort scenes according to their recording date
    scene_list.sort(key=lambda x: re.search(date_pattern, x).group())

    # make use of GDAL exception mechanism
    gdal.UseExceptions()

    # absolutize path of the destination file
    dest_file = os.path.abspath(dest_file)
    if os.path.exists(dest_file) & update_existing:
        # file exists and user wants to update it
        try:
            nc_file = netCDF4.Dataset(dest_file, 'a')
        except Exception as e:
            print(e, file=sys.stderr)
            return 1

        # require all 4 dimensions to exist in the file
        dimdiff = {'lon', 'lat', 'time', 'scene_index'} - set(nc_file.dimensions.keys())
        if len(dimdiff) > 0:
            for dim in dimdiff:
                print("Error: Missing dimension '{0}' in '{1}'."
                      .format(dim, dest_file), file=sys.stderr)
            print("Aborting to prevent modifying the wrong file.",
                  file=sys.stderr)
            return 1

        # all dimension and non back scatter value variables must exist
        has_missing_var = False
        for varname in ['lon', 'lat', 'time', 'crs', 'scene_index', 'scene_list', 'orbit']:
            if varname not in nc_file.variables.keys():
                print("Error: Missing variable '{0}' in '{1}'."
                      .format(varname, dest_file), file=sys.stderr)
                has_missing_var = True

        if has_missing_var:
            print("Aborting to prevent modifying the wrong file.",
                  file=sys.stderr)
            return 1

        # read the back scatter intensity variables from the NetCDF
        bsi = dict()
        for pol in const_polarizations:
            varname = "bsi_{0}".format(pol)
            if varname in nc_file.variables.keys():
                bsi[pol] = nc_file.variables[varname]
                print("Found variable '{0}'.".format(varname))

        if bsi == dict():
            print("Error: No backscatter values found.", file=sys.stderr)
            print("Aborting to prevent modifying the wrong file.",
                  file=sys.stderr)
            return 1

        # read time from NetCDF
        time_var = nc_file.variables["time"]

        # read orbit values from NetCDF
        orbit_var = nc_file.variables["orbit"]

        # read scene index and list from NetCDF
        scene_index_var = nc_file.variables["scene_index"]
        scene_index_offset = scene_index_var.size
        scene_list_var = nc_file.variables["scene_list"]

        # create the date lookup table, containing a combination of the dates already in the NetCDF file
        # and those of scenes that are to be read in
        scene_dates = [netCDF4.num2date(x, time_var.units).strftime("%Y%m%dT%H%M%S") for x in time_var]
        file_dates = set([re.search(date_pattern, x).group() for x in
                         scene_list])
        additional_dates = file_dates - (set(scene_dates) & file_dates)
        scene_dates.extend(sorted(additional_dates))
        date_lut = dict(zip(scene_dates, range(0, len(scene_dates))))
        # there might be polarizations not yet stored in the file
        polarizations = set([re.search(filename_pattern, x).group(3) for x in
                             scene_list])

        for pol in (set(const_polarizations) & set(polarizations)) - bsi.keys():
            bsi[pol] = nc_file.createVariable("bsi_{0}".format(pol), 'f4',
                                              ('time', 'lat', 'lon'),
                                              zlib=True, fill_value=0)
            bsi[pol].units = '1'
            bsi[pol].standard_name = 'backscatter intensity {0}'.format(pol.upper())
            bsi[pol].grid_mapping = 'crs'
            bsi[pol].set_auto_maskandscale(False)

        for scene_index, scene in enumerate(scene_list):
            if os.path.basename(scene) in scene_list_var:
                print("Skipping scene '{0}' because it is already included.".format(scene))
                continue

            # retrieve date and polarization from filename
            match = re.search(filename_pattern, scene)

            if match:
                (orbstr, dtstr, polstr) = match.groups()

                # parse date into datetime object
                dtobj = dt.datetime.strptime(dtstr, "%Y%m%dT%H%M%S")
                if verbose:
                    print("Processing scene from {0}"
                          .format(dtobj.strftime("%Y-%m-%d %H:%M:%S")))
                dtime = int(utctimestamp(dtobj))

                time_index = date_lut[dtstr]
                # extend time dimension
                time_var[time_index] = dtime
                orbit_var[time_index] = const_orb_flags[orbstr] if orbstr in const_orb_flags.keys() else -128

                if verbose:
                    print("File: {0}".format(scene))

                # open scene
                try:
                    bsi_ds = gdal.Open(scene, gdal.GA_ReadOnly)
                except RuntimeError as e:
                    print("Could not open {0}".format(scene), file=sys.stderr)
                    print(e, file=sys.stderr)
                    nc_file.close()
                    return 1

                # read its back scatter values
                a = bsi_ds.ReadAsArray()
                # transpose is necessary, because we insert in order: time,
                # lon, lat
                bsi[polstr.lower()][time_index, :, :] = np.transpose(a)

                # close GDAL dataset
                bsi_ds = None

                # casting to int necessary, because otherwise netCDF complains (why?)
                new_scene_index = int(scene_index + scene_index_offset)
                scene_index_var[new_scene_index] = new_scene_index
                scene_list_var[new_scene_index] = os.path.basename(scene)

        nc_file.close()
        print("NetCDF file {0} successfully updated.".format(dest_file))
    else:
        # either the file does not exist or shall be overwritten

        # get same basic information, e.g. size from oldest scene
        try:
            ds = gdal.Open(scene_list[0], gdal.GA_ReadOnly)
        except RuntimeError as e:
            print("Unable to open " + scene_list[0], file=sys.stderr)
            print(e, file=sys.stderr)
            return 1

        # NOTE: X is column count, Y is row count
        nlat, nlon = ds.RasterXSize, ds.RasterYSize

        # create the lat-lon grid
        b = ds.GetGeoTransform()
        lon = np.arange(nlon) * b[1] + b[0]
        lat = np.arange(nlat) * b[5] + b[3]

        # close scene
        ds = None

        try:
            nc_file = netCDF4.Dataset(dest_file, 'w', clobber=True,
                                      format='NETCDF4')
        except Exception as e:
            print(e, file=sys.stderr)
            return 1

        # create the 3 dimensions with correct size (time is unlimited)
        nc_file.createDimension('lon', nlon)
        nc_file.createDimension('lat', nlat)
        nc_file.createDimension('time', None)
        nc_file.createDimension('scene_index', None)

        # the time variable
        time_var = nc_file.createVariable('time', 'i4', ('time'))
        time_var.units = 'seconds since 1970-01-01 00:00:00'
        time_var.standard_name = 'time'

        # the longitude variable
        longitude_var = nc_file.createVariable('lon', 'f8', ('lon'))
        longitude_var.units = 'degrees_east'
        longitude_var.standard_name = 'longitude'

        # the latitude variable
        latitude_var = nc_file.createVariable('lat', 'f8', ('lat'))
        latitude_var.units = 'degrees_north'
        latitude_var.standard_name = 'latitude'

        scene_index_var = nc_file.createVariable('scene_index', 'i4', ('scene_index'))
        scene_index_var.units = '1'
        scene_index_var.standard_name = 'scene index'

        # the CRS and associated attributes
        spatial_ref = osr.SpatialReference()
        spatial_ref.ImportFromEPSG(4326)
        crs_var = nc_file.createVariable('crs', 'i4')
        crs_var.standard_name = 'Lon/Lat Coords in WGS84'
        crs_var.grid_mapping_name = 'latitude_longitude'
        crs_var.longitude_of_prime_meridian = 0.0
        crs_var.semi_major_axis = spatial_ref.GetSemiMajor()
        crs_var.inverse_flattening = spatial_ref.GetInvFlattening()
        crs_var.spatial_ref = spatial_ref.ExportToWkt()

        orbit_var = nc_file.createVariable('orbit', 'i1', ('time'), fill_value=-128)
        orbit_var.flag_values = list(const_orb_flags.values())
        orbit_var.flag_meanings = " ".join(const_orb_flags.keys())
        orbit_var.standard_name = 'Orbit (Ascending/Descending)'

        scene_list_var = nc_file.createVariable('scene_list', str, ('scene_index'))
        scene_list_var.units = '1'
        scene_list_var.standard_name = 'File names of the stored scenes'

        file_dates = set([re.search(date_pattern, x).group() for x in
                         scene_list])
        date_lut = dict(zip(sorted(file_dates), range(0, len(file_dates))))
        polarizations = set([re.search(filename_pattern, x).group(3) for x in
                             scene_list])

        bsi = dict()
        for pol in polarizations:
            pol = pol.lower()
            bsi[pol] = nc_file.createVariable("bsi_{0}".format(pol), 'f4',
                                              ('time', 'lat', 'lon'),
                                              zlib=True, fill_value=0)
            bsi[pol].units = '1'
            bsi[pol].standard_name = 'backscatter intensity {0}'.format(pol)
            bsi[pol].grid_mapping = 'crs'
            bsi[pol].set_auto_maskandscale(False)

        # the NetCDF file follows version 1.7 of the CF Convention
        nc_file.Conventions = 'CF-1.7'

        # populate the longitude and latitude variables with values
        longitude_var[:] = lon
        latitude_var[:] = lat

        for scene_index, scene in enumerate(scene_list):
            # retrieve date and polarization from filename
            match = re.search(filename_pattern, scene)

            if match:
                (orbstr, dtstr, polstr) = match.groups()

                # convert date str into datetime object
                dtobj = dt.datetime.strptime(dtstr, "%Y%m%dT%H%M%S")
                if verbose:
                    print("Processing scene from {0}"
                          .format(dtobj.strftime("%Y-%m-%d %H:%M:%S")))
                dtime = int(utctimestamp(dtobj))

                time_index = date_lut[dtstr]
                # extend time dimension
                time_var[time_index] = dtime
                # write orbit
                orbit_var[time_index] = const_orb_flags[orbstr] if orbstr in const_orb_flags.keys() else -128

                if verbose:
                    print("File: {0}".format(scene))

                # open scene
                try:
                    bsi_ds = gdal.Open(scene, gdal.GA_ReadOnly)
                except RuntimeError as e:
                    print("Could not open {0}".format(scene), file=sys.stderr)
                    print(e, file=sys.stderr)
                    nc_file.close()
                    return 1

                # read its back scatter values
                a = bsi_ds.ReadAsArray()
                # transpose is necessary, because we insert in order: time,
                # lon, lat
                bsi[polstr.lower()][time_index, :, :] = np.transpose(a)

                # close GDAL dataset
                bsi_ds = None

                scene_index_var[scene_index] = scene_index
                scene_list_var[scene_index] = os.path.basename(scene)
        nc_file.time_coverage_start = time_var[0]
        nc_file.time_coverage_end   = time_var[-1]
        nc_file.close()
        print("NetCDF file {0} successfully created.".format(dest_file))

    return 0


def main():
    # feed options and arguments into the parser
    parser = argparse.ArgumentParser(description="Create a NetCDF time " +
                                     "series from Sentinel-1 GeoTiff scenes." +
                                     " All GeoTiffs MUST have the same " +
                                     "raster size, bounding box and CRS.")
    parser.add_argument("scene_directory", help="directory containing " +
                        "Sentinel-1 scenes in GeoTiff format", type=str,
                        metavar="SOURCE")
    parser.add_argument("-o", "--output", required=True, help="path of the " +
                        "output file", nargs=1, metavar="FILE", type=str)
    parser.add_argument("-u", "--update", help="if the destination file " +
                        "exists, update it", required=False,
                        action="store_true")
    parser.add_argument("-v",  "--verbose", help="give detailed output",
                        required=False, action="store_true")
    # evaluate options and arguments the user used
    args = parser.parse_args()
    # launch the stacking with the parsed options and arguments
    return create_timestack(src_dir=args.scene_directory,
                            dest_file=args.output[0],
                            update_existing=args.update, verbose=args.verbose)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(e, file=sys.stderr)
        sys.exit(1)
