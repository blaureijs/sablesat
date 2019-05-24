# sablesat
This Project contains scripts for downloading and processing satellite imagery of Sable Island, NS and converting to coastline vector and land cover classification.
## Getting Started
In order to use these scripts the prerequisite software and libraries must be installed. Scripts, sable.gdb, and the clip_ext and selection_points directories must be unpacked to the same folder (e.g. ```D:\Sable\```).
### Prerequisites
#### Software
* PCI Geomatica 2017
* ArcGIS Desktop 10.6.1
* ArcGIS Desktop Background Geoprocessing (64-bit)

64-bit background geoprocessing is required as the scripts integrate functions from both the pci and arcpy python libraries. The default installation of python provided with ArcGIS desktop is 32-bit, which is incompatible with the 64-bit pci python installation.
More information about this requirement is [available from PCI Geomatics here](https://pcigeomatics.github.io/PCI-Geomatics-Python-Cookbook/geomatica_cookbook_integrate_arcpy.html).
It may also be necessary to copy the ```DTBGGP64.pth``` path file from ```C:\Python27\ArcGISx6410.6\Lib\site-packages``` to ```C:\Python27\Lib\site-packages``` to provide the correct path for the arcpy libraries. Alternatively, the [archook](https://pypi.org/project/archook/) python library can be used to complete this task.
#### Libraries
* sentinelsat 0.12.2
* untangle 1.1.1

The sentinelsat library is required for interacting with the Copernicus Open Access Hub API to download data files. The untangle library is required for parsing links to data products in the Copernicus cart XML file download.

Install with pip prior to running the api_download.py script: ```python -m pip install sentinelsat```

### Copernicus Data Hub Automatic Cart Download
The Copernicus Open Access Hub allows users to download the contents of their cart in an XML format file called ```products.meta4```. This allows the user to avoid manually initiating the download for each file in a large cart selection. The instructions to obtain this file follow:

1. Log-in to the data hub and search for data. Once suitable images have been identified, add them to your cart.
2. Navigate to your data cart:
![Copernicus Cart](/images/download01.png)
3. Click on 'Download Cart' to obtain the XML file required for api_download.py.
![Download Cart](/images/download02.png)
4. Save the ```products.meta4``` file to the project directory where you unpacked the scripts (e.g. ```D:\Sable\```).
5. The full contents of your cart can now be downloaded automatically by api_download.py.

## Authors
* **Brian Laureijs** - *Current work* - [brianlaureijs](https://github.com/blaureijs/)

## License & Disclaimer
Sablesat is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
This project has been completed as an student project for academic assessment in the 'Applied Geomatics Research Project' course at [Center of Geographic Sciences (COGS)](https://www.nscc.ca/explorenscc/campuses/cogs/).
