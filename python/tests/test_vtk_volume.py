from vtk import *

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

def writeDepthMap(idx, imageData):
    nbTuples = imageData.GetDimensions()[0] * imageData.GetDimensions()[1]

    depthDS = vtkImageData()
    depthDS.SetDimensions(imageData.GetDimensions())

    depth = vtkUnsignedCharArray()
    depth.SetNumberOfComponents(1)
    depth.SetNumberOfTuples(nbTuples)
    depth.SetName('Depth')
    depthDS.GetPointData().AddArray(depth)

    inputArray = imageData.GetPointData().GetArray(0)
    for i in range(nbTuples):
        depth.SetValue(i, int(inputArray.GetValue(i*3)))

    writer.SetInputData(depthDS)
    writer.SetFileName('./depth_%d.vtk' % idx)
    writer.Update()

def writeColorMap(idx, imageData):
    nbTuples = imageData.GetDimensions()[0] * imageData.GetDimensions()[1]

    colorDS = vtkImageData()
    colorDS.SetDimensions(imageData.GetDimensions())

    colorRGB = vtkUnsignedCharArray()
    colorRGB.SetNumberOfComponents(3) # RGB
    colorRGB.SetNumberOfTuples(nbTuples)
    colorRGB.SetName('RGB')
    colorDS.GetPointData().AddArray(colorRGB)

    inputArray = imageData.GetPointData().GetArray(0)
    for i in range(nbTuples):
        colorRGB.SetValue(i*3,   int(inputArray.GetValue(i*3)))
        colorRGB.SetValue(i*3+1, int(inputArray.GetValue(i*3+1)))
        colorRGB.SetValue(i*3+2, int(inputArray.GetValue(i*3+2)))

    writer.SetInputData(colorDS)
    writer.SetFileName('./color_%d.vtk' % idx)
    writer.Update()

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
volumeProperty.ShadeOn()
volumeProperty.SetInterpolationType(VTK_LINEAR_INTERPOLATION)
volumeProperty.SetColor(colorFunction)
volumeProperty.SetScalarOpacity(scalarOpacity)

volume = vtkVolume()
volume.SetMapper(mapper)
volume.SetProperty(volumeProperty)

window = vtkRenderWindow()
window.SetSize(500, 500)

renderer = vtkRenderer()
window.AddRenderer(renderer)

renderer.AddVolume(volume)
renderer.GetActiveCamera().Azimuth(90)
renderer.GetActiveCamera().Roll(90)
renderer.GetActiveCamera().Azimuth(-90)
renderer.ResetCamera()
renderer.GetActiveCamera().Zoom(1.8)

colorMap = vtkImageData()
depthMap = vtkImageData()

idx = 0
for center in centers:
    if id == 0:
        window.ResetCamera()
        window.Render()

    idx += 1
    updatePieceWise(scalarOpacity, dataRange, center, halfSpread)
    window.Render()
    mapper.GetColorTextureAsImageData(colorMap)
    writeColorMap(idx, colorMap)

    mapper.GetDepthTextureAsImageData(depthMap)
    writeDepthMap(idx, depthMap)
