﻿import numpy as np
import scipy.ndimage
import gzip
import os
import os.path
import netCDF4
import nibabel
import PIL

# Name, Label, T1, T2, T2*, PD, filename
params_15 = {
    0: ["Background", 0, 0, 0, 0, 0, "subject{}_bck_v{}"],
    1: ["CSF", 1, 2569.0, 329, 58, 1, "subject{}_csf_v{}"],
    2: ["Grey Matter", 2.0, 833, 83, 69, 0.86, "subject{}_gm_v{}"], # 577
    3: ["White Matter", 3.0, 500, 70, 61, 0.77, "subject{}_wm_v{}"], # 346
    4: ["Fat", 4, 350.0, 70.0, 58, 1, "subject{}_fat_v{}"],
    5: ["Muscle", 5, 900.0, 47, 30, 1, "subject{}_muscles_v{}"],
    6: ["Muscle / Skin", 6, 569.0, 329, 58, 1, "subject{}_muscles_skin_v{}"],
    7: ["Skull", 7, 0, 0, 0, 0, "subject{}_skull_v{}"],
    8: ["Vessels", 8, 2569.0, 329, 0, 1, "subject{}_vessels_v{}"],
    9: ["Around fat", 9, 500.0, 70, 61, 0.77, "subject{}_fat2_v{}"],
    10: ["Dura Matter", 10, 2569.0, 329, 58, 1, "subject{}_dura_v{}"],
    11: ["Bone Marrow", 11, 500.0, 70, 61, 0.77, "subject{}_marrow_v{}"]
}

params_3 = { # 3T params
    0: ["Background", 0, 0, 0, 0, 0, "subject{}_bck_v{}"],
    1: ["CSF", 1, 4163.0, 329, 58, 1, "subject{}_csf_v{}"],
    2: ["Grey Matter", 2.0, 1433.2, 92.6, 69, 0.86, "subject{}_gm_v{}"], # 993
    3: ["White Matter", 3.0, 866.9, 60.8, 61, 0.77, "subject{}_wm_v{}"], # 600
    4: ["Fat", 4, 346, 70.0, 58, 1, "subject{}_fat_v{}"],
    5: ["Muscle", 5, 1232.9, 37.2, 30, 1, "subject{}_muscles_v{}"],
    6: ["Muscle / Skin", 6, 377.0, 97.5, 58, 1, "subject{}_muscles_skin_v{}"],
    7: ["Skull", 7, 0, 0, 0, 0, "subject{}_skull_v{}"],
    8: ["Vessels", 8, 1984.4, 275.0, 0, 1, "subject{}_vessels_v{}"],
    9: ["Around fat", 9, 346, 70, 58, 0.77, "subject{}_fat2_v{}"],
    10: ["Dura Matter", 10, 2569.0, 329, 58, 1, "subject{}_dura_v{}"],
    11: ["Bone Marrow", 11, 365.0, 133.0, 61, 0.77, "subject{}_marrow_v{}"]
}

nii_names = {0: "BCK", 1:"CSF", 2:"GM", 3:"WM", 4:"FAT", 5:"MUSCLES", 6:"SKIN-MUSCLES", 7:"SKULL", 8:"VESSELS", 9:"FAT2", 10:"DURA", 11:"MARROW"}
brainWeb_names = {0: "subject{}_bck_v", 1:"subject{}_csf_v", 2:"subject{}_gm_v", 3:"subject{}_wm_v", 4:"subject{}_fat_v", 5:"subject{}_muscles_v",
 6:"subject{}_muscles_skin_v", 7:"subject{}_skull_v", 8:"subject{}_vessels", 9:"subject{}_fat2_v", 10:"subject{}_dura_v", 11:"subject{}_marrow_v"}

xdim = 362
ydim = 434
zdim = 362
shape = (zdim,ydim,xdim)

