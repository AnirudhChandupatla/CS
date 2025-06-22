import re

# --- SimpleRisc ISA Definitions (Simplified for this example) ---

# Opcodes (from SimpleRisc Table 3.10) - 5 bits
OPCODES = {
    'add': '00000', 'sub': '00001', 'mul': '00010', 'div': '00011', 'mod': '00100',
    'cmp': '00101', 'and': '00110', 'or': '00111', 'not': '01000', 'mov': '01001',
    'addu': '00000', 'subu': '00001', 'mulu': '00010', 'divu': '00011', 'modu': '00100',
    'cmpu': '00101', 'andu': '00110', 'oru': '00111', 'notu': '01000', 'movu': '01001',
    'addh': '00000', 'subh': '00001', 'mulh': '00010', 'divh': '00011', 'modh': '00100',
    'cmph': '00101', 'andh': '00110', 'orh': '00111', 'noth': '01000', 'movh': '01001',
    'lsl': '01010', 'lsr': '01011', 'asr': '01100', 'nop': '01101', 'ld': '01110',
    'st': '01111', 'beq': '10000', 'bgt': '10001', 'b': '10010', 'call': '10011',
    'ret': '10100',
}

MODIFIER_OPCODES = set ([
    'addu', 'subu', 'mulu', 'divu', 'modu',
    'cmpu', 'andu', 'oru', 'notu', 'movu',
    'addh', 'subh', 'mulh', 'divh', 'modh',
    'cmph', 'andh', 'orh', 'noth', 'movh',
])

# Register mapping (4 bits)
REGISTERS = {
    'r0': '0000', 'r1': '0001', 'r2': '0010', 'r3': '0011',
    'r4': '0100', 'r5': '0101', 'r6': '0110', 'r7': '0111',
    'r8': '1000', 'r9': '1001', 'r10': '1010', 'r11': '1011',
    'r12': '1100', 'r13': '1101', 'r14': '1110', 'sp': '1110', # r14 is sp
    'r15': '1111', 'ra': '1111', # r15 is ra
}

# Instruction Formats (simplified representation for this assembler)
# 'branch': op | offset (27)
# 'immediate': op | I=1 | rd (4) | rs1 (4) | imm (18)
# 'register': op | I=0 | rd (4) | rs1 (4) | rs2 (4) | unused (14) - Simplification: use 14 zeros for unused
# Special cases:
#   cmp: immediate/register format, rd field is ignored (set to 0000)
#   mov reg, imm: immediate format, rs1 field is ignored (set to 0000)
#   mov reg, reg: register format, rs1 and unused fields are ignored
#   ld/st: use immediate format: op | I=1 | rd (4) | rs1 (4) (base reg) | imm (18) (offset)

# --- Helper Functions ---

def to_binary(value, bits, signed=False):
    """Converts an integer to a binary string of specified bit length."""
    if signed:
        # Handle two's complement for negative numbers
        if value < 0:
            value = (1 << bits) + value
        return bin(value)[2:].zfill(bits)
    else:
        return bin(value)[2:].zfill(bits)

def parse_line(line):
    """Parses a single line of assembly code."""
    line = line.strip()
    if not line or line.startswith(';'): # Ignore empty lines and comments
        return None, None, None

    parts = line.split(';', 1) # Split off comments
    instruction_part = parts[0].strip()

    label = None
    if ':' in instruction_part:
        label_part, instruction_part = instruction_part.split(':', 1)
        label = label_part.strip()
        instruction_part = instruction_part.strip()

    if not instruction_part: # Line only contains a label
        return label, None, None

    # Split instruction mnemonic and operands
    match = re.match(r'([a-z]+)\s*(.*)', instruction_part)
    if match:
        mnemonic = match.group(1)
        operands_str = match.group(2).strip()
        operands = [op.strip() for op in operands_str.split(',') if op.strip()]
        return label, mnemonic, operands
    return label, None, None # Should not happen for valid lines

