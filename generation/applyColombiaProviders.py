import esdl
from biounits import ColBioUnitsProvider
from canopyheight import ColCanopyHeightProvider
#from clouds import ColCloudsProvider
#from nwds import ColNWSDProvider
#from worldclim import ColWorldClimProvider
#from fparv2 import ColFpar2Provider
from gppseoul import ColGPPProvider
from generalProv import ColProvider
#from chelsaT import ColChelsaTProvider
#from chelsaPrec import ColChelsaPrecProvider
from ColombiaStatic import StaticBGCProvider
from os.path import isdir
import os

import sys, getopt

lowres = sys.argv[2]=="low"
tschunk = sys.argv[1]=="ts"


print('lowres = ',lowres)
print('tschunk = ',tschunk)


resfac = 1 if lowres else 10
if lowres:
  cs = (46,12,12) if tschunk else (1,336,276)
else:
  cs = (46,60,60) if tschunk else (1,3360,2760)


from esdl import Cube, CubeConfig
from datetime import datetime
config = CubeConfig(
    ref_time = datetime(2001, 1, 1, 0, 0),
    grid_width = 276*resfac,
    variables = None,
    temporal_res = 8,
    start_time = datetime(2001, 1, 1, 0, 0),
    model_version = '1.0.0',
    static_data = False,
    grid_x0 = 1164*resfac,
    calendar = 'gregorian',
    compression = True,
    end_time = datetime(2018, 1, 1, 0, 0),
    spatial_res = 0.083333/resfac,
    grid_height = 336*resfac,
    grid_y0 = 912*resfac,
    file_format = 'NETCDF4_CLASSIC',
    comp_level = 1, 
    chunk_sizes = cs,
  
)
resustr = 'low' if lowres else 'high'
cubepath = '/Net/Groups/BGI/scratch/fgans/test/newvarscol/' + resustr + 'ColombiaCube_'+str(config.chunk_sizes[0])+'x'+str(config.chunk_sizes[1])+'x'+str(config.chunk_sizes[2])

if not isdir(cubepath):
    cube = Cube.create(cubepath, config)
else:
    cube = Cube.open(cubepath)

provlist=[
           #(ColGPPProvider,        ("GPP",                     "/Net/Groups/BGI/work_2/ColombiaCube/data/GPPSeoul/")),
           #(ColProvider,           ("ET",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/ETSeoul/", 10, 8)),
           #(ColProvider,           ("NDVIterra",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/NDVIterra/", 13, 16)),
        #(ColProvider,           ("NDVIaqua",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/NDVIaqua/", 13, 16)),
          #  (ColProvider,           ("EVIterra",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/EVIterra/", 12, 16)),
            #(ColProvider,           ("EVIaqua",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/EVIaqua/", 12, 16)),
            #(ColProvider,           ("TRMM",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/TRMM/", 17, "month")),
            #(ColProvider,           ("LAI",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/LAI/", 13, 8)),
            #(ColProvider,           ("LSTday",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/LSTday/", 20, 8)),
            #(ColProvider,           ("LSTnight",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/LSTnight/", 22, 8)),
        #    (ColChelsaTProvider,     ("ChelsaT",                    "/Net/Groups/BGI/work_2/ColombiaCube/Sources/chelsaT/netCDF")),
#           (ColChelsaPrecProvider,     ("ChelsaPrec",                    "/Net/Groups/BGI/work_2/ColombiaCube/Sources/chelsaPrec/")),
           # (ColProvider,           ("FPAR",                       "/Net/Groups/BGI/work_2/ColombiaCube/data/FPAR/", 14, 8)),
            #(ColBioUnitsProvider,    ("BioUnits",                   "/Net/Groups/BGI/work_2/ColombiaCube/data/BioUnits/")),
            #(ColCanopyHeightProvider,("CanopyHeight",                "/Net/Groups/BGI/work_2/ColombiaCube/data/canopy/")),
          ]
#provCloudsList = [(ColCloudsProvider, ("Clouds","/Net/Groups/BGI/work_2/ColombiaCube/data/Clouds/", i)) for i in range(1,13)]
#provNWSDList  = [(ColNWSDProvider, (name.split("4")[0][0:-1], "/Net/Groups/BGI/work_2/ColombiaCube/data/HWSD/"))
 #                for name in os.listdir("/Net/Groups/BGI/work_2/ColombiaCube/data/HWSD/")]
#provWorldClimList = [(ColWorldClimProvider, (name.split(".")[0], "/Net/Groups/BGI/work_2/ColombiaCube/data/WorldClim/"))
  #               for name in os.listdir("/Net/Groups/BGI/work_2/ColombiaCube/data/WorldClim/") if name.split(".")[-1] == "nc"]

#provlist.extend(provCloudsList)
#provlist.extend(provNWSDList)
#provlist.extend(provWorldClimList)
provbiom = StaticBGCProvider(config,"Bioma_IAvH2","/Net/Groups/BGI/work_2/ColombiaCube/Sources/dataIAvH/ingest")
provmun  = StaticBGCProvider(config,"municipios","/Net/Groups/BGI/work_2/ColombiaCube/Sources/dataIAvH/ingest")
provckc  = StaticBGCProvider(config,"CKC_hidrosig","/Net/Groups/BGI/work_2/ColombiaCube/Sources/Hidrosig/ingest")
provckcm  = StaticBGCProvider(config,"CKCM_hidrosig","/Net/Groups/BGI/work_2/ColombiaCube/Sources/Hidrosig/ingest")
provcke  = StaticBGCProvider(config,"CKe_hidrosig","/Net/Groups/BGI/work_2/ColombiaCube/Sources/Hidrosig/ingest")
provkde  = StaticBGCProvider(config,"KDE_hidrosig","/Net/Groups/BGI/work_2/ColombiaCube/Sources/Hidrosig/ingest")

for prov in (provbiom, provmun, provckc, provckcm, provcke, provkde):
    cube.update(prov)

for (tprov,args) in provlist:
    prov=tprov(cube.config,*args)
    cube.update(prov)
