Where is the cube-config?



We are planning to use the NetCDF provider and prepare our Geotiffs by using
gdalwarp.

After preprocessing we need to use the spatialist stack function to prepare the geotiffs and crop them to one grid.


To convert all geotiffs in a folder, use the following snippet in the shell.
```
for file in *.tif; do
  gdalwarp "$file" "${file%.*}.nc" -of NetCDF -co FORMAT=NC4 -dstnodata 0 -srcnodata 0
done
```

We can use our version of esdl_core to generate a Sentinel1 cube with the command
```
cube-gen s1cube_1day sentinel1:dir=/media/data/sen4redd/netcdf_test/ -c s1_config
```
