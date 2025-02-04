# Copyright (C) 2022 Battelle Memorial Institute
import json
import os
import sys
import pandas as pd
import helics
import time
import pv3_poly as pv3_model
#import h5py

def newDouble(val, sub):
  if (sub is not None) and (helics.helicsInputIsUpdated(sub)):
    val = helics.helicsInputGetDouble(sub)
  return val

def newComplexMag(val, sub):
  if (sub is not None) and (helics.helicsInputIsUpdated(sub)):
#    re, im = helics.helicsInputGetComplex(sub)
#    cval = complex(re, im)
    cval = helics.helicsInputGetComplex(sub)
    val = abs(cval)
  return val

def helics_loop(cfg_filename, hdf5_filename):
  fp = open (cfg_filename, 'r')
  cfg = json.load (fp)
  tmax = cfg['application']['Tmax']
  fp.close()

  model = pv3_model.pv3 ()
  model.set_sim_config (cfg['application'], model_only=False)
  Lf = 0.0 # 2.0   # mH
  Cf = 0.0 # 20.0  # uH
  Lc = 0.0 # 0.4   # mH
  # model.set_LCL_filter (Lf=Lf*1.0e-3, Cf=Cf*1.0e-6, Lc=Lc*1.0e-3)
  model.start_simulation ()

  h_fed = helics.helicsCreateValueFederateFromConfig(cfg_filename)
  fed_name = helics.helicsFederateGetName(h_fed)
  pub_count = helics.helicsFederateGetPublicationCount(h_fed)
  sub_count = helics.helicsFederateGetInputCount(h_fed)
  period = int(helics.helicsFederateGetTimeProperty(h_fed, helics.helics_property_time_period))
  print('Federate {:s} has {:d} pub and {:d} sub, {:d} period'.format(fed_name, pub_count, sub_count, period), flush=True)

  pub_Vdc = None
  pub_Idc = None
  pub_Id = None
  pub_Iq = None
  for i in range(pub_count):
    pub = helics.helicsFederateGetPublicationByIndex(h_fed, i)
    key = helics.helicsPublicationGetName(pub)
    print ('pub', i, key)
    if 'Vdc' in key:
      pub_Vdc = pub
    elif 'Idc' in key:
      pub_Idc = pub
    elif 'Id' in key:
      pub_Id = pub
    elif 'Iq' in key:
      pub_Iq = pub
    else:
      print (' ** could not match', key)

  sub_Vrms = None
  sub_G = None
  sub_T = None
  sub_Md = None
  sub_Mq = None
  sub_Fc = None
  sub_Ctl = None
  for i in range(sub_count):
    sub = helics.helicsFederateGetInputByIndex(h_fed, i)
    key = helics.helicsSubscriptionGetTarget(sub)
    print ('sub', i, key)
    if 'Vrms' in key:
      sub_Vrms = sub
    elif 'G' in key:
      sub_G = sub
    elif 'T' in key:
      sub_T = sub
    elif 'Md' in key:
      sub_Md = sub
    elif 'Mq' in key:
      sub_Mq = sub
    elif 'Fc' in key:
      sub_Fc = sub
    elif 'Ctl' in key:
      sub_Ctl = sub
    else:
      print (' ** could not match', key)

  Vrms = 0.0
  T = 0.0
  G = 0.0
  Md = 0.0
  Mq = 0.0
  Fc = 0.0
  Ctl = 0.0
  ts = 0
  rows = []

  helics.helicsFederateEnterExecutingMode(h_fed)
  # some notes on helicsInput timing
  #  1) initial values are garbage until the other federate actually publishes
  #  2) helicsInputIsValid checks the subscription pipeline for validity, but not the value
  #  3) helicsInputIsUpdated resets to False immediately after you read the value,
  #     will become True if value changes later
  #  4) helicsInputLastUpdateTime is > 0 only after the other federate published its first value
  while ts < tmax:
    Ctl = newDouble (Ctl, sub_Ctl)
    T = newDouble (T, sub_T)
    G = newDouble (G, sub_G)
    Md = newDouble (Md, sub_Md)
    Mq = newDouble (Mq, sub_Mq)
    Fc = newDouble (Fc, sub_Fc)
    Vrms = newComplexMag (Vrms, sub_Vrms)
    GVrms = 0.001 * G * Vrms

    print ('{:6.3f}, Vrms={:.3f}, G={:.1f}, GVrms={:.3f}, T={:.3f}, Md={:.3f}, Mq={:.3f}, Fc={:.3f}, Ctl={:.1f}'.format(ts, Vrms, G, GVrms, T, Md, Mq, Fc, Ctl))

    Vdc, Idc, Id, Iq = model.step_simulation (G=G, T=T, Md=Md, Mq=Mq, Fc=Fc, Vrms=Vrms, Ctl=Ctl, GVrms=GVrms)

    if pub_Idc is not None:
      helics.helicsPublicationPublishDouble(pub_Idc, Idc)
    if pub_Idc is not None:
      helics.helicsPublicationPublishDouble(pub_Vdc, Vdc)
    if pub_Id is not None:
      helics.helicsPublicationPublishComplex(pub_Id, Id+0j)
    if pub_Iq is not None:
      helics.helicsPublicationPublishComplex(pub_Iq, Iq+0j)

    dict = {'t':ts,'G':G,'T':T,'Md':Md,'Mq':Mq,'Fc':Fc,'Ctl':Ctl,'Vrms':Vrms,'GVrms':GVrms,'Vdc':Vdc,'Idc':Idc,'Id':Id,'Iq':Iq}
    rows.append (dict)
    ts = helics.helicsFederateRequestTime(h_fed, tmax)
  helics.helicsFederateDestroy(h_fed)

  print ('simulation done, writing output to', hdf5_filename)
  df = pd.DataFrame (rows)
  df.to_hdf (hdf5_filename, 'basecase', mode='w', complevel=9)

if __name__ == '__main__':
  t0 = time.process_time()
  cfg_filename = 'pv3_server.json'
  hdf5_filename = 'pv3_server.hdf5'
  helics_loop(cfg_filename, hdf5_filename)
  t1 = time.process_time()
  print ('PV3 Server elapsed time = {:.4f} seconds.'.format (t1-t0))

