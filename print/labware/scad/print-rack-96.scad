// SBS 96 rack, 9 mm pitch
// part id: print-rack-96  license: CERN-OHL-W-2.0
// derived from: obs-tipbox-1000-blue, obs-tipbox-200f-magenta, obs-tipbox-purple-hinged, obs-microtube-96-purple
// Edit the parameters to remix. Catalog dimensions marked est. need calipers before a production run.
use <labware.scad>

sbs_plate(rows = 8, cols = 12, pitch = 9.0, hole_d = 5.8, height = 20.0, a1_x = 14.38, a1_y = 11.24, footprint_x = 127.76, footprint_y = 85.48);
