import os

from paraview import simple
from vtk import *

VTK_DATA_TYPES = [ 'void',            # 0
                   'bit',             # 1
                   'char',            # 2
                   'unsigned_char',   # 3
                   'short',           # 4
                   'unsigned_short',  # 5
                   'int',             # 6
                   'unsigned_int',    # 7
                   'long',            # 8
                   'unsigned_long',   # 9
                   'float',           # 10
                   'double',          # 11
                   'id_type',         # 12
                   'unspecified',     # 13
                   'unspecified',     # 14
                   'signed_char' ]

# -----------------------------------------------------------------------------
# Scalar Value to File
# -----------------------------------------------------------------------------
# LoadPlugin(pv_path + '/lib/libRGBZView.dylib')


class ScalarRenderer(object):
    def __init__(self):
        simple.LoadDistributedPlugin('RGBZView')
        self.view = simple.CreateView('RGBZView')
        self.reader = vtkPNGReader()

    def getView(self):
        return self.view

    def writeArray(self, path, source, name, component=0):
        rep = simple.Show(source, self.view)
        rep.Representation = 'Surface'
        rep.DiffuseColor = [1,1,1]

        dataRange = [0.0, 1.0]

        simple.ColorBy(rep, name)
        self.view.SetArrayNameToDraw = name
        self.SetArrayComponentToDraw = component

        pdi = source.GetPointDataInformation()
        cdi = source.GetCellDataInformation()

        if pdi.GetArray(name):
            self.view.SetDrawCells = 0
            dataRange = pdi.GetArray(name).GetRange(component)
        elif cdi.GetArray(name):
            self.view.SetDrawCells = 1
            dataRange = cdi.GetArray(name).GetRange(component)
        else:
            return

        # Grab data
        tmpFileName = path + '__.png'
        self.view.SetScalarRange = dataRange
        self.view.ResetClippingBounds()
        self.view.StartCaptureValues()
        simple.SaveScreenshot(tmpFileName, self.view)
        self.view.StopCaptureValues()

        # Convert data
        self.reader.SetFileName(tmpFileName)
        self.reader.Update()

        rgbArray = self.reader.GetOutput().GetPointData().GetArray(0)
        arraySize = rgbArray.GetNumberOfTuples()

        rawArray = vtkFloatArray()
        rawArray.SetNumberOfTuples(arraySize)

        print dataRange
        delta = (dataRange[1] - dataRange[0]) / 16777215.0 # 2^24 - 1 => 16,777,215
        for idx in range(arraySize):
            rgb = rgbArray.GetTuple3(idx)
            if rgb[0] != 0 or rgb[1] != 0 or rgb[2] != 0:
                value = dataRange[0] + delta * float(rgb[0]*65536 + rgb[1]*256 + rgb[2] - 1)
                rawArray.SetTuple1(idx, value)
            else:
                rawArray.SetTuple1(idx, float('NaN'))

        with open(path + name + '.float32', 'wb') as f:
            f.write(buffer(rawArray))

        # Delete temporary file
        os.remove(tmpFileName)

        # Remove representation from view
        simple.Hide(source, self.view)
