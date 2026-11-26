# o3d_bridge: X3D ⇄ Open3D / Open3D-ML

`x3do3d.py` (numpy + lxml; open3d lazily). X3D → Open3D (`read_x3d`: PointSet, IndexedFaceSet, TriangleSet, IndexedTriangleSet; Transform, Switch, DEF/USE),
Open3D → X3D (`pointcloud_to_x3d`, `mesh_to_x3d`), Open3D-ML segmentation → labelled X3D (`segmentation_to_x3d`, `read_segmentation`),
3D detections ⇄ X3D (`boxes_to_x3d`, `read_boxes`), frames (`ml_frame_from_source`). Demo: x3d.demo Demo 81.

Tests: `X3D_MCP_PATH=<x3d_mcp> pytest tests/test_x3do3d.py` (model test needs `X3DO3D_CKPT`, `X3DO3D_CFG`).

## Install notes (measured 26 Nov 2026)
- `pip install open3d torch==2.13.0 'open3d[ml]' tensorboard nvidia-cuda-runtime-cu12`; Open3D 0.20.0 needs exactly torch 2.13.*, the CUDA build (the CPU wheel fails with "Could not load this library").
  Put the dir holding `libcudart.so.12` on `LD_LIBRARY_PATH`. On a bare Linux box also `apt install libegl1 libgl1`.
- Frames: Open3D-ML is Z up; S3DIS weights want the floor near z=0 (without it 74% of labels change). `predict_scores` is not a softmax; use max/sum.
- Pipeline output is stochastic (random centre-point sampling): compare against a repeat run, not a single one.
