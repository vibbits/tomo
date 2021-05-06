
# Tomo

Experimental software for serial section array tomography on the [Delmic SECOM](https://www.delmic.com/en/products/clem-solutions/secom) platform.

## Documentation

Please refer to the [user manual](doc/Tomo%20user%20manual.pdf) for documentation on how to use Tomo.

## Prerequisites

The normal environment for Tomo, when doing actual microscopy work, is:

* Ubuntu 16.04 or 18.04 (for Odemis)
* [Odemis](https://github.com/delmic/odemis) v3.0.7
* Electron microscope with SECOM platform, controlled by Odemis
* [Fiji](https://imagej.net/Fiji)

However, for software development we can also run Tomo with reduced functionality on a system without microscope and without Odemis.

## Installation

For actual microscopy work, Tomo needs to be installed on the computer which runs Odemis and is connected to the electron microscope equiped with the SECOM platform. Since Odemis is not installed in a virtual enviroment, neither is Tomo in this case.

First get the latest Tomo sources from GitHub:

```bash
git clone https://github.com/vibbits/tomo.git
cd tomo
```

Tomo requirements are then installed like this:

```bash
pip install -r requirements.txt
```

Tomo can however also be run in a development environment, on a stand-alone computer without a microscope and without Odemis installed. Stub functions are then used instead of Odemis API calls, but a significant part of Tomo is still functional. This setup is useful for software development of Tomo. Tomo requirements can then be installed in a [Conda](https://docs.conda.io/en/latest/) environment:

```bash
conda env create -f environment-dev.yml
conda activate tomo-dev
```

In both setups we can now start Tomo:

```bash
python src/tomo.py
```

This will open the graphical user interface of Tomo.


## Image Registration Plugins

For registration of the LM and EM images, Tomo runs a headless Fiji with a script that calls a Fiji plugin to perform the actual image registration. Tomo currently supports two well-known image registration plugins: [StackReg](https://imagej.net/StackReg) and [Linear Stack Alignment with SIFT](https://imagej.net/Linear_Stack_Alignment_with_SIFT).

### Fiji

As mentioned in the prerequisites above, simply download Fiji from its official [website](https://imagej.net/Fiji). The location of the resulting Fiji installation can be specified in Tomo's Preferences dialog, as described in the [user manual](doc/Tomo%20user%20manual.pdf).

### Linear Stack Alignment with SIFT

The official Fiji has the Linear Stack Alignment with SIFT plugin already installed. Depending on the specific images that need to be registered, this plugin may suffice. In that case StackReg (see below) is not needed.

### StackReg

For some images, StackReg may produce better registration results than Linear Stack Alignment with SIFT. So Tomo *also* supports StackReg. StackReg is not part of the default set of plugins of Fiji, so we will have to add it ourselves. Unfortunately, StackReg outputs the aligned images but does not output the corresponding transformation matrices used for aligning the images, and they are needed by Tomo. If you wish to use StackReg in Tomo, please follow the procedure below to apply a small [patch](support/stackreg.patch) to StackReg to also have it output the transformations.

```bash
# Get ImageJ dependency
wget https://repo1.maven.org/maven2/net/imagej/ij/1.50a/ij-1.50a.jar

# Get and extract StackReg
wget http://bigwww.epfl.ch/thevenaz/stackreg/stackreg.tar
tar xf stackreg.tar

# Apply patch to output the transformation matrices
patch StackReg/StackReg_.java ~/tomo/support/stackreg.patch

# Build StackReg and re-create the JAR with the modified StackReg plugin
mkdir StackReg/classes
javac -classpath ij-1.50a.jar -d StackReg/classes StackReg/StackReg_.java 
jar cvfM StackReg_.jar StackReg/StackReg_.java -C StackReg/classes .
```

Place the newly created StackReg_.jar file in the plugins folder of your Fiji installation. Finally, download StackReg's ancillary [TurboReg](http://bigwww.epfl.ch/thevenaz/turboreg/) plugin and add it to the plugins folder as well.
