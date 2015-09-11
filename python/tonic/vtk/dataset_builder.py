from tonic        import *
from tonic.vtk    import *
from tonic.camera import *

from vtk import *

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

    def start(self, renderWindow=None, renderer=None):
        if renderWindow:
            # Keep track of renderWindow and renderer
            self.renderWindow = renderWindow
            self.renderer = renderer

            # Initialize image capture
            self.imageCapture.SetRenderWindow(renderWindow)

            # Handle camera if any
            if self.cameraDescription:
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
            size = inputArray.GetNumberOfTuples()
            for idx in range(size):
                self.depthToWrite[idx] = int(inputArray.GetValue(idx))

            with open(depthPath, 'wb') as f:
                f.write(self.depthToWrite)

    def start(self, renderWindow, renderer):
        DataSetBuilder.start(self, renderWindow, renderer)
        self.camera.updatePriority([2,1])

    def stop(self):
        # Push metadata
        self.compositePipeline['dimensions'] = self.renderWindow.GetSize()
        self.compositePipeline['default_pipeline'] = 'A'.join(self.compositePipeline['layers']) + 'A'
        self.dataHandler.addSection('CompositePipeline', self.compositePipeline)

        # Write metadata
        DataSetBuilder.stop(self)

# -----------------------------------------------------------------------------
# Data Prober Dataset Builder
# -----------------------------------------------------------------------------
class DataProberDataSetBuilder(DataSetBuilder):
    def __init__(self, location, sampling_dimesions, fields_to_keep, custom_probing_bounds = None, metadata={}):
        DataSetBuilder.__init__(self, location, None, metadata)
        self.fieldsToWrite = fields_to_keep
        self.resamplerFilter = vtkPResampleFilter()
        self.resamplerFilter.SetSamplingDimension(sampling_dimesions)
        if custom_probing_bounds:
            self.resamplerFilter.SetUseInputBounds(0)
            self.resamplerFilter.SetCustomSamplingBounds(custom_probing_bounds)
        else:
            self.resamplerFilter.SetUseInputBounds(1)

        # Register all fields
        self.dataHandler.addTypes('data-prober', 'binary')
        self.DataProber = { 'types': {}, 'dimensions': sampling_dimesions, 'ranges': {}, 'spacing': [1,1,1] }
        for field in self.fieldsToWrite:
            self.dataHandler.registerData(name=field, type='array', fileName='/%s.array' % field)

    def setDataToProbe(self, dataset):
        self.resamplerFilter.SetInputData(dataset)

    def setSourceToProbe(self, source):
        self.resamplerFilter.SetInputConnection(source.GetOutputPort())

    def writeData(self):
        self.resamplerFilter.Update()
        arrays = self.resamplerFilter.GetOutput().GetPointData()
        for field in self.fieldsToWrite:
            array = arrays.GetArray(field)
            if array:
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

    def stop(self):
        # Push metadata
        self.dataHandler.addSection('DataProber', self.DataProber)

        # Write metadata
        DataSetBuilder.stop(self)

