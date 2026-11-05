"""Shared row-3 geometry for the Fig. 3 panels d, e and f (2026-10-10
alignment batch, user-directed).

The three panels share one exact millimetre canvas and one identical axes
rectangle, so their coordinate frames land on the same lines once the
composite assembler (`fig3_assemble.py`, the "grid3" row) centres them in
its three equal columns: same y-axis position, same x-axis baseline, same
panel width and height, letters level.  The tight-crop saves
(`bbox_inches="tight"`) these panels previously used are retired (the
figS1-S6 house convention): a tight crop shrinks each canvas to its own
ink, so the axes could never share absolute positions — the 2026-10-02
renders came out 54.0/53.9/53.6 mm wide and 40.6/34.4/42.3 mm tall.

Geometry (mm): canvas 54.0 x 52.0; axes 12.0 from the left (the widest
left stack needs 10.8 — fig3e's "EGARPS" tick labels at pad 2, and
fig3d's log ticks plus rotated y-label), 12.0 from the bottom (fig3e's
style-key row under its x-label stack), 41.0 wide (1.0 mm right margin),
36.0 tall (fig3f's audited axes height; 4.0 mm head band).  54.0 mm
sits within the assembler's grid3 column limit (content width 480.9 pt
gives 152.96 pt columns + the 0.5 pt tolerance).
"""
CANVAS_W_MM = 54.0
CANVAS_H_MM = 52.0
AX_L_MM = 12.0
AX_B_MM = 12.0
AX_W_MM = 41.0
AX_H_MM = 36.0
