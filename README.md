
# Tomo
Experimental software for serial section array tomography on the [Delmic SECOM](https://www.delmic.com/en/products/clem-solutions/secom) platform.

## Requirements
* Ubuntu 16.04 or 18.04 (for Odemis)
* [Odemis](https://github.com/delmic/odemis) v3.0.7
* Electron microscope with SECOM platform (for production work)
* [Fiji](https://imagej.net/Fiji)

# Installation

First get the latest Tomo sources from GitHub:
```
git clone https://github.com/vibbits/tomo.git
cd tomo
```

For actual production work, Tomo needs to be installed on the computer which runs Odemis and is connected to the electron microscope equiped with the SECOM platform. Since Odemis is not installed in a virtual enviroment, neither is Tomo in this case. Tomo requirements are then installed like this:
```
pip install -r requirements.txt
```

Tomo can however also be run in a development environment, without a microscope and without Odemis installed. Stub functions are then used instead of Odemis API calls, but a significant part of Tomo is still functional. This setup is useful for software development of Tomo. Tomo requirements can then be installed in a Conda environment:

```
conda env create -f environment-dev.yml
conda activate tomo-dev
```

In both setups we can now run Tomo:
```
python src/tomo.py
```
