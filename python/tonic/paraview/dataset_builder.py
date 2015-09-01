from tonic          import *
from tonic.paraview import *
from tonic.camera   import *

from paraview import simple

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

    def writeData(self):
        self.resamplerFilter.UpdatePipeline()
        arrays = self.resamplerFilter.GetClientSideObject().GetOutput().GetPointData()
        for field in self.fieldsToWrite:
            array = arrays.GetArray(field)
            if array:
                b = buffer(array)
                with open(self.dataHandler.getDataAbsoluteFilePath(field), 'wb') as f:
                    f.write(b)

                self.DataProber['types'][field] = jsMapping[arrayTypesMapping[array.GetDataType()]]
                self.DataProber['ranges'][field] = array.GetRange()
            else:
                print 'No array for', field
                print self.resamplerFilter.GetOutput()

    def stop(self):
        # Push metadata
        self.dataHandler.addSection('DataProber', self.DataProber)

        # Write metadata
        DataSetBuilder.stop(self)
