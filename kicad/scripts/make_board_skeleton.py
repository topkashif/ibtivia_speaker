#!/usr/bin/env python3
"""Create the Neo N1 board skeleton with the M2 4-layer stackup.

Run with KiCad's bundled Python:
    "/c/Program Files/KiCad/10.0/bin/python.exe" kicad/scripts/make_board_skeleton.py

Creates kicad/neo_n1.kicad_pcb with 4 copper layers, inner layers renamed
to the M2 assignment (In1 = GND, In2 = PWR; F.Cu/B.Cu are the signal layers).
Physical stackup values (thickness/material) are decided in M3 once the fab
house is chosen - see kicad/stackup.md.
"""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(HERE, os.pardir, "neo_n1.kicad_pcb")

b = pcbnew.CreateEmptyBoard()
b.SetCopperLayerCount(4)
b.SetLayerName(pcbnew.In1_Cu, "GND")
b.SetLayerName(pcbnew.In2_Cu, "PWR")

# Placeholder outline so DRC has a valid Edge.Cuts polygon; the real
# floorplan outline replaces this in M3.
outline = pcbnew.PCB_SHAPE(b)
outline.SetShape(pcbnew.SHAPE_T_RECT)
outline.SetLayer(pcbnew.Edge_Cuts)
outline.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(0), pcbnew.FromMM(0)))
outline.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(50), pcbnew.FromMM(40)))
b.Add(outline)

b.Save(BOARD)
print("saved:", os.path.abspath(BOARD))

# round-trip verify
b2 = pcbnew.LoadBoard(BOARD)
print("copper layer count:", b2.GetCopperLayerCount())
for lid in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
    print(f"  layer {lid}: {b2.GetLayerName(lid)}")
