from tonic          import *
from tonic.paraview import *
from tonic.camera   import *

from tonic.paraview import data_writer

from paraview import simple

import json, os, math, gzip, shutil

# Global helper variables
encode_codes = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
arrayTypesMapping = '  bBhHiIlLfd'
jsMapping = {
    'b': 'Int8Array',
    'B': 'Uint8Array',
    'h': 'Int16Array',
    'H': 'Int16Array',
    'i': 'Int32Array',
    'I': 'Uint32Array',
    'l': 'Int32Array',
    'L': 'Uint32Array',
    'f': 'Float32Array',
    'd': 'Float64Array'
}

# -----------------------------------------------------------------------------
# Basic Dataset Builder
# -----------------------------------------------------------------------------

class DataSetBuilder(object):
    def __init__(self, location, camera_data, metadata={}, sections={}):
        self.dataHandler = DataHandler(location)
        self.cameraDescription = camera_data
        self.camera = None

        for key, value in metadata.iteritems():
            self.dataHandler.addMetaData(key, value)

        for key, value in sections.iteritems():
            self.dataHandler.addSection(key, value)

    def getDataHandler(self):
        return self.dataHandler

    def getCamera(self):
        return self.camera

    def updateCamera(self, camera):
        update_camera(self.view, camera)

    def start(self, view=None):
        if view:
            # Keep track of the view
            self.view = view

            # Handle camera if any
            if self.cameraDescription['type'] == 'spherical':
                self.camera = SphericalCamera(self.dataHandler, view.CenterOfRotation, view.CameraPosition, view.CameraViewUp, self.cameraDescription['phi'], self.cameraDescription['theta'])
            elif self.cameraDescription['type'] == 'cylindrical':
                self.camera = CylindricalCamera(self.dataHandler, view.CenterOfRotation, view.CameraPosition, view.CameraViewUp, self.cameraDescription['phi'], self.cameraDescription['translation'])

            # Update background color
            bgColor = view.Background
            bgColorString = 'rgb(%d, %d, %d)' % tuple(int(bgColor[i]*255) for i in range(3))

            if view.UseGradientBackground:
                bgColor2 = view.Background2
                bgColor2String = 'rgb(%d, %d, %d)' % tuple(int(bgColor2[i]*255) for i in range(3))
                self.dataHandler.addMetaData('backgroundColor', 'linear-gradient(%s,%s)' % (bgColor2String, bgColorString))
            else:
                self.dataHandler.addMetaData('backgroundColor', bgColorString)

        # Update file patterns
        self.dataHandler.updateBasePattern()

    def stop(self):
        self.dataHandler.writeDataDescriptor()

# -----------------------------------------------------------------------------
# Image Dataset Builder
# -----------------------------------------------------------------------------

class ImageDataSetBuilder(DataSetBuilder):
    def __init__(self, location, imageMimeType, cameraInfo, metadata={}):
        DataSetBuilder.__init__(self, location, cameraInfo, metadata)
        imageExtenstion = '.' + imageMimeType.split('/')[1]
        self.dataHandler.registerData(name='image', type='blob', mimeType=imageMimeType, fileName=imageExtenstion)

    def writeImages(self):
        for cam in self.camera:
            update_camera(self.view, cam)
            simple.WriteImage(self.dataHandler.getDataAbsoluteFilePath('image'))

