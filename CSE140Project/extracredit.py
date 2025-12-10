# Globals
pc = 0
next_pc = 0
branch_target = 0
alu_zero = 0
total_clock_cycles = 0

# Initialize register file
rf = [0] * 32
# part 1
rf[1] = 0x20
rf[2] = 0x5
rf[10] = 0x70
rf[11] = 0x4

# Data memory
d_mem = [0] * 32
# part 1
d_mem[28] = 0x5
d_mem[29] = 0x10

# Pipeline stage registers
class IF_ID:
    def __init__(self):
        self.pc = 0
        self.instruction = ""
        self.valid = False

class ID_EX:
    def __init__(self):
        self.pc = 0
        self.rs1_val = 0
        self.rs2_val = 0
        self.rd_reg = None
        self.imm = 0
        self.operation = ""
        self.control_signals = {
            'RegWrite': 0, 'Branch': 0, 'MemRead': 0, 'MemWrite': 0,
            'MemtoReg': 0, 'ALUSrc': 0, 'ALUOp': '00', 'JAL': 0, 'JALR': 0
        }
        self.valid = False

class EX_MEM:
    def __init__(self):
        self.pc = 0
        self.alu_result = 0
        self.rs2_val = 0
        self.rd_reg = None
        self.operation = ""
        self.control_signals = {
            'RegWrite': 0, 'Branch': 0, 'MemRead': 0, 'MemWrite': 0,
            'MemtoReg': 0, 'ALUSrc': 0, 'ALUOp': '00', 'JAL': 0, 'JALR': 0
        }
        self.valid = False
        self.return_addr = 0  # For JAL/JALR

class MEM_WB:
    def __init__(self):
        self.pc = 0
        self.alu_result = 0
        self.mem_data = 0
        self.rd_reg = None
        self.control_signals = {
            'RegWrite': 0, 'MemtoReg': 0
        }
        self.valid = False

# Initialize pipeline registers
if_id = IF_ID()
id_ex = ID_EX()
ex_mem = EX_MEM()
mem_wb = MEM_WB()

# Register ABI mapping
register_abi_map = {
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4, "t0": 5, "t1": 6, "t2": 7,
    "s0": 8, "fp": 8, "s1": 9, "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15,
    "a6": 16, "a7": 17, "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23,
    "s8": 24, "s9": 25, "s10": 26, "s11": 27, "t3": 28, "t4": 29, "t5": 30, "t6": 31
}
register_abi_reverse_map = {v: k for k, v in register_abi_map.items()}

def findOp(code):
    opcode = code[25:32]
    if opcode == "0110011": return "R"
    elif opcode in ["0010011", "0000011", "1100111"]: return "I"
    elif opcode == "0100011": return "S"
    elif opcode == "1100011": return "SB"
    elif opcode == "1101111": return "UJ"
    elif opcode == "0110111": return "U"
    return ""

def findOperation(fields, itype, opcode, mcode):
    operation = "unknown"
    
    if itype == "R":
        funct3 = fields["funct3"]
        funct7 = fields["funct7"]
        if funct7 == "0000000":
            if funct3 == "000": operation = "add"
            elif funct3 == "001": operation = "sll"
            elif funct3 == "010": operation = "slt"
            elif funct3 == "011": operation = "sltu"
            elif funct3 == "100": operation = "xor"
            elif funct3 == "101": operation = "srl"
            elif funct3 == "110": operation = "or"
            elif funct3 == "111": operation = "and"
        elif funct7 == "0100000":
            if funct3 == "000": operation = "sub"
            elif funct3 == "101": operation = "sra"

    elif itype == "I":
        funct3 = fields["funct3"]
        if opcode == "0000011":
            if funct3 == "000": operation = "lb"
            elif funct3 == "001": operation = "lh"
            elif funct3 == "010": operation = "lw"
        elif opcode == "0010011":
            if funct3 == "000": operation = "addi"
            elif funct3 == "010": operation = "slti"
            elif funct3 == "011": operation = "sltiu"
            elif funct3 == "100": operation = "xori"
            elif funct3 == "110": operation = "ori"
            elif funct3 == "111": operation = "andi"
            elif funct3 == "001": operation = "slli"
            elif funct3 == "101":
                if fields["funct7"] == "0000000": operation = "srli"
                elif fields["funct7"] == "0100000": operation = "srai"
        elif opcode == "1100111":
            operation = "jalr"

    elif itype == "S":
        funct3 = fields["funct3"]
        if funct3 == "000": operation = "sb"
        elif funct3 == "001": operation = "sh"
        elif funct3 == "010": operation = "sw"

    elif itype == "SB":
        funct3 = fields["funct3"]
        if funct3 == "000": operation = "beq"
        elif funct3 == "001": operation = "bne"
        elif funct3 == "100": operation = "blt"
        elif funct3 == "101": operation = "bge"

    elif itype == "U":
        if opcode == "0110111": operation = "lui"
        elif opcode == "0010111": operation = "auipc"

    elif itype == "UJ":
        operation = "jal"

    return operation

