from paraview import simple
from tonic    import camera

def update_camera(viewProxy, cameraData):
    viewProxy.CameraFocalPoint = cameraData['focalPoint']
    viewProxy.CameraPosition = cameraData['position']
    viewProxy.CameraViewUp = cameraData['viewUp']
    simple.Render(viewProxy)

def create_spherical_camera(viewProxy, dataHandler, phiValues, thetaValues):
    return camera.SphericalCamera(dataHandler, viewProxy.CenterOfRotation, viewProxy.CameraPosition, viewProxy.CameraViewUp, phiValues, thetaValues)

def create_cylindrical_camera(viewProxy, dataHandler, phiValues, translationValues):
    return camera.CylindricalCamera(dataHandler, viewProxy.CenterOfRotation, viewProxy.CameraPosition, viewProxy.CameraViewUp, phiValues, translationValues)
