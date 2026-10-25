// SBS 2x3 screened grid frame
// part id: print-grid-mesh  license: CERN-OHL-S-2.0
// derived from: obs-printed-grid-mesh, obs-perforated-sheet
// Edit the parameters to remix. Catalog dimensions marked est. need calipers before a production run.
use <labware.scad>

grid_frame(footprint_x = 127.76, footprint_y = 85.48, height = 8.0, wall = 4.0, rows = 2, cols = 3, rib = 3.0, floor = 1.2, mesh_hole = 2.0, mesh_pitch = 3.0);
