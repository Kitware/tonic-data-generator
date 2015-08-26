# -----------------------------------------------------------------------------
# User configuration
# -----------------------------------------------------------------------------

dataset_destination_path = '/Users/seb/Desktop/vtk_volume'

# -----------------------------------------------------------------------------

from vtk import *
from tonic.vtk.dataset_builder import *

# -----------------------------------------------------------------------------
# VTK Helper methods
# -----------------------------------------------------------------------------

def updatePieceWise(pwf, dataRange, center, halfSpread):
    scalarOpacity.RemoveAllPoints()
    if (center - halfSpread) <= dataRange[0]:
        scalarOpacity.AddPoint(dataRange[0], 0.0)
        scalarOpacity.AddPoint(center, 1.0)
    else:
        scalarOpacity.AddPoint(dataRange[0], 0.0)
        scalarOpacity.AddPoint(center - halfSpread, 0.0)
        scalarOpacity.AddPoint(center, 1.0)

    if (center + halfSpread) >= dataRange[1]:
        scalarOpacity.AddPoint(dataRange[1], 0.0)
    else:
        scalarOpacity.AddPoint(center + halfSpread, 0.0)
        scalarOpacity.AddPoint(dataRange[1], 0.0)

# -----------------------------------------------------------------------------

writer = vtkDataSetWriter()
imageWriter = vtkJPEGWriter()

# def writeDepthMap(imageData, path):
#     nbTuples = imageData.GetDimensions()[0] * imageData.GetDimensions()[1]

#     depthDS = vtkImageData()
#     depthDS.SetDimensions(imageData.GetDimensions())

#     depth = vtkUnsignedCharArray()
#     depth.SetNumberOfComponents(1)
#     depth.SetNumberOfTuples(nbTuples)
#     depth.SetName('Depth')
#     depthDS.GetPointData().AddArray(depth)

#     inputArray = imageData.GetPointData().GetArray(0)
#     for i in range(nbTuples):
#         depth.SetValue(i, int(inputArray.GetValue(i*3)))

#     writer.SetInputData(depthDS)
#     writer.SetFileName(path)
#     writer.Update()

def writeDepthMap(imageData, path):
    width = imageData.GetDimensions()[0]
    height = imageData.GetDimensions()[1]
    nbTuples = width * height

    inputArray = imageData.GetPointData().GetArray(0)
    array = bytearray(nbTuples)
    # Need to flip the data along Y
    # and reverse data (big depth is on the front)
    for j in range(height):
        for i in range(width):
            array[j*width + i] = 255 - int(inputArray.GetValue(((height-j-1)*width + i)*3))

    with open(path, 'wb') as f:
        f.write(array)

def writeColorMap(imageData, path):
    nbTuples = imageData.GetDimensions()[0] * imageData.GetDimensions()[1]

    colorDS = vtkImageData()
    colorDS.SetDimensions(imageData.GetDimensions())

    colorRGB = vtkUnsignedCharArray()
    colorRGB.SetNumberOfComponents(3) # RGB
    colorRGB.SetNumberOfTuples(nbTuples)
    colorRGB.SetName('RGB')
    colorDS.GetPointData().AddArray(colorRGB)
    colorDS.GetPointData().SetActiveScalars('RGB')

    inputArray = imageData.GetPointData().GetArray(0)
    for i in range(nbTuples):
        colorRGB.SetValue(i*3,   int(inputArray.GetValue(i*3)))
        colorRGB.SetValue(i*3+1, int(inputArray.GetValue(i*3+1)))
        colorRGB.SetValue(i*3+2, int(inputArray.GetValue(i*3+2)))

    imageWriter.SetInputData(colorDS)
    imageWriter.SetFileName(path)
    imageWriter.Update()

# -----------------------------------------------------------------------------
# VTK Pipeline creation
# -----------------------------------------------------------------------------

source = vtkRTAnalyticSource()

mapper = vtkGPUVolumeRayCastMapper()
mapper.SetInputConnection(source.GetOutputPort())
mapper.RenderToTextureOn()

colorFunction = vtkColorTransferFunction()
colorFunction.AddRGBPoint(37.35310363769531, 0.231373, 0.298039, 0.752941)
colorFunction.AddRGBPoint(157.0909652709961, 0.865003, 0.865003, 0.865003)
colorFunction.AddRGBPoint(276.8288269042969, 0.705882, 0.0156863, 0.14902)

dataRange = [37.3, 276.8]
nbSteps = 10
halfSpread = (dataRange[1] - dataRange[0]) / float(2*nbSteps)
centers = [ dataRange[0] + halfSpread*float(2*i+1) for i in range(nbSteps)]

scalarOpacity = vtkPiecewiseFunction()

volumeProperty = vtkVolumeProperty()
# volumeProperty.ShadeOn()
volumeProperty.SetInterpolationType(VTK_LINEAR_INTERPOLATION)
volumeProperty.SetColor(colorFunction)
volumeProperty.SetScalarOpacity(scalarOpacity)

volume = vtkVolume()
volume.SetMapper(mapper)
volume.SetProperty(volumeProperty)

window = vtkRenderWindow()
window.SetSize(500, 500)

renderer = vtkRenderer()
renderer.SetBackground(0.5, 0.5, 0.6)
window.AddRenderer(renderer)

renderer.AddVolume(volume)
renderer.ResetCamera()
window.Render()

colorMap = vtkImageData()
depthMap = vtkImageData()

# -----------------------------------------------------------------------------
# Data Generation
# -----------------------------------------------------------------------------

# Create Image Builder
dsb = ImageDataSetBuilder(dataset_destination_path, 'image/jpg', {'type': 'spherical', 'phi': range(0, 360, 30), 'theta': range(-60, 61, 30)})

# Add PieceWise navigation
dsb.getDataHandler().registerArgument(priority=1, name='pwf', label='Transfer function', values=centers, ui='slider')

# Add Depth data
dsb.getDataHandler().registerData(name='depth', type='array', fileName='_depth.uint8', metadata={ 'dimensions': window.GetSize() })

# Loop over data and generate images
dsb.start(window, renderer)
for center in dsb.getDataHandler().pwf:
    updatePieceWise(scalarOpacity, dataRange, center, halfSpread)
    for camera in dsb.getCamera():
        dsb.updateCamera(camera)

        dsb.writeImage()

        # mapper.GetColorTextureAsImageData(colorMap)
        # writeColorMap(colorMap, dsb.getDataHandler().getDataAbsoluteFilePath('image'))

        mapper.GetDepthTextureAsImageData(depthMap)
        writeDepthMap(depthMap, dsb.getDataHandler().getDataAbsoluteFilePath('depth'))
dsb.stop()
