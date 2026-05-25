# test_design.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly
import random

# Reference ALU implementation in Python
def reference_alu(a, b, opcode, width=8):
    mask = (1 << width) - 1
    # Get signed representations for signed overflow & comparisons
    a_signed = a if (a < (1 << (width - 1))) else a - (1 << width)
    b_signed = b if (b < (1 << (width - 1))) else b - (1 << width)
    
    carry_out = 0
    overflow = 0
    res = 0
    
    if opcode == 0:  # ADD
        res_full = a + b
        res = res_full & mask
        carry_out = 1 if (res_full > mask) else 0
        res_signed = res if (res < (1 << (width - 1))) else res - (1 << width)
        overflow = 1 if ((a_signed + b_signed) != res_signed) else 0
    elif opcode == 1:  # SUB
        res_full = a - b
        res = res_full & mask
        carry_out = 1 if (a < b) else 0
        res_signed = res if (res < (1 << (width - 1))) else res - (1 << width)
        overflow = 1 if ((a_signed - b_signed) != res_signed) else 0
    elif opcode == 2:  # AND
        res = a & b
    elif opcode == 3:  # OR
        res = a | b
    elif opcode == 4:  # XOR
        res = a ^ b
    elif opcode == 5:  # NOT
        res = (~a) & mask
    elif opcode == 6:  # LSL
        shift = b & 7
        res = (a << shift) & mask
    elif opcode == 7:  # LSR
        shift = b & 7
        res = (a >> shift) & mask
    elif opcode == 8:  # ASR
        shift = b & 7
        res = (a_signed >> shift) & mask
    elif opcode == 9:  # EQ
        res = mask if (a == b) else 0
    elif opcode == 10:  # GT
        res = mask if (a_signed > b_signed) else 0
    elif opcode == 11:  # LT
        res = mask if (a_signed < b_signed) else 0
    else:
        res = 0
        
    zero = 1 if (res == 0) else 0
    negative = 1 if (res & (1 << (width - 1))) else 0
    
    return res, carry_out, zero, overflow, negative

async def setup_dut(dut):
    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    # Assert reset
    dut.rst_n.value = 0
    dut.en.value = 0
    dut.opcode.value = 0
    dut.a.value = 0
    dut.b.value = 0
    
    # Wait 2 clock cycles
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    
    # Deassert reset
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