# -----------------------------------------------------------------------------
# Data Prober Dataset Builder
# -----------------------------------------------------------------------------
class DataProberDataSetBuilder(DataSetBuilder):
    def __init__(self, input, location, sampling_dimesions, fields_to_keep, custom_probing_bounds = None, metadata={}):
        DataSetBuilder.__init__(self, location, None, metadata)
        self.fieldsToWrite = fields_to_keep
        self.resamplerFilter = simple.ImageResampling(Input=input)
        self.resamplerFilter.SamplingDimension = sampling_dimesions
        if custom_probing_bounds:
            self.resamplerFilter.UseInputBounds = 0
            self.resamplerFilter.CustomSamplingBounds = custom_probing_bounds
        else:
            self.resamplerFilter.UseInputBounds = 1

        # Register all fields
        self.dataHandler.addTypes('data-prober', 'binary')
        self.DataProber = { 'types': {}, 'dimensions': sampling_dimesions, 'ranges': {}, 'spacing': [1,1,1] }
        for field in self.fieldsToWrite:
            self.dataHandler.registerData(name=field, type='array', fileName='/%s.array' % field)

    def writeData(self, time=0):
        self.resamplerFilter.UpdatePipeline(time)
        arrays = self.resamplerFilter.GetClientSideObject().GetOutput().GetPointData()
        maskArray = arrays.GetArray('vtkValidPointMask')
        for field in self.fieldsToWrite:
            array = arrays.GetArray(field)
            if array:
                # Push NaN when no value are present instead of 0
                for idx in range(maskArray.GetNumberOfTuples()):
                    if not maskArray.GetValue(idx):
                        array.SetValue(idx, float('NaN'))

                b = buffer(array)
                with open(self.dataHandler.getDataAbsoluteFilePath(field), 'wb') as f:
                    f.write(b)

                self.DataProber['types'][field] = jsMapping[arrayTypesMapping[array.GetDataType()]]
                if field in self.DataProber['ranges']:
                    dataRange = array.GetRange()
                    if dataRange[0] < self.DataProber['ranges'][field][0]:
                        self.DataProber['ranges'][field][0] = dataRange[0]
                    if dataRange[1] > self.DataProber['ranges'][field][1]:
                        self.DataProber['ranges'][field][1] = dataRange[1]
                else:
                    self.DataProber['ranges'][field] = [array.GetRange()[0], array.GetRange()[1]]

            else:
                print 'No array for', field
                print self.resamplerFilter.GetOutput()

    def stop(self, compress=True):
        # Push metadata
        self.dataHandler.addSection('DataProber', self.DataProber)

        # Write metadata
        DataSetBuilder.stop(self)

        if compress:
            for root, dirs, files in os.walk(self.dataHandler.getBasePath()):
                print 'Compress', root
                for name in files:
                    if '.array' in name and '.gz' not in name:
                        with open(os.path.join(root, name), 'rb') as f_in, gzip.open(os.path.join(root, name + '.gz'), 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                        os.remove(os.path.join(root, name))


# -----------------------------------------------------------------------------
# Float Image with Layer Dataset Builder
# -----------------------------------------------------------------------------

class LayerDataSetBuilder(DataSetBuilder):
    def __init__(self, input, location, cameraInfo, imageSize=[500,500], metadata={}):
        DataSetBuilder.__init__(self, location, cameraInfo, metadata)
        self.dataRenderer = data_writer.ScalarRenderer()
        self.view = self.dataRenderer.getView()
        self.view.ViewSize = imageSize
        self.floatImage = {'dimensions': imageSize, 'layers': [], 'ranges': {}}
        self.layerMap = {}
        self.input = input
        self.activeLayer = None
        self.activeField = None
        self.layerChanged = False

        # Update data type
        self.dataHandler.addTypes('float-image')

    def getView(self):
        return self.view

    def setActiveLayer(self, layer, field, hasMesh=False):
        needDataRegistration = False
        if layer not in self.layerMap:
            layerObj = { 'name': layer, 'array': field, 'arrays': [ field ], 'active': True, 'type': 'Float32Array', 'hasMesh': hasMesh }
            self.layerMap[layer] = layerObj
            self.floatImage['layers'].append(layerObj)
            needDataRegistration = True

            # Register layer lighting
            self.dataHandler.registerData(name='%s__light' % layer, type='array', fileName='/%s__light.array' % layer, categories=[ '%s__light' % layer ])

            # Register layer mesh
            if hasMesh:
                self.dataHandler.registerData(name='%s__mesh' % layer, type='array', fileName='/%s__mesh.array' % layer, categories=[ '%s__mesh' % layer ])

        elif field not in self.layerMap[layer]['arrays']:
            self.layerMap[layer]['arrays'].append(field)
            needDataRegistration = True

        # Keep track of the active data
        if self.activeLayer != layer:
            self.layerChanged = True
        self.activeLayer = layer
        self.activeField = field

        if needDataRegistration:
            self.dataHandler.registerData(name='%s_%s' % (layer, field), type='array', fileName='/%s_%s.array' % (layer, field), categories=[ '%s_%s' % (layer, field) ])

    def writeLayerData(self, time=0):
        dataRange = [0, 1]
        self.input.UpdatePipeline(time)

        if self.activeField and self.activeLayer:

            if self.layerChanged:
                self.layerChanged = False

                # Capture lighting information
                for camPos in self.getCamera():
                    self.view.CameraFocalPoint = camPos['focalPoint']
                    self.view.CameraPosition = camPos['position']
                    self.view.CameraViewUp = camPos['viewUp']
                    self.dataRenderer.writeLightArray(self.dataHandler.getDataAbsoluteFilePath('%s__light'%self.activeLayer), self.input)

                # Capture mesh information
                if self.layerMap[self.activeLayer]['hasMesh']:
                    for camPos in self.getCamera():
                        self.view.CameraFocalPoint = camPos['focalPoint']
                        self.view.CameraPosition = camPos['position']
                        self.view.CameraViewUp = camPos['viewUp']
                        self.dataRenderer.writeMeshArray(self.dataHandler.getDataAbsoluteFilePath('%s__mesh'%self.activeLayer), self.input)


            for camPos in self.getCamera():
                self.view.CameraFocalPoint = camPos['focalPoint']
                self.view.CameraPosition = camPos['position']
                self.view.CameraViewUp = camPos['viewUp']
                dataName = ('%s_%s' % (self.activeLayer, self.activeField))
                dataRange = self.dataRenderer.writeArray(self.dataHandler.getDataAbsoluteFilePath(dataName), self.input, self.activeField)

            if self.activeField not in self.floatImage['ranges']:
                self.floatImage['ranges'][self.activeField] = [ dataRange[0], dataRange[1] ]
            else:
                # Expand the ranges
                if dataRange[0] < self.floatImage['ranges'][self.activeField][0]:
                    self.floatImage['ranges'][self.activeField][0] = dataRange[0]
                if dataRange[1] > self.floatImage['ranges'][self.activeField][1]:
                    self.floatImage['ranges'][self.activeField][1] = dataRange[1]

    def start(self):
        DataSetBuilder.start(self, self.view)

    def stop(self, compress=True):
        # Push metadata
        self.dataHandler.addSection('FloatImage', self.floatImage)

        # Write metadata
        DataSetBuilder.stop(self)

        if compress:
            for root, dirs, files in os.walk(self.dataHandler.getBasePath()):
                print 'Compress', root
                for name in files:
                    if '.array' in name and '.gz' not in name:
                        with open(os.path.join(root, name), 'rb') as f_in, gzip.open(os.path.join(root, name + '.gz'), 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                        os.remove(os.path.join(root, name))
