# FR900 SDK Documentation

## Overview

### Introduction
The SDK is a .NET library for controlling Bluebird Fixed RFID readers.

### Requirements
- Microsoft Windows XP or later
- Microsoft Visual Studio 2012 or later
- Microsoft .NET Framework 4.8 or later
- The Microsoft .NET Micro Framework and Compact Framework are not currently supported.

### Getting Start
1. Create a new Visual Studio project
2. Create a new sub-directory under your project called 'lib'
3. Extract the SDK files (.DLL) to the lib directory
4. Add references to these libraries by selecting Project->Add Reference from the Visual Studio menu

## Class List

### AntennaConfig
Class used to define the configuration settings for an individual antenna port.

**Constructor & Destructor:**
- `AntennaConfig()` - Default Constructor
- `AntennaConfig(ushort NewPortNumber)` - Constructor for a new antenna configuration object

**Properties:**
- `bool IsEnabled` - If set to true, the reader will try to inventory tags on that port
- `bool MaxTxPower` - Specifies that the maximum antenna receive sensitivity setting should be used
- `string PortName` - A string that the user can name the antenna port (Example: Door Antenna)
- `ushort PortNumber` - Specifies the antenna port number (starting at port 1) to configure
- `double TxPower` - Defines the antenna transmit power in dBm (e.g. 24.0 dBm)
- `Direction Direction` - Indicate direction of per-antenna (Example: Unknown, In, Out)
- `bool MaxRxSensitivity` - Specifies that the maximum antenna receive sensitivity setting should be used
- `double RxSensitivity` - Defines the antenna receive sensitivity (AKA receive sensitivity filter) in dBm (e.g. -55 dBm)
- `double isAutoDetect` - Defines auto detect antenna port
- `double AutoDetectPower` - Defines the antenna power when isAutoDetect is true

### AntennaStatus
Class containing the status information for an individual antenna port.

**Constructor & Destructor:**
- `AntennaStatus()` - Default Constructor

**Properties:**
- `bool IsConnected` - Indicates whether the antenna port is connected to an antenna
- `ushort PortNumber` - The antenna port number

### FixedReader
The class is a main class for a Bluebird Fixed RFID reader.

**Constructor & Destructor:**
- `FixedReader()` - Create and Initializes a FixedReader object
- `FixedReader(string address, string name)` - Create and Initializes a FixedReader object

**Member Functions:**
- `void AddOpSequence(TagOpSequence seq)` - Adds a sequence of tag operations (read, write, lock, kill) to the reader
- `void Connect()` - Connect to a Fixed RFID reader. The Address property must be set prior to calling this method
- `void Connect(string address)` - Connect to a Fixed RFID reader
- `void Disconnect()` - Close the connection to the reader
- `ReaderCapability GetCapabilities()` - Get the reader for a summary of the capabilities that it supports
- `Settings GetCurrentSettings()` - This function gets the reader for a summary of its current settings
- `Settings GetDefaultSettings()` - This function gets the reader for a summary of its default settings
- `Status GetReaderStatus()` - This function gets the reader for a summary of its default settings
- `void SetCurrentSetting(Settings settings)` - Sets the provided settings to the reader
- `void SetDefaultSetting()` - Sets the default settings to the reader
- `void SetGpo(ushort port, bool state)` - Sets the value of a GPO signal to the specified value
- `void Start()` - Starts the reader. Tag reports will be received asynchronously via an event
- `void Stop()` - Stops the reader. Tags will no longer be read

**Properties:**
- `string Address` - IP address or Hostname of the reader (Read Only)
- `int ConnectTimeout` - The connection timeout in milliseconds
- `bool IsConnected` - Indicates whether or not a connection to reader exists

**Events:**
- `ConnectAsyncCompleteHandler ConnectAsyncComplete` - Event to provide notification of a completed asynchronous connection attempt
- `ConnectionLostHandler ConnectionLost` - Event to provide notification that the TCP/IP connection to the Reader has been lost
- `GpiChangedHandler GpiChanged` - Event to provide notification when a GPI port status changes
- `KeepaliveHandler KeepaliveReceived` - Event to provide notification that a keep alive TCP/IP packet was received from the reader
- `ReaderStartedHandler ReaderStarted` - Event to provide notification when the reader has started
- `ReaderStoppedHandler ReaderStopped` - Event to provide notification when the reader has stopped
- `TagOpCompleteHandler TagOpComplete` - Event to provide notification that a tag operation has completed, including the results of the operation
- `TagReportCallbackHandler TagReportCallback` - Event to provide notification when a tag report is available

### ReaderCapability
Container class used to encapsulate the features supported by a given a fixed reader. An object of this type is returned by a call to `FixedReader.GetCapabilities()`.

