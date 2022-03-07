import pandas as pd
import numpy as np
import os
import sys
import matplotlib.pyplot as plt
import pv3_poly as pv3_model

data_path = r'./data/gfm8.hdf5'
model_folder = r'./models'

def plot_case(model, idx):
  rmse, y_hat, y_true, u = model.testOneCase(idx)
#  rmse, y_hat, y_true, u = model.stepOneCase(idx)
  print ('column', model.COL_Y, 'RMS errors', rmse)
  valstr = ' '.join('{:.4f}'.format(rms) for rms in rmse)
#  print ('y_hat shape', y_hat.shape)
#  print ('y_true shape', y_true.shape)
#  print ('u shape', u.shape)

  fig, ax = plt.subplots (3, 4, sharex = 'col', figsize=(15,8), constrained_layout=True)
  fig.suptitle ('Case {:d} Simulation; Output RMSE = {:s}'.format(idx, valstr))
  j = 0
  for key in model.COL_U:
    scale = model.normfacs[key]['scale']
    offset = model.normfacs[key]['offset']
    if bNormalized:
      scale = 1.0
      offset = 0.0
    if j > 3:
      row = 1
      col = j-4
    else:
      row = 0
      col = j
    ax[row,col].set_title ('Input {:s}'.format (key))
    ax[row,col].plot (model.t, u[:,j]*scale + offset)
    j += 1
  j = 0
  for key in model.COL_Y:
    scale = model.normfacs[key]['scale']
    offset = model.normfacs[key]['offset']
    if bNormalized:
      scale = 1.0
      offset = 0.0
    row = 2
    col = j
    ax[row,col].set_title ('Output {:s}'.format (key))
    ax[row,col].plot (model.t, y_true[:,j]*scale + offset, label='y')
    ax[row,col].plot (model.t, y_hat[0,:,j]*scale + offset, label='y_hat')
#    ax[2,j].plot (model.t, y_hat[:,j]*scale + offset, label='y_hat')
    ax[row,col].legend()
    j += 1
  plt.show()

if __name__ == '__main__':

  case_idx = 189
  bNormalized = False
  if len(sys.argv) > 1:
    case_idx = int(sys.argv[1])
  if len(sys.argv) > 2:
    if int(sys.argv[2]) > 0:
      bNormalized = True

  model = pv3_model.pv3(os.path.join(model_folder,'gfm8_config.json'))
  model.loadTrainingData(data_path)
  model.loadAndApplyNormalization(os.path.join(model_folder,'normfacs.json'))
  model.initializeModelStructure()
  model.loadModelCoefficients(model_folder)
  print (len(model.COL_U), 'inputs:', model.COL_U)
  print (len(model.COL_Y), 'outputs:', model.COL_Y)

  if case_idx < 0:
    for idx in range(model.n_cases):
      plot_case (model, idx)
  else:
    plot_case (model, case_idx)
