#!/bin/bash
rm ExpComb.blif ExpSeq.blif
yosys -p "synth_ice40 -blif ExpComb.blif" ExpComb.v
yosys -p "synth_ice40 -blif ExpSeq.blif" ExpSeq.v
