*ghpythonremote*

## A software utility package to run and connect to an external Python instance from CAD package Rhinoceros/Grasshopper, and vice-versa

#### General Purpose

The general purpose of this software is to run and to an external Python instance from CAD package Rhinoceros/Grasshopper, and vice-versa. This allows the user -- designer, programmer -- to access and use all functionalities of the Python engine and its extension packages. This helps overcome the limitations of the Python interpreter embedded in Rhinoceros/Grasshopper. Most notably, it allows using scientific python packages in Rhinoceros/Grasshopper.

#### Technical description

The software first launches a controlled Python interpreter by calling the target `python` command in a subprocess of the initial Python engine. Two modes are available:

- From python embedded into Rhinoceros/Grasshopper to a standard Python interpreter.
- From a standard Python interpreter to Rhinoceros/Grasshopper.

The controlled Python interpreter then launches a RPC (Remote Procedure Call) server (using the "rpyc" package, MIT License) that will be used to communicate between the two interpreters. This allows running arbitrary code in the interpreter, and sharing objects transparently between both interpreters,

#### Advantages and improvements over existing methods

One existing method (robot software by ETHZ) that allows running scientific python packages in Rhinoceros/Grasshopper implements a custom RPC server, connecting to a remote Python interpreter manually launched elsewhere. Major limitations include a slow communication channel between the two Python instances, the need to manually define special objects to pass and retrieve information with the remote target, and and the manual process of managing the remote target.

The proposed software utility overcomes all three of these limitations, respectively:

- thanks to the network optimizations of rpyc, the communication channel between the two instances is faster;
- thanks to the embedded serializers in rpyc, arbitrary objects can be shared between the two instances, without manual overhead;
- the remote target management has been entirely automatized.

Another approach ("GH_CPython") launches an autonomous standard python interpreter in Rhinoceros/Grasshopper, runs a small snippet of code in it, retrieves the result and immediately closes the interpreter. This makes running many of these snippets of code slow, due to the overhead of re-creating the python interpreter each time. Additionally, all inputs/outputs to the python interpreter are via text files, slowing down the process again. Also, the python interpreter does not have access to objects from Rhinoceros/Grasshopper. Again, the proposed software utility overcomes all of these limitations.

Other methods include running custom versions of scientific packages directly in Rhinoceros/Grasshopper, but using the more limited 32 bits version of the software. The small subset of packages available this way makes the method unsustainable.

Another advantage of the proposed software is the ability to reverse the direction, i.e. controlling Rhinoceros/Grasshopper from a regular python instance, without any additional complexity.

#### Commercial applications

Direct commercial applications are limited, but the software vastly extends the capabilities of Rhinoceros/Grasshopper for scientific studies. As such, it has been used for the optimization of building structures, and is soon to be used for energy studies buildings, and at the urban scale.

Another possible use is the automatic production of 2D and 3D drawings.
