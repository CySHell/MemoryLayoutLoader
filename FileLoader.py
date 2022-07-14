import binaryninja as bn
from . import Config


def is_bv_valid_for_plugin(bv: bn.binaryview) -> bool:
    if bv.arch == bn.Architecture['x86'] or bv.arch == bn.Architecture['x86_64']:
        return True
    print(f'{Config.PluginName}: Detected non x86 main BinaryView - Unsupported.')
    return False


def is_interval_overlapping(interval1_start, interval1_end, interval2_start, interval2_end) -> bool:
    return max(interval1_start, interval2_start) <= min(interval1_end, interval2_end)


def is_memory_overlapping(bv: bn.BinaryView, input_bv: bn.BinaryView) -> bool:
    for input_seg in input_bv.segments:
        for seg in bv.segments:
            if is_interval_overlapping(seg.start, seg.end, input_seg.start, input_seg.end):
                return True
    return False


def load_single_file(bv: bn.BinaryView):
    input_file_path = bn.interaction.get_open_filename_input("Choose a File to load into memory space", "")
    base = bn.interaction.get_int_input("Base address of file in memory space", "")

    try:
        input_bv = bn.open_view(input_file_path).rebase(base, force=True)
        raw_file_name = input_bv.file.filename.split("/")[-1]
        print(f"Successfully opened {raw_file_name}, continue with loading process...")
    except Exception as e:
        print(f"Unable to load file , exception: \n{e}")
        return

    if is_memory_overlapping(bv, input_bv):
        print(f"Unable to load file, Base address for input file overlaps with current memory layout.")
        return

    input_bv_raw_base_file_offset = bv.file.raw.end
    offset = 0
    while offset < input_bv.file.raw.end:
        null = bv.file.raw.write(input_bv_raw_base_file_offset + offset, input_bv.file.raw.read(offset, 8))
        offset += 8

    for seg in input_bv.segments:
        flags = 0
        if seg.writable:
            flags += 2
        if seg.executable:
            flags += 1
        if seg.readable:
            flags += 4

        seg_raw_offset = input_bv_raw_base_file_offset + seg.data_offset
        bv.add_user_segment(seg.start, seg.end - seg.start, seg_raw_offset, seg.data_length, flags)

    for sect_name, sect in input_bv.sections.items():
        absolute_section_length = sect.end - sect.start
        bv.add_user_section(f"{raw_file_name}_{sect.name}", sect.start, absolute_section_length, sect.semantics,
                            sect.type,
                            sect.align, sect.entry_size, sect.linked_section, sect.info_section, sect.info_data)

    for func in input_bv.functions:
        bv.add_function(func.start)

    for data_var_addr, data_var in input_bv.data_vars.items():
        if data_var.name:
            data_var_name = f"{raw_file_name}_{data_var.name}"
        else:
            data_var_name = None
        bv.define_data_var(data_var_addr, data_var.type, data_var_name)

    for symb_name, symb in input_bv.symbols.items():
        fixed_symb = bn.Symbol(symb[0].type, symb[0].address, symb_name, symb_name)
        bv.define_user_symbol(fixed_symb)

    print(f"Successfully added {raw_file_name} to the memory space!")
