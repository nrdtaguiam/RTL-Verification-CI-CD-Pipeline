# Makefile
# cocotb simulation configuration

SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Point to design files (use shell pwd for absolute path inside WSL/Linux)
VERILOG_SOURCES += $(shell pwd)/design.v

# Top-level module name in the Verilog code
TOPLEVEL = alu

# Python test module name (without .py extension)
MODULE = test_design

# Pass compile macro to Verilog to enable VCD dumping
COMPILE_ARGS += -DCOCOTB_SIM

# Include cocotb makefile rules
include $(shell cocotb-config --makefiles)/Makefile.sim
