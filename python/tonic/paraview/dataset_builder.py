from tonic          import *
from tonic.paraview import *
from tonic.camera   import *

from paraview import simple

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

    def start(self, view):
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
