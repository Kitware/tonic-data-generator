# tonic-data-generator

Helper toolkit for generating DataSet for ArcticViewer.
The current implementation provide a Python module that can be used by any
visualization tool but additional helper class and method are provided for
its usage within ParaView.

## Installation

First you should let __tonic-data-generator__ know where you want to deploy the
tonic python module and which executable should be used.

To do that locally, you can just export those variables, but it might be more
useful to set them up globally in your ~/.bashrc or ~/.profile.

```sh
# OS X using installed ParaView inside /Applications
$ export TONIC_PYTHON_PATH=/Applications/paraview.app/Contents/Python

# OS X + Linux using build tree
$ export TONIC_PYTHON_PATH=/.../ParaView/build/lib/site-packages

# Optionally you can set the TONIC_PYTHON_EXEC one.
# If not provided __tonic-run-py__ will search for vtkpython or pvpython using
# the TONIC_PYTHON_PATH one.
$ export TONIC_PYTHON_PATH=/.../ParaView/build/bin/pvpython
```

Then you can install and run __tonic-data-generator__ with the following set
of commands.

```sh
# Install globally
$ npm install -g tonic-data-generator

# Update your python path with latest tonic code base
$ tonic-install-py

# Run a data generator script (TONIC_PYTHON_PATH must be set)
$ tonic-run-py /path/to/your/python/script.py
```

## Usage

Once the __tonic__ module has been deployed inside ParaView, you can run the
following script:

```python
from paraview.simple import *
from tonic.paraview.dataset_builder import *

dataset_destination_path = '/tmp/cylinder_v2'

# Initial ParaView scene setup
Cylinder(Resolution = 30, Height = 10.0, Center = (1,2,3))
rep = Show()
view = Render()

ResetCamera()
view.CenterOfRotation = view.CameraFocalPoint

ColorBy(rep, ('POINTS', 'Normals'))
normalsLUT = GetColorTransferFunction('Normals')
normalsLUT.VectorMode = 'Component'
normalsLUT.VectorComponent = 0

Render()

# Create Tonic Dataset
dsb = ImageDataSetBuilder(dataset_destination_path, 'image/jpg', {'type': 'cylindrical', 'phi': range(0, 360, 30), 'translation': range(-5, 5, 1)})
dsb.start(view)
dsb.writeImages()
dsb.stop()
```

Or if you prefer a time dependent dataset like the __can.ex2__.

```python
from paraview.simple import *
from tonic.paraview.dataset_builder import *

# Can.ex2 file path
fileToLoad = '/Users/seb/Work/code/ParaView/data/can.ex2'
dataset_destination_path = '/tmp/can'

# Initial ParaView scene setup
can = OpenDataFile(fileToLoad)
can.ElementVariables = ['EQPS']
can.PointVariables = ['DISPL', 'VEL', 'ACCL']
can.GlobalVariables = ['KE', 'XMOM', 'YMOM', 'ZMOM', 'NSTEPS', 'TMSTEP']
can.ElementBlocks = ['Unnamed block ID: 1 Type: HEX', 'Unnamed block ID: 2 Type: HEX']

rep = Show()
view = Render()

anim = GetAnimationScene()
anim.UpdateAnimationUsingDataTimeSteps()
anim.GoToLast()

ColorBy(rep, ('POINTS', 'DISPL'))
rep.RescaleTransferFunctionToDataRange(True)

timeValues = anim.TimeKeeper.TimestepValues

view.CameraPosition = [-18.29191376466667, 21.185677224902403, -45.68993692892029]
view.CameraFocalPoint = [-0.5119223594665527, 3.3483874797821045, -11.321756362915039]
view.CameraViewUp = [0.29015080553622485, -0.779749133967588, -0.5548006832399148]

view.ResetCamera()
view.CenterOfRotation = view.CameraFocalPoint
Render()

# Create Tonic Dataset
dsb = ImageDataSetBuilder(dataset_destination_path, 'image/jpg', {'type': 'spherical', 'phi': range(0, 360, 45), 'theta': range(-60, 61, 30)})

# Add time information
dsb.getDataHandler().registerArgument(priority=1, name='time', values=timeValues, ui='slider', loop='modulo')

# Explore dataset
dsb.start(view)
for time in dsb.getDataHandler().time:
    anim.TimeKeeper.Time = time
    dsb.writeImages()
dsb.stop()
```
