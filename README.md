# MemoryLayoutLoader

Binary Ninja plugin to load files into the current BinaryViews' memory space.

## Description

The main use case of this plugin is to load Dll's into the BinaryView of the main process image, and thus allowing the creation of cross references of calls from the main image into the correct dll.

## Usage

Open the BinaryView you wish to add the dll into, and then choose the dll raw image and base address of the dll within the memory space when prompted by the plugin.

## License

This plugin is released under an [MIT license](./license).