def findI(code, itype):
    fields = {}
    if itype in ["R", "I", "U", "UJ"]:
        fields["rd"] = code[21:26]
    
    if itype in ["R", "B", "SB", "S"]:
        fields["rs2"] = code[7:12]

    if itype in ["R", "B", "I", "SB", "S"]:
        fields["rs1"] = code[12:17]

    if itype == "R":
        fields["funct7"] = code[0:7]
        fields["funct3"] = code[17:20]
        fields["rs1"] = code[12:17]
        fields["rs2"] = code[7:12]
        fields["rd"] = code[20:25]
    
    if itype == "I":
        fields["funct3"] = code[17:20]
        fields["imm"] = sign_extend(code[0:12], 12)
        fields["rd"] = code[20:25]
    
    if itype in ["S", "SB"]:
        fields["funct3"] = code[17:20]
        imm = code[0:7] + code[20:25]
        fields["imm"] = sign_extend(imm, 12)

    if itype == "UJ":  # JAL
        imm20 = code[0]        # bit 20 (sign bit)
        imm10_1 = code[1:11]   # bits 10:1
        imm11 = code[11]       # bit 11
        imm19_12 = code[12:20] # bits 19:12
        
        imm = (sign_extend(imm20 + imm19_12 + imm11 + imm10_1, 20)) << 1
        fields["imm"] = imm
        fields["rd"] = code[20:25]
            
    return fields

def sign_extend(imm, bits):
    if isinstance(imm, str):
        imm = int(imm, 2)
    if imm & (1 << (bits-1)):
        imm -= 1 << bits
    return imm

def Fetch(instructions):
    global pc, next_pc, if_id, id_ex, ex_mem
    
    # Check for stalls (data hazards)
    stall = False
    
    
    if (ex_mem.control_signals['MemRead'] and 
        ex_mem.rd_reg is not None and 
        if_id.instruction and 
        ((int(if_id.instruction[12:17], 2) == ex_mem.rd_reg or 
         (if_id.instruction[25:32] in ["0100011", "1100011"] and  
          int(if_id.instruction[7:12], 2) == ex_mem.rd_reg)))):
        stall = True
    
    if stall:
        # Insert NOP
        if_id.instruction = "00000000000000000000000000000000"
        if_id.pc = pc
        if_id.valid = False
        return
    
    # Normal fetch
    index = pc // 4
    if index >= len(instructions):
        if_id.valid = False
        return
    
    if_id.instruction = instructions[index]
    if_id.pc = pc
    if_id.valid = True
    
    # Handle branches and jumps
    if ex_mem.control_signals['Branch'] and alu_zero:
        pc = branch_target
    elif ex_mem.control_signals['JAL']:
        pc = ex_mem.alu_result
    elif ex_mem.control_signals['JALR']:
        pc = ex_mem.alu_result & ~1
    else:
        pc += 4

def Decode():
    global if_id, id_ex, rf
    
    if not if_id.valid:
        id_ex.valid = False
        return
    
    instruction = if_id.instruction
    itype = findOp(instruction)
    fields = findI(instruction, itype)
    operation = findOperation(fields, itype, instruction[25:32], instruction)
    
    # Get register values
    rs1_reg = int(fields["rs1"], 2) if "rs1" in fields else 0
    rs2_reg = int(fields["rs2"], 2) if "rs2" in fields else 0
    rd_reg = int(fields["rd"], 2) if "rd" in fields else None
    
    # Set up ID/EX pipeline register
    id_ex.pc = if_id.pc
    id_ex.rs1_val = rf[rs1_reg]
    id_ex.rs2_val = rf[rs2_reg]
    id_ex.rd_reg = rd_reg
    id_ex.imm = fields.get("imm", 0)
    id_ex.operation = operation
    id_ex.valid = True
    
    # Set control signals
    control_signals = ControlUnit(instruction[25:32], operation)
    id_ex.control_signals = control_signals.copy()

def Execute():
    global id_ex, ex_mem, alu_zero, branch_target, pc
    
    if not id_ex.valid:
        ex_mem.valid = False
        return
    
    a = id_ex.rs1_val
    b = (id_ex.imm) if id_ex.control_signals['ALUSrc'] else id_ex.rs2_val
    result = None
    return_addr = id_ex.pc + 4
    
    if id_ex.control_signals['JAL']:
        result = id_ex.pc + id_ex.imm
    elif id_ex.control_signals['JALR']:
        result = (id_ex.rs1_val + id_ex.imm) & ~1
    elif id_ex.operation in ["add", "addi", "lw", "sw"]:
        result = a + b
    elif id_ex.operation == "sub":
        result = a - b
    elif id_ex.operation in ["and", "andi"]:
        result = a & b
    elif id_ex.operation in ["or", "ori"]:
        result = a | b
    elif id_ex.operation == "beq":
        result = a - b
        alu_zero = int(result == 0)
    
    # Set up EX/MEM pipeline register
    ex_mem.pc = id_ex.pc
    ex_mem.alu_result = result
    ex_mem.rs2_val = id_ex.rs2_val
    ex_mem.rd_reg = id_ex.rd_reg
    ex_mem.operation = id_ex.operation
    ex_mem.control_signals = id_ex.control_signals.copy()
    ex_mem.return_addr = return_addr
    ex_mem.valid = True
    
    # Calculate branch target
    if id_ex.control_signals['Branch']:
        branch_target = id_ex.pc + id_ex.imm

