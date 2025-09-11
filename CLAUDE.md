# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LLRP Toolkit is an implementation of the EPCGlobal Low Level Reader Protocol (LLRP) specification. It provides libraries and tools for communicating with RFID readers using the LLRP protocol. The toolkit includes implementations in multiple languages:

- **libltkc**: C implementation of LLRP
- **libltkcpp**: C++ implementation of LLRP  
- **LTKNet**: .NET implementation of LLRP
- **LTK/Definitions**: XML schema and definition files for the LLRP protocol

## Architecture

The toolkit follows a code generation approach where LLRP message and parameter definitions are specified in XML files conforming to XML schemas, and language-specific code is generated from these definitions:

1. **Core Protocol Definitions**: Located in `LTK/Definitions/Core/`, containing:
   - `llrp-1x0-def.xml`: Binary protocol definitions
   - `llrp-1x0.xsd`: XML Schema for LLRP protocol validation

2. **Language Implementations**:
   - Each language binding (C, C++, .NET) generates code from the XML definitions
   - Generated code provides strongly-typed message and parameter classes
   - Each implementation supports encoding/decoding between binary, object, and XML representations

3. **Extension Support**: Organizations can define custom messages and parameters as vendor extensions that conform to the base schema

## Build Commands

### C Library (libltkc)
```bash
cd libltkc/example
make example1
```

### C++ Library (libltkcpp)
```bash
cd libltkcpp/example
make example1
```

### .NET Library (LTKNet)
Requires .NET Framework 2.0+:
```bash
# From LTKNet directory with Visual Studio tools:
msbuild
msbuild /t:clean
msbuild /t:rebuild
```

**Note**: Before building LTKNet:
1. Copy `llrp-1x0-def.xml` to the LLRP directory
2. For vendor extensions, copy VendorExt.xml to LLRPVendorExt directory

## Key Components

- **Message Classes**: Each LLRP message type has a corresponding class with encode/decode methods
- **Parameter Classes**: LLRP parameters are represented as classes that can be nested
- **Connection Management**: TCP/IP client and server implementations for LLRP communication
- **XML Support**: Messages can be serialized to/from XML for debugging and configuration

## Development Notes

- The C and C++ libraries include precompiled static libraries (.a files on Unix, .lib on Windows)
- Example programs demonstrate basic LLRP operations like connecting to a reader and running inventory operations
- Test data and utilities are available in the LTKNet directory for .NET development