# -----------------------------------------------------------------------------
# Sorted Composite Dataset Builder
# -----------------------------------------------------------------------------
class ConvertVolumeStackToSortedStack(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.textureSize = 0
        self.texturePadding = 0
        self.layers = 0

    def convert(self, directory):
        imagePaths = {}
        depthPaths = {}
        layerNames = []
        for fileName in os.listdir(directory):
            if '_rgb' in fileName or '_depth' in fileName:
                fileId = fileName.split('_')[0][0]
                if '_rgb' in fileName:
                    imagePaths[fileId] = os.path.join(directory, fileName)
                else:
                    layerNames.append(fileId)
                    depthPaths[fileId] = os.path.join(directory, fileName)

        layerNames.sort()

        # Load data in Memory
        depthArrays = []
        imageReader = vtkPNGReader()
        numberOfValues = self.width * self.height * len(layerNames)
        imageSize = self.width * self.height
        self.layers = len(layerNames)
        self.textureSize = int(math.ceil(math.sqrt(numberOfValues)))
        self.texturePadding = int((self.textureSize * self.textureSize) - numberOfValues)
        paddingArray = buffer(bytearray(self.texturePadding))

        # Write all images as single buffer
        opacity = vtkUnsignedCharArray()
        opacity.SetNumberOfComponents(1)
        opacity.SetNumberOfTuples(numberOfValues)

        intensity = vtkUnsignedCharArray()
        intensity.SetNumberOfComponents(1)
        intensity.SetNumberOfTuples(numberOfValues)

        for layer in range(self.layers):
            imageReader.SetFileName(imagePaths[layerNames[layer]])
            imageReader.Update()

            rgbaArray = imageReader.GetOutput().GetPointData().GetArray(0)

            for idx in range(imageSize):
                intensity.SetValue((layer * imageSize) + idx, rgbaArray.GetValue(idx*4))
                opacity.SetValue((layer * imageSize) + idx, rgbaArray.GetValue(idx*4 + 3))

            with open(depthPaths[layerNames[layer]], 'rb') as depthFile:
                depthArrays.append(depthFile.read())

        # Add opacity + padding
        with open(os.path.join(directory, 'alpha.uint8'), 'wb') as alphaFile:
            alphaFile.write(buffer(opacity))
            alphaFile.write(paddingArray)

        # Add intensity + padding
        with open(os.path.join(directory, 'intensity.uint8'), 'wb') as intensityFile:
            intensityFile.write(buffer(intensity))
            intensityFile.write(paddingArray)

        # Apply pixel sorting
        destOrder = vtkUnsignedCharArray()
        destOrder.SetNumberOfComponents(1)
        destOrder.SetNumberOfTuples(numberOfValues)

        for pixelIdx in range(imageSize):
            depthStack = []
            for depthArray in depthArrays:
                depthStack.append((depthArray[pixelIdx], len(depthStack)))
            depthStack.sort(key=lambda tup: tup[0])

            for destLayerIdx in range(len(depthStack)):
                sourceLayerIdx = depthStack[destLayerIdx][1]

                # Copy Idx
                destOrder.SetValue((imageSize * destLayerIdx) + pixelIdx, sourceLayerIdx)

        with open(os.path.join(directory, 'order.uint8'), 'wb') as f:
            f.write(buffer(destOrder))
            f.write(paddingArray)


class SortedCompositeDataSetBuilder(VolumeCompositeDataSetBuilder):
    def __init__(self, location, cameraInfo, metadata={}):
        VolumeCompositeDataSetBuilder.__init__(self, location, 'image/png', cameraInfo, metadata)
        self.dataHandler.addTypes('sorted-composite', 'rgba')

        # Register order and color textures
        self.layerScalars = []
        self.dataHandler.registerData(name='order',     type='array', fileName='/order.uint8')
        self.dataHandler.registerData(name='alpha',     type='array', fileName='/alpha.uint8')
        self.dataHandler.registerData(name='intensity', type='array', fileName='/intensity.uint8', categories=['intensity'])

    def start(self, renderWindow, renderer):
        VolumeCompositeDataSetBuilder.start(self, renderWindow, renderer)
        imageSize = self.renderWindow.GetSize()
        self.dataConverter = ConvertVolumeStackToSortedStack(imageSize[0], imageSize[1])

    def activateLayer(self, colorBy, scalar):
        VolumeCompositeDataSetBuilder.activateLayer(self, 'root', '%d' % scalar, colorBy)
        self.layerScalars.append(scalar)

    def writeData(self, mapper):
        VolumeCompositeDataSetBuilder.writeData(self, mapper)

        # Fill data pattern
        self.dataHandler.getDataAbsoluteFilePath('order')
        self.dataHandler.getDataAbsoluteFilePath('alpha')
        self.dataHandler.getDataAbsoluteFilePath('intensity')

    def stop(self, clean=True, compress=True):
        VolumeCompositeDataSetBuilder.stop(self)

        # Go through all directories and convert them
        for root, dirs, files in os.walk(self.dataHandler.getBasePath()):
            for name in dirs:
                print 'Process', os.path.join(root, name)
                self.dataConverter.convert(os.path.join(root, name))

        # Rename info.json to info_origin.json
        os.rename(os.path.join(self.dataHandler.getBasePath(), "info.json"), os.path.join(self.dataHandler.getBasePath(), "info_origin.json"))

        # Update info.json
        with open(os.path.join(self.dataHandler.getBasePath(), "info_origin.json"), "r") as infoFile:
            metadata = json.load(infoFile)
            metadata['SortedComposite'] = {
                'dimensions': metadata['CompositePipeline']['dimensions'],
                'layers': self.dataConverter.layers,
                'scalars': self.layerScalars[0:self.dataConverter.layers],
                'textures': {
                    'order'    : { 'size': self.dataConverter.textureSize },
                    'alpha'    : { 'size': self.dataConverter.textureSize },
                    'intensity': { 'size': self.dataConverter.textureSize }
                }
            }

            # Clean metadata
            dataToKeep = []
            del metadata['CompositePipeline']
            for item in metadata['data']:
                if item['name'] in ['order', 'alpha', 'intensity']:
                    dataToKeep.append(item)
            metadata['data'] = dataToKeep
            metadata['type'] = [ "tonic-query-data-model", "sorted-composite", "alpha" ]

            # Override info.json
            with open(os.path.join(self.dataHandler.getBasePath(), "info.json"), 'w') as newMetaFile:
                newMetaFile.write(json.dumps(metadata))

        # Clean temporary data
        if clean:
            for root, dirs, files in os.walk(self.dataHandler.getBasePath()):
                print 'Clean', root
                for name in files:
                    if '_rgb.png' in name or '_depth.uint8' in name or name == "info_origin.json":
                        os.remove(os.path.join(root, name))

        if compress:
            for root, dirs, files in os.walk(self.dataHandler.getBasePath()):
                print 'Compress', root
                for name in files:
                    if '.uint8' in name and '.gz' not in name:
                        with open(os.path.join(root, name), 'rb') as f_in, gzip.open(os.path.join(root, name + '.gz'), 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                        os.remove(os.path.join(root, name))