**Constructor & Destructor:**
- `ReaderCapability()` - Default Constructor

**Properties:**
- `EnumCommunicationsStandard CommunicationsStandard` - The Regulatory standard supported by the reader
- `string FirmwareVersion` - Firmware version running on Fixed reader
- `ushort GpiCount` - Number of general purpose input (GPI) ports supported by Fixed reader
- `ushort GpoCount` - Number of general purpose output (GPO) ports supported by Fixed reader
- `bool IsHoppingRegion` - Indicates whether frequency hopping supported by the current CommunicationsStandard
- `bool isSupportedBlockErase` - Indicates whether BlockErase supported
- `bool isSupportedBlockPermalock` - Indicates whether BlockPermalock supported
- `bool isSupportedBlockWrite` - Indicates whether BlockWrite supported
- `bool isSupportedXPC` - Indicates whether XPC supported
- `string Manufacturer` - Manufacturer name of the Reader: Bluebird
- `uint MaxAccessSpecNum` - Maximum Number of AccessSpec supported by Fixed reader
- `uint MaxAntennaNum` - Maximum Number of Antenna supported by Fixed reader
- `uint MaxOpSpecNumPerAccessSpec` - Maximum Number of OpSpec supported by Fixed reader
- `uint MaxRoSpecNum` - Maximum Number of RoSpec supported by Fixed reader
- `string ModelName` - Model name of the Fixed Reader: FR900
- `List<ReaderMode> ReaderModes` - A readonly list of reader modes supported by the connected reader
- `List<RxSensitivityTableEntry> RxSensitivities` - Table that correlates a receive sensitivity in dBm to an index in the reader internal receive sensitivity table
- `List<double> TxFrequencies` - Holds the transmit frequencies the reader can hop on
- `List<TxPowerTableEntry> TxPowers` - Table that correlates transmit powers in dBm to an index in the reader internal power table

### Settings
Class for containing all the settings necessary for a reader to begin singulating. It is a composite class consisting of other composite classes containing individual settings, and is consumed by the following methods:
- `FixedReader.GetCurrentSettings`
- `FixedReader.GetDefaultSettings`
- `FixedReader.SetCurrentSettings`
- `FixedReader.SetDefaultSettings`

**Constructor & Destructor:**
- `Settings()` - Default Constructor

**Properties:**
- `AntennaConfigGroup Antennas` - Per-antenna settings: power, sensitivity, etc.
- `AutoStartConfig AutoStart` - The conditions in which a reader will automatically start operation
- `AutoStopConfig AutoStop` - The conditions in which a reader will automatically stop operation
- `FilterSettings Filters` - The settings for defining any tag filters that the reader must use to select a portion of the tag population to participate in singulation
- `GpiConfigGroup Gpis` - Enable general purpose input (GPI) events on specific GPI ports
- `GpoConfigGroup Gpos` - Enable general purpose output (GPO) events on specific GPO ports
- `bool IsDirectionFunc` - Indicate Direction Check Operation
- `KeepaliveConfig Keepalives` - Optionally cause the reader to send a keep-alive message periodically
- `ReaderMode ReaderMode` - The selected reader mode for this configuration
- `ReportConfig Report` - Set how tags are reported and select optional report fields
- `ushort Session` - Session number (0 - 3) to use for the inventory operation for this configuration
- `ushort TagPopulationEstimate` - An estimate of the tag population in view of the RF field of the antenna

### Tag
Class used to contain the details for a specific tag.

**Constructor & Destructor:**
- `Tag()` - Default Constructor

**Properties:**
- `ushort AntennaPortNumber` - The reader antenna port number for the antenna that last saw the tag; requires this option to be enabled in the reader settings report configuration
- `double ChannelInMhz` - The Reader channel, defined in Megahertz, that was being used when the tag was last seen; requires this option to be enabled in the reader settings report configuration
- `ushort Crc` - Contents of the CRC 16-bit word (word 0) in the tag EPC memory bank; requires this option to be enabled in the reader settings report configuration
- `Direction Direction` - Tag Direction. Only use Direction Mode
- `string Epc` - Contents of the tag EPC memory bank
- `BBTimestamp FirstTimeStamp` - The time that the reader first saw the tag; requires this option to be enabled in the reader settings report configuration
- `bool IsAntennaPortNumber` - Does the tag data include antenna port number data?
- `bool IsChannelInMhz` - Does the tag data include channel frequency data?
- `bool IsCrc` - Does the tag data include the EPC CRC data?
- `bool IsFirstTimeStamp` - Does the tag data include the first seen timestamp data?
- `bool IsLastTimeStamp` - Does the tag data include the last seen timestamp data?
- `bool IsPcBits` - Does the tag data include the EPC PC Bits data?
- `bool IsPeakRssi` - Does the tag data include the peak RSSI data?
- `bool IsSeenCount` - Does the tag data include data on the number of times the tag has been seen?
- `BBTimestamp LastTimeStamp` - The time that the reader last saw the tag; requires this option to be enabled in the reader settings report configuration
- `ushort PcBits` - Contents of the PC Bits 16-bit word (word 1) in the tag EPC memory bank; requires this option to be enabled in the reader settings report configuration
- `double PeakRssi` - The maximum RSSI, in dBm, that was seen for this tag; requires this option to be enabled in the reader settings report configuration
- `ushort TagSeenCount` - The number of times the reader has seen this tag; requires this option to be enabled in the reader settings report configuration

