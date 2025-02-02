'''
@paper: GAN Prior Embedded Network for Blind Face Restoration in the Wild (CVPR2021)
@author: yangxy (yangtao9009@gmail.com)
'''
import torch
import os
import cv2
import glob
import numpy as np
from torch import nn
import torch.nn.functional as F
from torchvision import transforms, utils
from gpen_model_script import FullGenerator

class FaceGAN(object):
    def __init__(self, base_dir='./', size=512, model=None, channel_multiplier=2, narrow=1, key=None, is_norm=True, device='cuda'):
        self.mfile = os.path.join(base_dir, 'weights', model+'.pth')
        self.n_mlp = 8
        self.device = device
        self.is_norm = is_norm
        self.resolution = size
        self.key = key
        self.load_model(channel_multiplier, narrow)

    def load_model(self, channel_multiplier=2, narrow=1):
        self.model = FullGenerator(self.resolution, 512, self.n_mlp, channel_multiplier, narrow=narrow, device=self.device)
        pretrained_dict = torch.load(self.mfile, map_location=torch.device('cpu'))
        if self.key is not None: pretrained_dict = pretrained_dict[self.key]
        self.model.load_state_dict(pretrained_dict)
        ###转torch1.3.1模型
        #torch.save(self.model.state_dict(), "gpen_resave.pth",_use_new_zipfile_serialization=False)
        self.model.to(self.device)
        self.model.eval()
        ###转TensorScript
        img_tensor = torch.randn(1, 3, self.resolution, self.resolution, device=self.device)
        traced_script_module_encoder = torch.jit.trace(self.model, (img_tensor))
        traced_script_module_encoder.save('gpen.pt')

    def process(self, img):
        img = cv2.resize(img, (self.resolution, self.resolution))
        img_t = self.img2tensor(img)

        with torch.no_grad():
            out, __ = self.model(img_t)

        out = self.tensor2img(out)

        return out

    def img2tensor(self, img):
        img_t = torch.from_numpy(img).to(self.device)/255.
        if self.is_norm:
            img_t = (img_t - 0.5) / 0.5
        img_t = img_t.permute(2, 0, 1).unsqueeze(0).flip(1) # BGR->RGB
        return img_t

    def tensor2img(self, img_t, pmax=255.0, imtype=np.uint8):
        if self.is_norm:
            img_t = img_t * 0.5 + 0.5
        img_t = img_t.squeeze(0).permute(1, 2, 0).flip(2) # RGB->BGR
        img_np = np.clip(img_t.float().cpu().numpy(), 0, 1) * pmax

        return img_np.astype(imtype)
