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
dsb = ImageDataSetBuilder(dataset_destination_path, 'image/png', {'type': 'cylindrical', 'phi': range(0, 360, 30), 'translation': range(-5, 5, 1)}, {'author': 'Sebastien Jourdain'})
dsb.start(view)
dsb.writeImages()
dsb.stop()
