# Sentinel-1 ESDL Datacubes 
## Contribution to the ESDL Early Adopter Call

This is the repository with the scripts and the report for the Earth System Data Laboratory (ESDL) adopter call.
The idea is, to use the ESDL package to handle the large data sets of Sentinel-1 data. 

In the generation folder you find everything to the generation of the Sentinel-1 data cubes and the needed preparation steps. 
The report folder contains the .tex file and the figures for the report. 

The Notebooks assume, that the original cube is in a cubes folder, this folder is not submitted, because of the size. 

The sentinel-1 cube is till 2019/10/18 available at 
https://upload.uni-jena.de/data/5d30ccbdd88bc1.12453671/s1cube_1dayallzarrbbnew.tar.gz

The Plotting notebook is not yet tested with the zarr cube, because the save cube function did not work. 