def assemble(assembly_code):
    """
    Performs a two-pass assembly process.
    """
    lines = assembly_code.strip().split('\n')
    processed_lines = []
    for line_num, line in enumerate(lines):
        label, mnemonic, operands = parse_line(line)
        if mnemonic is not None or label is not None:
            processed_lines.append({'line_num': line_num, 'label': label, 'mnemonic': mnemonic, 'operands': operands, 'raw_line': line})

    # --- Pass 1: Build Label Map ---
    label_map = {}
    current_address = 0
    for entry in processed_lines:
        if entry['label']:
            label_map[entry['label']] = current_address
        if entry['mnemonic']: # Only increment address if it's an instruction
            current_address += 1

    print("--- First Pass: Label Map ---")
    for label, addr in label_map.items():
        print(f"Label: {label}, Address: {addr}")
    print("-" * 30)

    # --- Pass 2: Encode Instructions ---
    machine_code = []
    current_address = 0
    for entry in processed_lines:
        mnemonic = entry['mnemonic']
        operands = entry['operands']
        raw_line = entry['raw_line']
        assembled_instruction = None

        if mnemonic:
            opcode = OPCODES.get(mnemonic)
            if not opcode:
                print(f"Error: Unknown mnemonic '{mnemonic}' on line: {raw_line}")
                current_address += 1 # Still increment to keep addresses consistent
                continue

            # Handle Branch/Call/Return (Branch Format)
            if mnemonic in ['beq', 'bgt', 'b', 'call', 'ret']:
                if mnemonic == 'ret': # ret is 0-address, offset field is 27 zeros
                    offset_bin = to_binary(0, 27)
                else: # Branch or Call, needs label resolution
                    target_label = operands[0]
                    if target_label not in label_map:
                        print(f"Error: Undefined label '{target_label}' on line: {raw_line}")
                        current_address += 1
                        continue
                    
                    target_address = label_map[target_label]
                    # PC for offset calculation is (current instruction address + 1)
                    pc_next = current_address + 1
                    offset = target_address - pc_next
                    offset_bin = to_binary(offset, 27, signed=True)
                assembled_instruction = opcode + offset_bin

            # Handle Immediate/Register Format instructions (simplified)
            elif mnemonic in ['cmp', 'sub', 'add', 'mul', 'mov', 'ld', 'st', 'and', 'or', 'not'] or mnemonic in MODIFIER_OPCODES:
                I_bit = '1' # Assume immediate for simplicity if 3rd operand is numeric or for ld/st offset
                rd_bin = '0000' # Default
                rs1_bin = '0000' # Default
                immediate_val = 0
                
                if mnemonic in ['cmp', 'cmpu', 'cmph']: # cmp rd, (reg/imm) -> cmp rs1, rs2/imm. rd is ignored.
                    rs1_bin = REGISTERS.get(operands[0], '0000') # First operand is rs1
                    if len(operands) > 1:
                        if operands[1].isdigit() or (operands[1].startswith('-') and operands[1][1:].isdigit()):
                            I_bit = '1'
                            immediate_val = int(operands[1])
                        else:
                            I_bit = '0' # Register operand
                            rs2_bin = REGISTERS.get(operands[1], '0000')
                            # For register format, the 14 bits after rs2 are unused.
                            assembled_instruction = opcode + I_bit + rd_bin + rs1_bin + rs2_bin + '0' * 14
                            immediate_val = None # Not an immediate instruction
                
                elif mnemonic in ['sub', 'add', 'mul', 'and', 'or', 'subu', 'addu', 'mulu', 'andu', 'oru', 'subh', 'addh', 'mulh', 'andh', 'orh']: # reg, reg, (reg/imm)
                    rd_bin = REGISTERS.get(operands[0], '0000')
                    rs1_bin = REGISTERS.get(operands[1], '0000')
                    if len(operands) > 2:
                        if operands[2].isdigit() or (operands[2].startswith('-') and operands[2][1:].isdigit()):
                            I_bit = '1'
                            immediate_val = int(operands[2])
                        else: # Register as second source operand
                            I_bit = '0'
                            rs2_bin = REGISTERS.get(operands[2], '0000')
                            assembled_instruction = opcode + I_bit + rd_bin + rs1_bin + rs2_bin + '0' * 14
                            immediate_val = None
                
                elif mnemonic in ['mov', 'movu','movh', 'not', 'notu', 'noth']: # mov reg, (reg/imm)
                    rd_bin = REGISTERS.get(operands[0], '0000')
                    if len(operands) > 1:
                        if operands[1].isdigit() or (operands[1].startswith('-') and operands[1][1:].isdigit()):
                            I_bit = '1'
                            immediate_val = int(operands[1])
                        else: # Register operand
                            I_bit = '0'
                            rs2_bin = REGISTERS.get(operands[1], '0000')
                            assembled_instruction = opcode + I_bit + rd_bin + '0000' + rs2_bin + '0' * 14 # rs1 is 0000 for mov reg, reg
                            immediate_val = None

                elif mnemonic in ['ld', 'st']: # ld reg, imm[reg] or st reg, imm[reg]
                    rd_bin = REGISTERS.get(operands[0], '0000') # Destination/Source register for load/store
                    mem_operand = operands[1] # e.g., '4[sp]' or '[sp]'
                    
                    offset_match = re.match(r'(-?\d*)\[(.*?)\]', mem_operand)
                    if offset_match:
                        offset_str = offset_match.group(1)
                        if offset_str:
                            immediate_val = int(offset_str)
                        else:
                            immediate_val = 0 # e.g., '[sp]' means offset 0
                        rs1_name = offset_match.group(2)
                        rs1_bin = REGISTERS.get(rs1_name, '0000')
                        I_bit = '1' # Always immediate format for ld/st offset
                    else:
                        print(f"Error: Invalid memory operand '{mem_operand}' on line: {raw_line}")
                        current_address += 1
                        continue

                # If an immediate value was determined (I_bit='1') and not already assembled (like register format)
                if I_bit == '1' and immediate_val is not None and assembled_instruction is None:
                    imm_bin = to_binary(immediate_val, 16, signed=True) # 16 bits
                    if mnemonic in MODIFIER_OPCODES:
                        if mnemonic[-1] == 'u':
                            imm_field = '01' + imm_bin
                        else:
                            imm_field = '10' + imm_bin                
                    else:
                        imm_field = '00' + imm_bin # 2 modifier bits + 16-bit constant
                        
                    assembled_instruction = opcode + I_bit + rd_bin + rs1_bin + imm_field

            else:
                # Fallback for other instructions if not specifically handled (e.g., nop)
                if mnemonic == 'nop':
                    assembled_instruction = OPCODES['nop'] + '0' * 27 # nop is a branch format with 0 offset
                elif mnemonic == 'ret': # ret handled in branch logic
                    assembled_instruction = OPCODES['ret'] + '0' * 27
                else:
                    print(f"Warning: Instruction '{mnemonic}' not fully implemented in tiny assembler. Skipping: {raw_line}")
                    current_address += 1
                    continue

            if assembled_instruction:
                # Ensure the instruction is exactly 32 bits.
                if len(assembled_instruction) != 32:
                     print(f"Error: Generated instruction length is {len(assembled_instruction)} not 32 for line: {raw_line}")
                     assembled_instruction = '0' * 32 # Placeholder
                machine_code.append((entry['line_num'], raw_line, assembled_instruction))
            current_address += 1
        else: # It was just a label or empty line, no instruction to assemble
            machine_code.append((entry['line_num'], raw_line, None))


    return machine_code

# --- Your SimpleRisc Factorial Assembly Code ---
factorial_assembly = """
b .main
.factorial: cmp r0,1
beq .return
bgt .continue
b .return
.continue: sub sp,sp,2
st r0,[sp]
st ra,1[sp]
sub r0,r0,1
call .factorial
ld r0,[sp]
ld ra,1[sp]
mul r1,r0,r1
add sp,sp,2
ret
.return: mov r1,1
ret
.main: mov r0,10
call .factorial
"""

# --- Assemble and Print ---
assembled_program = assemble(factorial_assembly)

print("\n--- Second Pass: Assembled Machine Code (Binary) ---")
for line_num, original_line, binary_code in assembled_program:
    if binary_code:
        # Format into hex for easier reading
        hex_code = f"0x{int(binary_code, 2):08X}"
        print(f"[{line_num:02d}] {original_line.strip():<30} -> {binary_code} ({hex_code})")
    else:
        print(f"[{line_num:02d}] {original_line.strip():<30} -> (No instruction)")

print('binary codes:')
for _1, _2, binary_code in assembled_program: print(binary_code)

print('hex codes:')
for _1, _2, binary_code in assembled_program: 
    hex_code = f"{int(binary_code, 2):08X}"
    print(hex_code)