### TagReport
Container class used to encapsulate individual tag details returned from the reader.

**Constructor & Destructor:**
- `TagReport()` - Default Constructor

**Properties:**
- `List<Tag> Tags` - A list of tag details

### ReportConfig
Class for configuring the tag inventory reports returned by the reader.

**Constructor & Destructor:**
- `ReportConfig()` - Default Constructor

**Properties:**
- `bool IncludeAntennaPortNumber` - Include Antenna Port Number in the inventory report

## Programmer's Guide

### Library
Required library files:
- `BBFixedReader\Library\Bluebird.FixedReader.dll` (Reference)
- `BBFixedReader\Library\LLRP.dll`
- `BBFixedReader\Library\LLRP.Impinj.dll`

### Basic Operation

#### Tag Inventory
- Sample: `BBFixedReader\TagInventory`

#### Connecting to the Reader

**Connect**
- Sample: `BBFixedReader\FixedReaderSampleApp`

**ConnectAsync**
- Sample: `BBFixedReader\ConnectAsyncSample`

**KeepAlive**
- Sample: `BBFixedReader\KeepAliveSample`

#### Knowing the Reader Capabilities
- Sample: `BBFixedReader\ReaderSettingSample`

#### Configuring the Reader

**Settings**
- Sample: `BBFixedReader\ReaderSettingSample`

**GPI**
- Sample: `BBFixedReader\GpiTriggerSample`

**GPO**
- Sample: `BBFixedReader\GpoSample`

**Antennas**
- Sample: `BBFixedReader\MultiAntennaSample`

**Reader Modes (Link Profile)**
- Sample: `BBFixedReader\SetReaderModeSample`

**PeriodicTrigger**
- Sample: `BBFixedReader\PeriodicTriggerSample`

**Filter**
- Sample: `BBFixedReader\ReaderFilterSample`
- Sample: `BBFixedReader\SoftwareFilterSample`

**Power**
- Sample: `BBFixedReader\RfPowerSample`

**RxSensitivity**
- Sample: `BBFixedReader\RxSensitivitySample`

**Status**
- Sample: `BBFixedReader\ReaderStatusSample`

#### Managing Events
- Sample: `BBFixedReader\ReaderEventSample`

### Access Operation

#### Kill Operation
- Sample: `BBFixedReader\KillTagSample`

#### Lock Operation
- Sample: `BBFixedReader\LockUserMemorySample`

#### Read/Write Operation
- Sample: `BBFixedReader\WriteEpcSample`
- Sample: `BBFixedReader\WriteUserMemorySample`

### Advanced Operations

#### Direction Check
- Sample: `BBFixedReader\DirectionSample`

#### Multi Reader
- Sample: `BBFixedReader\MultiReaderSample`

## Key Points for Implementation

1. **Framework Requirement**: .NET Framework 4.8 or later is required
2. **Main Reference**: `Bluebird.FixedReader.dll` is the primary library
3. **Basic Workflow**:
   - Create `FixedReader` instance
   - Connect to reader using IP address
   - Set callback for tag reports: `reader.TagReportCallback += OnTagsReported`
   - Configure settings using `Settings` class
   - Start inventory with `reader.Start()`
   - Stop inventory with `reader.Stop()`
   - Disconnect with `reader.Disconnect()`

4. **Tag Properties Available**:
   - `tag.Epc` - EPC value
   - `tag.AntennaPortNumber` - Antenna that detected the tag
   - `tag.PeakRssi` - Signal strength
   - `tag.ChannelInMhz` - Frequency channel
   - `tag.TagSeenCount` - Number of times seen

5. **Reader Configuration**:
   - Antenna power settings via `settings.Antennas.GetAntenna(n).TxPower`
   - Report configuration via `settings.Report.IncludeXXX` properties
   - Reader modes for different performance profiles
   - Session and tag population settings