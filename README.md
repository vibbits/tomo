
# Tomo
Experimental software for serial section array tomography on the Delmic SECOM platform.

## Requirements
* Linux (tested on Ubuntu 16.04 and 18.04)
* Odemis v?.?.? (TODO)

## Installation in a production environment
For actual production work, Tomo needs to be installed on the computer which runs Odemis and is connected to the electron microscope. (TODO)

## Installation for development of Tomo
Tomo can also be run in a "development" environment, without a microscope and without Odemis installed. Stub functions are then used instead of Odemis API calls, but a significant part of Tomo is still functional. This setup is useful for software development of Tomo.

Download the latest Tomo sources from GitHub:
```
git clone https://github.com/vibbits/tomo.git
```

Create a Conda environment with dependencies for Tomo
```
cd tomo
conda env create -f environment-dev.yml
conda activate tomo-dev
```

Run Tomo
```
python src/tomo.py
```
