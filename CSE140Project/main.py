#JALR and JAL use array for the pc. based on pc, jump toa ddress based on idndex
# Globals
pc = 0
next_pc = 0
branch_target = 0
alu_zero = 0
total_clock_cycles = 0

# Initialize register file
rf = [0] * 32
#part 1
rf[1] = 0x20
rf[2] = 0x5
rf[10] = 0x70
rf[11] = 0x4


#part 2
# rf[8] = 0x20   # s0
# rf[10] = 0x5    # a0
# rf[11] = 0x2    # a1
# rf[12] = 0xa    # a2
# rf[13] = 0xf    # a3

# # Data memory
d_mem = [0] * 32

#part 1
d_mem[28] = 0x5
d_mem[29] = 0x10


# Control signals
control_signals = {
    'RegWrite': 0, 'Branch': 0, 'MemRead': 0, 'MemWrite': 0,
    'MemtoReg': 0, 'ALUSrc': 0, 'ALUOp': '00', 'JAL': 0, 'JALR': 0
}

# Register ABI mapping
# register_abi_map = {
#     "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4, "t0": 5, "t1": 6, "t2": 7,
#     "s0": 8, "fp": 8, "s1": 9, "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14, "a5": 15,
#     "a6": 16, "a7": 17, "s2": 18, "s3": 19, "s4": 20, "s5": 21, "s6": 22, "s7": 23,
#     "s8": 24, "s9": 25, "s10": 26, "s11": 27, "t3": 28, "t4": 29, "t5": 30, "t6": 31
# }
# register_abi_reverse_map = {v: k for k, v in register_abi_map.items()}

#based on opcode, returns instruction type
def findOp(code):
    opcode = code[25:32]
    if opcode == "0110011": return "R"
    elif opcode in ["0010011", "0000011", "1100111"]: return "I"
    elif opcode == "0100011": return "S"
    elif opcode == "1100011": return "SB"
    elif opcode == "1101111": return "UJ"
    elif opcode == "0110111": return "U"
    return ""

#this finds the operation based on the machine code
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

#this finds the different fields based on the itype
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
    #used AI to debug for intermediate calculations
    if itype == "I":
        fields["funct3"] = code[17:20]
        #immediate is calculated
        fields["imm"] = sign_extend(code[0:12], 12)
        fields["rd"] = code[20:25]
    
    if itype in ["S", "SB"]:
        fields["funct3"] = code[17:20]
        imm = code[0:7] + code[20:25]
        #immediate is calculated
        fields["imm"] = sign_extend(imm, 12)

    if itype == "UJ":  # JAL
       
        imm20 = code[0]        
        imm10_1 = code[1:11]   
        imm11 = code[11]       
        imm19_12 = code[12:20] 
        #adds up to find immediate and shifts left by 1
        imm = (sign_extend(imm20 + imm19_12 + imm11 + imm10_1, 20)) << 1
        fields["imm"] = imm
        fields["rd"] = code[20:25]
            
    return fields

def sign_extend(imm, bits):
    if isinstance(imm, str):
        imm = int(imm, 2)
    #checks if MSB is 1
    if imm & (1 << (bits-1)):
        imm -= 1 << bits
    return imm

def Fetch(instructions):
    global pc, next_pc
    index = pc // 4
    #if end of program, returns none
    if index >= len(instructions):
        return None
    next_pc = pc + 4  
    return instructions[index]


def Decode(instr):
    #find instruction type
    itype = findOp(instr)  
    #find fields
    fields = findI(instr, itype)  
    #get operation name
    operation = findOperation(fields, itype, instr[25:32], instr)  
    
    rd_reg = int(fields["rd"], 2) if "rd" in fields else None
    rs1_reg = int(fields["rs1"], 2) if "rs1" in fields else 0
    rs2_reg = int(fields["rs2"], 2) if "rs2" in fields else 0

    opcode = instr[25:32]
       
    rd_str = f"x{rd_reg}"
    #this is decoded
    return {
        "rs1_val": rf[rs1_reg],
        "rs2_val": rf[rs2_reg],
        
        "rd_reg": rd_reg,
        "rd_reg_str": rd_str,
        "imm": fields.get("imm", 0),
        "operation": operation
    }

