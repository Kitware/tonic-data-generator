from tonic        import *
from tonic.vtk    import *
from tonic.camera import *

from vtk import *

# -----------------------------------------------------------------------------
# Basic Dataset Builder
# -----------------------------------------------------------------------------

class DataSetBuilder(object):
    def __init__(self, location, camera_data, metadata={}, sections={}):
        self.dataHandler = DataHandler(location)
        self.cameraDescription = camera_data
        self.camera = None
        self.imageCapture = CaptureRenderWindow()

        for key, value in metadata.iteritems():
            self.dataHandler.addMetaData(key, value)

        for key, value in sections.iteritems():
            self.dataHandler.addSection(key, value)

    def getDataHandler(self):
        return self.dataHandler

    def getCamera(self):
        return self.camera

    def updateCamera(self, camera):
        update_camera(self.renderer, camera)
        self.renderWindow.Render()

    def start(self, renderWindow, renderer):
        # Keep track of renderWindow and renderer
        self.renderWindow = renderWindow
        self.renderer = renderer

        # Initialize image capture
        self.imageCapture.SetRenderWindow(renderWindow)

        # Handle camera if any
        if self.cameraDescription['type'] == 'spherical':
            self.camera = create_spherical_camera(renderer, self.dataHandler, self.cameraDescription['phi'], self.cameraDescription['theta'])
        elif self.cameraDescription['type'] == 'cylindrical':
            self.camera = create_cylindrical_camera(renderer, self.dataHandler, self.cameraDescription['phi'], self.cameraDescription['translation'])

        # Update background color
        bgColor = renderer.GetBackground()
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
        self.imageCapture.SetFormat(imageMimeType)

    def writeImage(self):
        self.imageCapture.writeImage(self.dataHandler.getDataAbsoluteFilePath('image'))

    def writeImages(self):
        for cam in self.camera:
            update_camera(self.renderer, cam)
            self.renderWindow.Render()
            self.imageCapture.writeImage(self.dataHandler.getDataAbsoluteFilePath('image'))