def read_minc(params, names, in_dir, sub=(), trans=None, nib=False):
    print(in_dir)

    t1 = np.zeros(shape, dtype=np.float32)
    t2 = np.zeros(shape, dtype=np.float32)
    pd = np.zeros(shape, dtype=np.float32)
    s = np.zeros(shape, dtype=np.float32)

    for p in params:
        #print(p, os.path.join(in_dir, names[p].format(*sub)+".mnc"))
        if nib:
            d = nibabel.load(os.path.join(in_dir, names[p].format(*sub)+".mnc"))
            img = d.get_fdata()
            a = np.array(img, dtype=np.float32)
        else:
            with gzip.open(os.path.join(in_dir, names[p].format(*sub)+".mnc.gz"), "rb") as f:
                d = netCDF4.Dataset("in_memory.mnc", memory=np.array(f.read()))
                img = np.array(d.variables["image"])
                a = np.array(img, dtype=np.float32)
        if trans is not None:
            #print(np.min(a), np.max(a), np.mean(a), np.median(a))
            a = trans(a)
            #print(np.min(a), np.max(a), np.mean(a), np.median(a))
        t1 = t1 + a*params[p][2]
        t2 = t2 + a*params[p][3]
        pd = pd + a*params[p][-2]
        s = s + a

    #print(np.min(s), np.max(s), np.mean(s), np.median(s), np.count_nonzero(s>1.1), np.count_nonzero(s<0.9))
    s[s==0] = 1
    t1 = t1/s
    t2 = t2/s
    pd = pd/s
    
    #print(np.min(t1), np.max(t1), np.quantile(t1, 0.9999), np.count_nonzero(t1>np.quantile(t1, 0.9999)))

    zoom = (2**8/xdim, 2**8/ydim, 2**8/zdim)
    t1 = scipy.ndimage.zoom(t1, zoom, order=0)
    pd = scipy.ndimage.zoom(pd, zoom, order=0)
    t2 = scipy.ndimage.zoom(t2, zoom, order=0)

    return t1, t2, pd

def read_phantomag(in_dir, trans=None):
    img = None
    r1 = None
    r2 = None
    pd = None
    for i, name in enumerate(os.listdir(in_dir)):
        with PIL.Image.open(os.path.join(in_dir, name)) as f:
            if img is None:
                img = np.zeros((len(os.listdir(in_dir)), f.width, f.height, 3))
                r1 = np.zeros((len(os.listdir(in_dir)), f.width, f.height))
                r2 = np.zeros((len(os.listdir(in_dir)), f.width, f.height))
                pd = np.zeros((len(os.listdir(in_dir)), f.width, f.height))
            img[i] = np.array(f)
            r1[i] = np.array(f.getchannel("R"))
            r2[i] = np.array(f.getchannel("G"))
            pd[i] = np.array(f.getchannel("B"))
    
    #img = np.swapaxes(img, 0, 2)
    #t1 = 1/img[...,0]
    #t2 = 1/img[...,1]
    #pd = img[...,2]
    t1s = 265.824140
    t2s = 320.593736
    pds = 796.450777
    t1s = 1433.2
    t2s = 92.6
    pds = 0.86
    t1 = t1s*3*25.5/r1
    t2 = t2s*3*25.5/r2
    pd = pds*3*pd/255
    t1[r1==0] = 0
    #print(np.min(t1), np.max(t1), np.quantile(t1, 0.9999), np.count_nonzero(t1>np.quantile(t1, 0.9999)))
    t2[r2==0] = 0
    t1cutoff = 2569
    t1[t1>t1cutoff] = t1cutoff
    t2cutoff = 329
    t2[t2>t2cutoff] = t2cutoff

    zoom = (1, 2**8/t1.shape[1], 2**8/t1.shape[2])
    t1 = scipy.ndimage.zoom(t1, zoom, order=0)
    t2 = scipy.ndimage.zoom(t2, zoom, order=0)
    pd = scipy.ndimage.zoom(pd, zoom, order=0)

    return t1, t2, pd

