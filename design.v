// design.v
// A parameterizable synchronous ALU
module alu #(
    parameter DATA_WIDTH = 8
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  en,
    input  wire [3:0]            opcode,
    input  wire [DATA_WIDTH-1:0] a,
    input  wire [DATA_WIDTH-1:0] b,
    output reg  [DATA_WIDTH-1:0] result,
    output reg                   carry_out,
    output reg                   zero,
    output reg                   overflow,
    output reg                   negative
);

    // Opcodes
    localparam OP_ADD = 4'b0000;
    localparam OP_SUB = 4'b0001;
    localparam OP_AND = 4'b0010;
    localparam OP_OR  = 4'b0011;
    localparam OP_XOR = 4'b0100;
    localparam OP_NOT = 4'b0101;
    localparam OP_LSL = 4'b0110;
    localparam OP_LSR = 4'b0111;
    localparam OP_ASR = 4'b1000;
    localparam OP_EQ  = 4'b1001;
    localparam OP_GT  = 4'b1010;
    localparam OP_LT  = 4'b1011;

    // Internal registers for combinational ALU output
    reg [DATA_WIDTH-1:0] next_result;
    reg                  next_carry_out;
    reg                  next_zero;
    reg                  next_overflow;
    reg                  next_negative;

    // Combinational Logic
    always @(*) begin
        // Default values
        next_result    = {DATA_WIDTH{1'b0}};
        next_carry_out = 1'b0;
        next_zero      = 1'b0;
        next_overflow  = 1'b0;
        next_negative  = 1'b0;

        if (en) begin
            case (opcode)
                OP_ADD: begin
                    {next_carry_out, next_result} = a + b;
                    // Overflow flag for signed addition: operands have same sign, result has opposite sign
                    next_overflow = (a[DATA_WIDTH-1] == b[DATA_WIDTH-1]) && (next_result[DATA_WIDTH-1] != a[DATA_WIDTH-1]);
                end
                OP_SUB: begin
                    {next_carry_out, next_result} = a - b;
                    // Overflow flag for signed subtraction: operands have opposite sign, result sign matches B's sign
                    next_overflow = (a[DATA_WIDTH-1] != b[DATA_WIDTH-1]) && (next_result[DATA_WIDTH-1] == b[DATA_WIDTH-1]);
                end
                OP_AND: begin
                    next_result = a & b;
                end
                OP_OR: begin
                    next_result = a | b;
                end
                OP_XOR: begin
                    next_result = a ^ b;
                end
                OP_NOT: begin
                    next_result = ~a;
                end
                OP_LSL: begin
                    next_result = a << b[2:0]; // Limit shift range to 0-7 for 8-bit safety
                end
                OP_LSR: begin
                    next_result = a >> b[2:0];
                end
                OP_ASR: begin
                    next_result = $signed(a) >>> b[2:0];
                end
                OP_EQ: begin
                    next_result = (a == b) ? {DATA_WIDTH{1'b1}} : {DATA_WIDTH{1'b0}};
                end
                OP_GT: begin
                    next_result = ($signed(a) > $signed(b)) ? {DATA_WIDTH{1'b1}} : {DATA_WIDTH{1'b0}};
                end
                OP_LT: begin
                    next_result = ($signed(a) < $signed(b)) ? {DATA_WIDTH{1'b1}} : {DATA_WIDTH{1'b0}};
                end
                default: begin
                    next_result = {DATA_WIDTH{1'b0}};
                end
            endcase

            next_zero     = (next_result == {DATA_WIDTH{1'b0}});
            next_negative = next_result[DATA_WIDTH-1];
        end else begin
            // Hold state when enable is low
            next_result    = result;
            next_carry_out = carry_out;
            next_zero      = zero;
            next_overflow  = overflow;
            next_negative  = negative;
        end
    end

    // Sequential Logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result    <= {DATA_WIDTH{1'b0}};
            carry_out <= 1'b0;
            zero      <= 1'b0;
            overflow  <= 1'b0;
            negative  <= 1'b0;
        end else begin
            result    <= next_result;
            carry_out <= next_carry_out;
            zero      <= next_zero;
            overflow  <= next_overflow;
            negative  <= next_negative;
        end
    end

    // Dump waveform if COCOTB_SIM is defined
    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("waveform.vcd");
        $dumpvars(0, alu);
    end
    `endif

endmodule
