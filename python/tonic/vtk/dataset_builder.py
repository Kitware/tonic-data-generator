from tonic        import *
from tonic.vtk    import *
from tonic.camera import *

from vtk import *

encode_codes = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

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

# -----------------------------------------------------------------------------
# Volume Composite Dataset Builder
# -----------------------------------------------------------------------------
class VolumeCompositeDataSetBuilder(DataSetBuilder):
    def __init__(self, location, imageMimeType, cameraInfo, metadata={}):
        DataSetBuilder.__init__(self, location, cameraInfo, metadata)

        self.dataHandler.addTypes('volume-composite', 'rgba+depth')

        self.imageMimeType = imageMimeType
        self.imageExtenstion = '.' + imageMimeType.split('/')[1]

        if imageMimeType == 'image/png':
            self.imageWriter = vtkPNGWriter()
        if imageMimeType == 'image/jpg':
            self.imageWriter = vtkJPEGWriter()

        self.imageDataColor = vtkImageData()
        self.imageWriter.SetInputData(self.imageDataColor)

        self.imageDataDepth = vtkImageData()
        self.depthToWrite = None

        self.layerInfo = {}
        self.colorByMapping = {}
        self.compositePipeline = {'layers': [], 'dimensions': [], 'fields': {}, 'layer_fields': {}, 'pipeline': []}
        self.activeDepthKey = ''
        self.activeRGBKey = ''
        self.nodeWithChildren = {}

    def activateLayer(self, parent, name, colorBy):
        layerCode = ''
        colorCode = ''
        needToRegisterDepth = False
        needToRegisterColor = False
        if name in self.layerInfo:
            # Layer already exist
            layerCode = self.layerInfo[name]['code']
            if colorBy not in self.compositePipeline['layer_fields'][name]:
                if colorBy in self.colorByMapping:
                    # Color already registered
                    # => Add it for the field if not already in
                    colorCode = self.colorByMapping[colorBy]
                    if colorCode not in self.compositePipeline['layer_fields'][layerCode]:
                        needToRegisterColor = True
                        self.compositePipeline['layer_fields'][layerCode].append(colorCode)
                else:
                    needToRegisterColor = True
                    # No color code assigned yet
                    colorCode = encode_codes[len(self.colorByMapping)]
                    # Assign color code
                    self.colorByMapping[colorBy] = colorCode
                    # Register color code with color by value
                    self.compositePipeline['fields'][colorCode] = colorBy
                    # Add color code to the layer
                    self.compositePipeline['layer_fields'][layerCode].append(colorCode)
        else:
            # The layer does not exist yet
            needToRegisterDepth = True
            needToRegisterColor = True
            layerCode = encode_codes[len(self.layerInfo)]
            self.layerInfo[layerCode] = { 'code': layerCode, 'name': name, 'parent': parent }
            self.compositePipeline['layers'].append(layerCode)
            if colorBy in self.colorByMapping:
                # The color code exist
                colorCode = self.colorByMapping[colorBy]
                self.compositePipeline['layer_fields'][layerCode] = [ colorCode ]
            else:
                # No color code assigned yet
                colorCode = encode_codes[len(self.colorByMapping)]
                # Assign color code
                self.colorByMapping[colorBy] = colorCode
                # Register color code with color by value
                self.compositePipeline['fields'][colorCode] = colorBy
                # Add color code to the layer
                self.compositePipeline['layer_fields'][layerCode] = [ colorCode ]

            # Let's register it in the pipeline
            if parent:
                if parent not in self.nodeWithChildren:
                    # Need to create parent
                    rootNode = {'name': parent, 'ids': [], 'children':[]}
                    self.nodeWithChildren[parent] = rootNode
                    self.compositePipeline['pipeline'].append(rootNode)

                # Add node to its parent
                self.nodeWithChildren[parent]['children'].append({'name': name, 'ids': [layerCode]})
                self.nodeWithChildren[parent]['ids'].append(layerCode)

            else:
                self.compositePipeline['pipeline'].append({'name': name, 'ids': [layerCode]})

        # Update active keys
        self.activeDepthKey = '%s_depth' % layerCode
        self.activeRGBKey   = '%s%s_rgb' % (layerCode, colorCode)

        # Need to register data
        if needToRegisterDepth:
            self.dataHandler.registerData(name=self.activeDepthKey, type='array', fileName='/%s_depth.uint8' % layerCode, categories=[ layerCode ])

        if needToRegisterColor:
            self.dataHandler.registerData(name=self.activeRGBKey, type='blob', fileName='/%s%s_rgb%s' % (layerCode, colorCode, self.imageExtenstion), categories=[ '%s%s' % (layerCode, colorCode) ], mimeType=self.imageMimeType)

    def writeData(self, mapper):
        width = self.renderWindow.GetSize()[0]
        height = self.renderWindow.GetSize()[1]

        if not self.depthToWrite:
            self.depthToWrite = bytearray(width * height)

        for cam in self.camera:
            self.updateCamera(cam)
            imagePath = self.dataHandler.getDataAbsoluteFilePath(self.activeRGBKey)
            depthPath = self.dataHandler.getDataAbsoluteFilePath(self.activeDepthKey)

            # -----------------------------------------------------------------
            # Write Image
            # -----------------------------------------------------------------
            mapper.GetColorImage(self.imageDataColor)
            self.imageWriter.SetFileName(imagePath)
            self.imageWriter.Write()

            # -----------------------------------------------------------------
            # Write Depth
            # -----------------------------------------------------------------
            mapper.GetDepthImage(self.imageDataDepth)
            inputArray = self.imageDataDepth.GetPointData().GetArray(0)
            for idx in range(inputArray.GetNumberOfTuples()):
                self.depthToWrite[idx] = 255 - int(inputArray.GetValue(idx))

            with open(depthPath, 'wb') as f:
                f.write(self.depthToWrite)

    def start(self, renderWindow, renderer):
        DataSetBuilder.start(self, renderWindow, renderer)
        self.camera.updatePriority([2,1])

    def stop(self):
        # Push metadata
        self.compositePipeline['dimensions'] = self.renderWindow.GetSize()
        self.dataHandler.addSection('CompositePipeline', self.compositePipeline)

        # Write metadata
        DataSetBuilder.stop(self)
