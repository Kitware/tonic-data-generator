from paraview import simple
from tonic.paraview.data_writer import *

ds = simple.Wavelet()

dataRenderer = ScalarRenderer()

view = dataRenderer.getView()
view.ViewSize = [500, 500]

simple.Show(ds, view)
simple.ResetCamera(view)

dataRenderer.writeArray('/Users/seb/Desktop/composite/', ds, 'RTData')
