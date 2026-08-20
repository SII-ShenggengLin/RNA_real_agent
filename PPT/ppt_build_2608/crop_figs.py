# -*- coding: utf-8 -*-
"""Crop paper figures into PPT-ready panels."""
import os
from PIL import Image

ROOT = "/inspire/hdd/global_user/linshenggeng-240107100015/RNA_real_agent"
PAPER = os.path.join(ROOT, "rna_agent_system/experiments/plots/paper")
OUT = os.path.join(ROOT, "PPT/ppt_build_2608/crops")
os.makedirs(OUT, exist_ok=True)

# name -> (src, x0, y0, x1, y1) relative coords
CROPS = {
    # fig1 2130x2520
    "f1_arch":      ("fig1.png", 0.000, 0.020, 0.600, 1.000),
    # fig2 4050x3780
    "f2_cai":       ("fig2.png", 0.000, 0.000, 0.285, 0.245),
    "f2_sirna":     ("fig2.png", 0.520, 0.000, 0.760, 0.245),
    "f2_rnasmol":   ("fig2.png", 0.765, 0.000, 1.000, 0.245),
    "f2_coverage":  ("fig2.png", 0.000, 0.752, 0.305, 1.000),
    # fig3 2160x3120
    "f3_screening": ("fig3.png", 0.000, 0.000, 0.545, 0.305),
    "f3_mrna":      ("fig3.png", 0.000, 0.650, 1.000, 0.965),
    # fig5 2160x2910
    "f5_e5":        ("fig5.png", 0.000, 0.000, 0.575, 0.250),
    "f5_e6eff":     ("fig5.png", 0.615, 0.000, 1.000, 0.250),
    "f5_e6heat":    ("fig5.png", 0.000, 0.275, 1.000, 0.495),
    "f5_e14":       ("fig5.png", 0.000, 0.738, 1.000, 0.985),
    # fig6 2130x2700
    "f6_fail":      ("fig6.png", 0.000, 0.000, 1.000, 0.310),
}

for name, (src, x0, y0, x1, y1) in CROPS.items():
    im = Image.open(os.path.join(PAPER, src))
    W, H = im.size
    box = (int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H))
    crop = im.crop(box)
    path = os.path.join(OUT, name + ".png")
    crop.save(path)
    print(f"{name}: {crop.size}  <- {src} {box}")

# fig4 used whole - just copy
im = Image.open(os.path.join(PAPER, "fig4.png"))
im.save(os.path.join(OUT, "f4_whole.png"))
print("f4_whole:", im.size)
