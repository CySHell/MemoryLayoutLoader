import time

import binaryninja as bn
from . import Config

test = None


def block_until_analysis_finished(bv: bn.BinaryView):
    print(f"Current Analysis state is {bv.analysis_progress.state}")
    while bv.analysis_progress.state != bn.enums.AnalysisState.IdleState.value and \
            bv.analysis_progress.state != bn.enums.AnalysisState.InitialState.value:
        print(f"Blocking for 3 seconds")
        time.sleep(3)


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


def check_address_alignment(addr: int) -> bool:
    # Check if address is page aligned, PAGE_SIZE is assumed to be 0x1000
    return addr == (addr & ~0xFFFF)


def load_single_file(bv: bn.BinaryView):
    input_file_path = bn.interaction.get_open_filename_input("Choose a File to load into memory space", "")
    base = bn.interaction.get_int_input("Base address of file in memory space, Or \"0\" to add right after bv.end", "")

    try:
        PAGE_SIZE = 0x1000
        SPACE_BETWEEN_VIEWS = PAGE_SIZE * 0x10

        if base:
            if not check_address_alignment(base):
                print(f"Base address provided is NOT page aligned (PAGE_SIZE = 0x1000), please"
                      f"provide an aligned base address, i.e address in the form of 0xXXXXX000")
        else:
            # Set base to end of current view and Align to page boundaries
            base = (bv.end + SPACE_BETWEEN_VIEWS) & ~0xFFFF

        with bn.open_view(input_file_path).rebase(base, force=True) as input_bv:
            input_bv.update_analysis()
            raw_file_name = input_bv.file.filename.split("/")[-1]
            print(f"Successfully opened {raw_file_name}, continue with loading process...")

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

            block_until_analysis_finished(bv)

            for sect_name, sect in input_bv.sections.items():
                absolute_section_length = sect.end - sect.start
                bv.add_user_section(f"{raw_file_name}_{sect.name}", sect.start, absolute_section_length, sect.semantics,
                                    sect.type,
                                    sect.align, sect.entry_size, sect.linked_section, sect.info_section, sect.info_data)

            block_until_analysis_finished(bv)

            # Up until now we needed the raw file information of the loaded file in order for the segments
            # to be correctly defined by Binja.
            # The raw file does not contain correct rebase information for data variables, so now we need to
            # overwrite the incorrect values with the correct values directly from the loaded input_bv.
            end = input_bv.end
            offset = base
            while offset < end:
                null = bv.write(offset, input_bv.read(offset, 8))
                offset += 8

            for func in input_bv.functions:
                bv.add_function(func.start)

            block_until_analysis_finished(bv)

            for symb_name, symb in input_bv.symbols.items():
                fixed_symb = bn.Symbol(symb[0].type, symb[0].address, symb_name, symb_name)
                bv.define_user_symbol(fixed_symb)

            block_until_analysis_finished(bv)

            for data_var_addr, data_var in input_bv.data_vars.items():
                print(f"Defining Data Var {data_var.address}::{data_var.name} of type {data_var.type}")
                if data_var.name:
                    data_var_name = f"{raw_file_name}_{data_var.name}"
                else:
                    data_var_name = None
                bv.define_data_var(data_var_addr, data_var.type, data_var_name)

            print(f"Successfully added {raw_file_name} to the memory space!")

    except Exception as e:
        print(f"Unable to load file , exception: \n{e}")
        return
