import binaryninja as bn
from . import FileLoader
from . import Config

bn.PluginCommand.register(Config.PluginName,
                          "Load a raw file into the current memory space.",
                          FileLoader.load_single_file,
                          FileLoader.is_bv_valid_for_plugin)
