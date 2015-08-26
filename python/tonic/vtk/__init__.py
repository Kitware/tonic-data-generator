from vtk   import *
from tonic import camera as tc

def update_camera(renderer, cameraData):
    camera = renderer.GetActiveCamera()
    camera.SetPosition(cameraData['position'])
    camera.SetFocalPoint(cameraData['focalPoint'])
    camera.SetViewUp(cameraData['viewUp'])

def create_spherical_camera(renderer, dataHandler, phiValues, thetaValues):
    camera = renderer.GetActiveCamera()
    return tc.SphericalCamera(dataHandler, camera.GetFocalPoint(), camera.GetPosition(), camera.GetViewUp(), phiValues, thetaValues)

def create_cylindrical_camera(renderer, dataHandler, phiValues, translationValues):
    camera = renderer.GetActiveCamera()
    return tc.CylindricalCamera(dataHandler, camera.GetFocalPoint(), camera.GetPosition(), camera.GetViewUp(), phiValues, translationValues)

class CaptureRenderWindow(object):
    def __init__(self, magnification=1):
        self.windowToImage = vtkWindowToImageFilter()
        self.windowToImage.SetMagnification(magnification)
        self.windowToImage.SetInputBufferTypeToRGB()
        self.windowToImage.ReadFrontBufferOn()
        self.writer = None

    def SetRenderWindow(self, renderWindow):
        self.windowToImage.SetInput(renderWindow)

    def SetFormat(self, mimeType):
        if mimeType == 'image/png':
            self.writer = vtkPNGWriter()
            self.writer.SetInputConnection(self.windowToImage.GetOutputPort())
        elif mimeType == 'image/jpg':
            self.writer = vtkJPEGWriter()
            self.writer.SetInputConnection(self.windowToImage.GetOutputPort())

    def writeImage(self, path):
        if self.writer:
            self.windowToImage.Modified()
            self.windowToImage.Update()
            self.writer.SetFileName(path)
            self.writer.Write()