@cocotb.test()
async def test_reset_state(dut):
    """Verify that reset drives all registers to 0."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    
    dut.rst_n.value = 0
    dut.en.value = 1
    dut.opcode.value = 3
    dut.a.value = 0xFF
    dut.b.value = 0x55
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    
    assert dut.result.value == 0, f"Expected result 0 on reset, got {dut.result.value}"
    assert dut.carry_out.value == 0, "Expected carry_out 0 on reset"
    assert dut.zero.value == 0, "Expected zero 0 on reset"
    assert dut.overflow.value == 0, "Expected overflow 0 on reset"
    assert dut.negative.value == 0, "Expected negative 0 on reset"

@cocotb.test()
async def test_enable_gate(dut):
    """Verify that outputs are held constant when clock enable (en) is low."""
    await setup_dut(dut)
    
    # Perform an ADD operation with en=1
    await FallingEdge(dut.clk)
    dut.a.value = 10
    dut.b.value = 20
    dut.opcode.value = 0  # ADD
    dut.en.value = 1
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 30, f"Expected 30, got {dut.result.value}"
    
    # Now set en=0, change inputs, and verify outputs don't change
    await FallingEdge(dut.clk)
    dut.a.value = 50
    dut.b.value = 50
    dut.en.value = 0
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 30, f"Expected result to be held at 30, but it changed to {dut.result.value}"

@cocotb.test()
async def test_arithmetic_ops(dut):
    """Verify ADD and SUB operations, including carry/borrow and overflow."""
    await setup_dut(dut)
    
    # 1. Simple ADD: 5 + 3 = 8
    await FallingEdge(dut.clk)
    dut.a.value = 5
    dut.b.value = 3
    dut.opcode.value = 0  # ADD
    dut.en.value = 1
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 8
    assert dut.carry_out.value == 0
    assert dut.zero.value == 0
    assert dut.overflow.value == 0
    assert dut.negative.value == 0
    
    # 2. ADD with carry: 250 + 10 = 260 -> 4 (8-bit wrap), carry_out=1
    await FallingEdge(dut.clk)
    dut.a.value = 250
    dut.b.value = 10
    dut.opcode.value = 0  # ADD
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 4
    assert dut.carry_out.value == 1
    assert dut.overflow.value == 0
    
    # 3. Signed ADD with overflow: 120 + 10 = 130 -> -126 (signed 8-bit overflow)
    await FallingEdge(dut.clk)
    dut.a.value = 120
    dut.b.value = 10
    dut.opcode.value = 0  # ADD
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 130
    assert dut.overflow.value == 1
    
    # 4. Simple SUB: 10 - 4 = 6
    await FallingEdge(dut.clk)
    dut.a.value = 10
    dut.b.value = 4
    dut.opcode.value = 1  # SUB
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 6
    assert dut.carry_out.value == 0
    assert dut.overflow.value == 0
    
    # 5. SUB with borrow: 3 - 5 = 254 (-2), carry_out=1 (borrow)
    await FallingEdge(dut.clk)
    dut.a.value = 3
    dut.b.value = 5
    dut.opcode.value = 1  # SUB
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 254
    assert dut.carry_out.value == 1
    assert dut.overflow.value == 0
    assert dut.negative.value == 1

@cocotb.test()
async def test_logical_ops(dut):
    """Verify bitwise operations: AND, OR, XOR, NOT."""
    await setup_dut(dut)
    
    # AND: 0xAA & 0x55 = 0x00
    await FallingEdge(dut.clk)
    dut.a.value = 0xAA
    dut.b.value = 0x55
    dut.opcode.value = 2  # AND
    dut.en.value = 1
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0x00
    assert dut.zero.value == 1
    
    # OR: 0xF0 | 0x0F = 0xFF
    await FallingEdge(dut.clk)
    dut.a.value = 0xF0
    dut.b.value = 0x0F
    dut.opcode.value = 3  # OR
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0xFF
    assert dut.zero.value == 0
    assert dut.negative.value == 1
    
    # XOR: 0x55 ^ 0xFF = 0xAA
    await FallingEdge(dut.clk)
    dut.a.value = 0x55
    dut.b.value = 0xFF
    dut.opcode.value = 4  # XOR
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0xAA
    
    # NOT: ~0x00 = 0xFF
    await FallingEdge(dut.clk)
    dut.a.value = 0x00
    dut.opcode.value = 5  # NOT
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0xFF

@cocotb.test()
async def test_shift_ops(dut):
    """Verify LSL, LSR, and ASR shift operations."""
    await setup_dut(dut)
    
    # LSL: 0x07 << 3 = 0x38 (56)
    await FallingEdge(dut.clk)
    dut.a.value = 0x07
    dut.b.value = 3
    dut.opcode.value = 6  # LSL
    dut.en.value = 1
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0x38
    
    # LSR: 0xF0 >> 4 = 0x0F
    await FallingEdge(dut.clk)
    dut.a.value = 0xF0
    dut.b.value = 4
    dut.opcode.value = 7  # LSR
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0x0F
    
    # ASR positive: 0x40 >>> 2 = 0x10
    await FallingEdge(dut.clk)
    dut.a.value = 0x40
    dut.b.value = 2
    dut.opcode.value = 8  # ASR
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0x10
    
    # ASR negative: 0x80 (-128) >>> 2 = 0xE0 (-32)
    await FallingEdge(dut.clk)
    dut.a.value = 0x80
    dut.b.value = 2
    dut.opcode.value = 8  # ASR
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0xE0

@cocotb.test()
async def test_comparison_ops(dut):
    """Verify EQ, GT, LT comparisons."""
    await setup_dut(dut)
    
    # EQ: 5 == 5 -> 0xFF (True)
    await FallingEdge(dut.clk)
    dut.a.value = 5
    dut.b.value = 5
    dut.opcode.value = 9  # EQ
    dut.en.value = 1
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0xFF
    
    # EQ: 5 == 3 -> 0x00 (False)
    await FallingEdge(dut.clk)
    dut.a.value = 5
    dut.b.value = 3
    dut.opcode.value = 9  # EQ
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0x00
    
    # GT: 5 > -2 (0xFE) -> 0xFF
    await FallingEdge(dut.clk)
    dut.a.value = 5
    dut.b.value = 0xFE
    dut.opcode.value = 10  # GT
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0xFF
    
    # LT: -2 (0xFE) < 5 -> 0xFF
    await FallingEdge(dut.clk)
    dut.a.value = 0xFE
    dut.b.value = 5
    dut.opcode.value = 11  # LT
    
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.result.value == 0xFF

@cocotb.test()
async def test_randomized_fuzzing(dut):
    """Drive 100 randomized inputs and compare against the Python reference ALU model."""
    await setup_dut(dut)
    
    random.seed(42)
    
    for i in range(100):
        a_val = random.randint(0, 255)
        b_val = random.randint(0, 255)
        op_val = random.randint(0, 11)
        
        await FallingEdge(dut.clk)
        dut.a.value = a_val
        dut.b.value = b_val
        dut.opcode.value = op_val
        dut.en.value = 1
        
        await RisingEdge(dut.clk)
        await ReadOnly()
        
        # Calculate golden reference
        ref_res, ref_carry, ref_zero, ref_ov, ref_neg = reference_alu(a_val, b_val, op_val, width=8)
        
        # Capture DUT outputs
        dut_res = int(dut.result.value)
        dut_carry = int(dut.carry_out.value)
        dut_zero = int(dut.zero.value)
        dut_ov = int(dut.overflow.value)
        dut_neg = int(dut.negative.value)
        
        # Assertions
        assert dut_res == ref_res, f"[{i}] OP={op_val} A={a_val} B={b_val}: Expected result={ref_res}, got {dut_res}"
        assert dut_carry == ref_carry, f"[{i}] OP={op_val} A={a_val} B={b_val}: Expected carry_out={ref_carry}, got {dut_carry}"
        assert dut_zero == ref_zero, f"[{i}] OP={op_val} A={a_val} B={b_val}: Expected zero={ref_zero}, got {dut_zero}"
        assert dut_ov == ref_ov, f"[{i}] OP={op_val} A={a_val} B={b_val}: Expected overflow={ref_ov}, got {dut_ov}"
        assert dut_neg == ref_neg, f"[{i}] OP={op_val} A={a_val} B={b_val}: Expected negative={ref_neg}, got {dut_neg}"