import matplotlib.pyplot as plt
def write_files(t1, t2, pd, sub, out_dir):
    print(t1.shape, t2.shape, pd.shape)
    if not os.path.exists(os.path.join(out_dir, sub[0])):
        os.makedirs(os.path.join(out_dir, sub[0]))
    with gzip.open(os.path.join(out_dir, sub[0], "t1.bin.gz"), "wb") as f:
        mi = np.min(t1)
        ma = np.max(t1)
        print(np.min(t1), np.max(t1), np.mean(t1), np.median(t1))
        ex = np.array(255 * (t1-mi) / (ma-mi), dtype=np.uint8)
        print("t1", mi, ma, np.mean(ex), np.max(ex), np.max(255 * (t1-mi) / (ma-mi)))
        er = (255 * (t1-mi) / (ma-mi)) - ex
        #print("er", np.min(er), np.max(er), np.mean(er), np.median(er))
        f.write(np.array([mi,ma], dtype=np.float32).tobytes())
        f.write(np.array(t1.shape,dtype=np.uint16).tobytes())
        f.write(ex.tobytes())

    with gzip.open(os.path.join(out_dir, sub[0], "t2.bin.gz"), "wb") as f:
        mi = np.min(t2)
        ma = np.max(t2)
        print(np.min(t2), np.max(t2), np.mean(t2), np.median(t2))
        ex = np.array(255 * (t2-mi) / (ma-mi), dtype=np.uint8)
        print("t2", mi, ma, np.mean(ex), np.max(ex), np.max(255 * (t2-mi) / (ma-mi)))
        er = (255 * (t2-mi) / (ma-mi)) - ex
        #print("er", np.min(er), np.max(er), np.mean(er), np.median(er))
        f.write(np.array([mi,ma], dtype=np.float32).tobytes())
        f.write(np.array(t2.shape,dtype=np.uint16).tobytes())
        f.write(ex.tobytes())

    with gzip.open(os.path.join(out_dir, sub[0], "pd.bin.gz"), "wb") as f:
        mi = np.min(pd)
        ma = np.max(pd)
        print(np.min(pd), np.max(pd), np.mean(pd), np.median(pd))
        ex = np.array(255 * (pd-mi) / (ma-mi), dtype=np.uint8)
        print("pd", mi, ma, np.mean(ex), np.max(ex), np.max(255 * (pd-mi) / (ma-mi)))
        er = (255 * (pd-mi) / (ma-mi)) - ex
        #print("er", np.min(er), np.max(er), np.mean(er), np.median(er))
        f.write(np.array([mi,ma], dtype=np.float32).tobytes())
        f.write(np.array(pd.shape,dtype=np.uint16).tobytes())
        f.write(ex.tobytes())

#t1,t2,pd = read_minc(params_15, nii_names, "mni_colin27_2008_fuzzy_minc2", nib=True)
#write_files(t1, t2, pd, ("bw",), "1t")
#t1,t2,pd = read_minc(params_3, nii_names, "mni_colin27_2008_fuzzy_minc2", nib=True)
#write_files(t1, t2, pd, ("bw",), "3t")

#t1,t2,pd = read_minc(params_15, brainWeb_names, "", ("05",), trans=lambda a: (a+128)/255)
#write_files(t1, t2, pd, ("05",), "1t")
#t1,t2,pd = read_minc(params_3, brainWeb_names, "", ("05",), trans=lambda a: (a+128)/255)
#write_files(t1, t2, pd, ("05",), "3t")

#t1,t2,pd = read_minc(params_15, brainWeb_names, "", ("54",), trans=lambda a: (a+128)/255)
#x1 = t1
#x2 = t2
#xp = pd
#write_files(t1, t2, pd, ("54",), "1t")
#t1,t2,pd = read_minc(params_3, brainWeb_names, "", ("54",), trans=lambda a: (a+128)/255)
#write_files(t1, t2, pd, ("54",), "3t")

t1,t2,pd = read_phantomag("NV_1_NV_1T/QMCI")
write_files(t1,t2,pd, ("phantomag",), "1T")

t1,t2,pd = read_phantomag("NV_1_NV_1_5T/QMCI")
write_files(t1,t2,pd, ("phantomag",), "1.5T")

#fig, axs = plt.subplots(1, 2, sharey=False, tight_layout=True)
#axs[0].hist(x1.flatten(), bins=256)
#axs[1].hist(t1.flatten(), bins=256)
#fig, axs = plt.subplots(1, 2, sharey=False, tight_layout=True)
#axs[0].hist(x2.flatten(), bins=256)
#axs[1].hist(t2.flatten(), bins=256)
#fig, axs = plt.subplots(1, 2, sharey=False, tight_layout=True)
#axs[0].hist(xp.flatten(), bins=256)
#axs[1].hist(pd.flatten(), bins=256)
#plt.show()
#plt.close()