def Memory():
    global ex_mem, mem_wb, d_mem
    
    if not ex_mem.valid:
        mem_wb.valid = False
        return
    
    mem_data = None
    if ex_mem.operation == "lw":
        addr = ex_mem.alu_result
        if 0 <= addr < len(d_mem)*4:
            mem_data = d_mem[addr//4]
    elif ex_mem.operation == "sw":
        addr = ex_mem.alu_result
        if 0 <= addr < len(d_mem)*4:
            d_mem[addr//4] = ex_mem.rs2_val
    
    # Set up MEM/WB pipeline register
    mem_wb.pc = ex_mem.pc
    mem_wb.alu_result = ex_mem.alu_result
    mem_wb.mem_data = mem_data
    mem_wb.rd_reg = ex_mem.rd_reg
    mem_wb.control_signals['RegWrite'] = ex_mem.control_signals['RegWrite']
    mem_wb.control_signals['MemtoReg'] = ex_mem.control_signals['MemtoReg']
    mem_wb.valid = True

def WriteBack():
    global mem_wb, rf
    
    if not mem_wb.valid:
        return
    
    if mem_wb.rd_reg is not None and mem_wb.control_signals['RegWrite']:
        if mem_wb.control_signals['MemtoReg']:
            rf[mem_wb.rd_reg] = mem_wb.mem_data
        else:
            rf[mem_wb.rd_reg] = mem_wb.alu_result

def ControlUnit(opcode, op_name):
    control_signals = {
        'RegWrite': 0, 'Branch': 0, 'MemRead': 0, 'MemWrite': 0,
        'MemtoReg': 0, 'ALUSrc': 0, 'ALUOp': '00', 'JAL': 0, 'JALR': 0
    }

    if op_name in ['add', 'sub', 'and', 'or', 'slt', 'sltu']:
        control_signals['RegWrite'] = 1
    elif op_name in ['addi', 'andi', 'ori', 'slti', 'sltiu']:
        control_signals.update({'RegWrite': 1, 'ALUSrc': 1})
    elif op_name == 'lw':
        control_signals.update({'RegWrite': 1, 'MemRead': 1, 'MemtoReg': 1, 'ALUSrc': 1})
    elif op_name == 'sw':
        control_signals.update({'MemWrite': 1, 'ALUSrc': 1})
    elif op_name == 'beq':
        control_signals['Branch'] = 1
    elif op_name == 'jal':
        control_signals.update({'JAL': 1, 'RegWrite': 1})
    elif op_name == 'jalr':
        control_signals.update({'JALR': 1, 'RegWrite': 1})
    
    return control_signals
def run_cpu(filename):
    global pc, total_clock_cycles
    
    with open(filename) as f:
        instructions = [line.strip() for line in f if line.strip()]
    
    pc = 0
    total_clock_cycles = 0  # Internal counter starts at 0
    max_cycles = 20
    
    # Initialize pipeline with bubbles
    if_id = IF_ID()
    id_ex = ID_EX()
    ex_mem = EX_MEM()
    mem_wb = MEM_WB()
    
    while total_clock_cycles < max_cycles:
        # Prints
        print(f"total_clock_cycles {total_clock_cycles + 1}:")  
        
        
        WriteBack()
        Memory()
        Execute()
        Decode()
        Fetch(instructions)
        
        
        if total_clock_cycles >= 4:
            if mem_wb.valid and mem_wb.rd_reg is not None and mem_wb.control_signals['RegWrite']:
                reg_name = register_abi_reverse_map.get(mem_wb.rd_reg, f"x{mem_wb.rd_reg}")
                print(f"{reg_name} is modified to 0x{rf[mem_wb.rd_reg]:X}")
            
            if ex_mem.valid and ex_mem.control_signals['MemWrite']:
                print(f"memory 0x{ex_mem.alu_result:X} is modified to 0x{ex_mem.rs2_val:X}")
        
        print(f"pc is modified to 0x{pc:X}")
        
        total_clock_cycles += 1
        
        #Checks to stop program
        if (pc // 4 >= len(instructions) and 
            not if_id.valid and not id_ex.valid and 
            not ex_mem.valid and not mem_wb.valid):
            print("program terminated:")
            print(f"total execution time is {total_clock_cycles} cycles")
            break

if __name__ == "__main__":
    filename = input("Enter the program file name to run:\n")
    run_cpu(filename)