def Execute(decoded):
    global pc, alu_zero, branch_target, next_pc
    
    next_pc = pc + 4
    if control_signals["JAL"]:
        return_addr = next_pc
        pc = pc + decoded["imm"]
        return return_addr
        
    if control_signals["JALR"]:
        return_addr = next_pc
        pc = (decoded["rs1_val"] + decoded["imm"]) & ~1
        return return_addr
        
    a = decoded["rs1_val"]
    b = (decoded["imm"]) if control_signals["ALUSrc"] else decoded["rs2_val"]
    result = None
    
 
    if decoded["operation"] in ["add","addi", "lw", "sw"]:
        result = a + b
    elif decoded["operation"] == "sub":
        result = a - b
    elif decoded["operation"] in ["and", "andi"]:
        result = a & b
    elif decoded["operation"] in ["or", "ori"]:
        result = a | b
    elif decoded["operation"] == "beq":
        result = a - b
        alu_zero = int(result == 0)

    if control_signals["Branch"]:
        #compares registers
        result = a - decoded["rs2_val"]
        alu_zero = int(result == 0)
        #finds jump targe
        branch_target = pc + (decoded["imm"])
        if alu_zero:
            pc = branch_target
        else:
            pc = next_pc
    else:
        pc = next_pc
    return result


def Mem(decoded, alu_result):
    if decoded["operation"] == "lw":
        addr = alu_result
        if 0 <= addr < len(d_mem)*4:
            return d_mem[addr//4]
            
    elif decoded["operation"] == "sw":
        addr = alu_result
        if 0 <= addr < len(d_mem)*4:
            d_mem[addr//4] = decoded["rs2_val"]
    
    return None

def WriteBack(decoded, alu_result, mem_data):
    if decoded["rd_reg"] is not None and control_signals["RegWrite"]:
        if control_signals["MemtoReg"]:
            rf[decoded["rd_reg"]] = mem_data
        else:
            rf[decoded["rd_reg"]] = alu_result

def ControlUnit(opcode, op_name):
    control_signals.update({
        'RegWrite': 0, 'Branch': 0, 'MemRead': 0, 'MemWrite': 0,
        'MemtoReg': 0, 'ALUSrc': 0, 'ALUOp': '00', 'JAL': 0, 'JALR': 0
    })

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

def run_cpu(filename):
    global pc, total_clock_cycles
    with open(filename) as f:
        instructions = [line.strip() for line in f if line.strip()]
    
    pc = 0
    total_clock_cycles = 1
    max_cycles = 10  # Safety limit
    
    while pc // 4 < len(instructions) and total_clock_cycles <= max_cycles:
        print(f"total_clock_cycles {total_clock_cycles} :")
        instr = Fetch(instructions)
        if not instr:
            print("program terminated:")
            break
            
        decoded = Decode(instr)
        ControlUnit(instr[25:32], decoded["operation"])
        result = Execute(decoded)
        mem_data = Mem(decoded, result)
        WriteBack(decoded, result, mem_data)
        
        # Print modifications
        if decoded["rd_reg"] is not None and control_signals["RegWrite"]:
            print(f"x{decoded['rd_reg']} is modified to 0x{rf[decoded['rd_reg']]:X}")
        
        if control_signals["MemWrite"]:
            print(f"memory 0x{result:X} is modified to 0x{decoded['rs2_val']:X}")
        
        print(f"pc is modified to 0x{pc:X}")
        total_clock_cycles += 1
        
        if total_clock_cycles > max_cycles:
            print("Maximum cycle limit reached, terminating")
            break


if __name__ == "__main__":
    filename = input("Enter the program file name to run:\n")
    run_cpu(filename)