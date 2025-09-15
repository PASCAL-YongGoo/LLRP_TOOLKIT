# Bluebird.FixedReader.dll API Reference

## Overview
The Bluebird.FixedReader.dll provides a high-level C# API for controlling Bluebird FR900 RFID readers using the LLRP protocol. This document describes all classes, methods, properties, and events available in the library.

## Table of Contents
- [Core Classes](#core-classes)
- [Event Handlers](#event-handlers)
- [Settings Configuration](#settings-configuration)
- [Tag Operations](#tag-operations)
- [Data Types](#data-types)
- [Enumerations](#enumerations)
- [Usage Examples](#usage-examples)

## Core Classes

### FixedReader Class
The main class for RFID reader operations.

#### Constructors
```csharp
FixedReader()                           // Default constructor
FixedReader(string hostname, string name) // Constructor with hostname and name
```

#### Connection Methods
| Method | Description |
|--------|-------------|
| `void Connect(string hostname)` | Synchronously connect to reader |
| `void ConnectAsync(string hostname)` | Asynchronously connect to reader |
| `void Disconnect()` | Disconnect from reader |

#### Properties
| Property | Type | Description |
|----------|------|-------------|
| `Address` | string | Reader IP address or hostname |
| `Name` | string | User-defined reader name |

#### Core Operations
| Method | Description |
|--------|-------------|
| `void Start()` | Start tag inventory operation |
| `void Stop()` | Stop tag inventory operation |
| `void SetDefaultSettings()` | Apply default configuration |
| `Settings GetDefaultSettings()` | Get default settings object |
| `Settings GetCurrentSettings()` | Get current reader settings |
| `void SetCurrentSettings(Settings settings)` | Apply new settings to reader |

#### Reader Information
| Method | Return Type | Description |
|--------|-------------|-------------|
| `GetCapabilities()` | ReaderCapability | Get reader hardware capabilities |
| `GetReaderStatus()` | Status | Get current reader status |

#### Tag Operations
| Method | Description |
|--------|-------------|
| `void AddOpSequence(TagOpSequence sequence)` | Add tag operation sequence (read/write/kill) |

#### GPIO Operations
| Method | Description |
|--------|-------------|
| `void SetGpo(ushort portNumber, bool state)` | Set General Purpose Output state |

## Event Handlers

### Tag Reporting Events
```csharp
// Primary tag reporting callback
event TagReportCallback TagReportCallback;
delegate void TagReportCallback(FixedReader sender, TagReport report);

// Tag operation completion
event TagOpCompleteCallback TagOpComplete;
delegate void TagOpCompleteCallback(FixedReader reader, TagOpReport report);
```

### Connection Events
```csharp
// Async connection completion
event ConnectAsyncCompleteCallback ConnectAsyncComplete;
delegate void ConnectAsyncCompleteCallback(FixedReader reader, 
    ConnectAsyncResult result, string errorMessage);

// Connection monitoring
event KeepaliveReceivedCallback KeepaliveReceived;
delegate void KeepaliveReceivedCallback(FixedReader reader);

event ConnectionLostCallback ConnectionLost;
delegate void ConnectionLostCallback(FixedReader reader);
```

### Reader State Events
```csharp
// Reader started/stopped events
event ReaderStartedCallback ReaderStarted;
delegate void ReaderStartedCallback(FixedReader reader, ReaderStartedEvent e);

event ReaderStoppedCallback ReaderStopped;
delegate void ReaderStoppedCallback(FixedReader reader, ReaderStoppedEvent e);
```

### Hardware Events
```csharp
// GPIO input changed
event GpiChangedCallback GpiChanged;
delegate void GpiChangedCallback(FixedReader sender, GpiEvent e);

// Antenna status changed
event AntennaChangedCallback AntennaChanged;
delegate void AntennaChangedCallback(FixedReader sender, AntennaEvent e);
```

## Settings Configuration

### Settings Class
Main configuration container for reader settings.

```csharp
class Settings
{
    // Reader performance mode
    ReaderMode ReaderMode { get; set; }
    
    // Session number (0-3)
    ushort Session { get; set; }
    
    // Search mode (SingleTarget/DualTarget)
    SearchMode SearchMode { get; set; }
    
    // Estimated tag population
    ushort TagPopulationEstimate { get; set; }
    
    // Enable direction detection
    bool IsDirectionFunc { get; set; }
    
    // Sub-settings
    AntennaSettings Antennas { get; }
    ReportSettings Report { get; }
    FilterSettings Filters { get; }
    GpiSettings Gpis { get; }
    AutoStartSettings AutoStart { get; }
    AutoStopSettings AutoStop { get; }
    KeepaliveSettings Keepalives { get; }
}
```

### AntennaSettings Class
Configure individual antenna properties.

```csharp
class AntennaSettings
{
    void EnableAll()              // Enable all antennas
    void DisableAll()             // Disable all antennas
    AntennaConfig GetAntenna(int antennaNumber) // Get specific antenna config
    
    double RxSensitivity { get; set; }    // Global receive sensitivity (dBm)
    bool MaxRxSensitivity { get; set; }   // Use maximum sensitivity
}

class AntennaConfig
{
    bool IsEnabled { get; set; }          // Enable/disable antenna
    double TxPower { get; set; }          // Transmit power (dBm)
    bool MaxTxPower { get; set; }         // Use maximum power
    Direction Direction { get; set; }      // Direction for direction feature
    string PortName { get; set; }         // Antenna port name (optional)
}
```

### ReportSettings Class
Configure tag report format and timing.

```csharp
class ReportSettings
{
    ReportMode Mode { get; set; }         // Report trigger mode
    ushort N { get; set; }                // N value for UponNtag mode
    
    // Fields to include in tag reports
    bool IncludeAntennaPortNumber { get; set; }
    bool IncludePcBits { get; set; }
    bool IncludePeakRssi { get; set; }
    bool IncludeFirstSeenTime { get; set; }
    bool IncludeLastSeenTime { get; set; }
    bool IncludeSeenCount { get; set; }
}
```

### FilterSettings Class
Configure tag filtering.

```csharp
class FilterSettings
{
    TagFilterMode Mode { get; set; }      // Filter mode
    TagFilterConfig TagFilter { get; }    // Filter configuration
}

class TagFilterConfig
{
    MemoryBank MemoryBank { get; set; }   // Memory bank to filter
    ushort BitPointer { get; set; }       // Starting bit position
    string TagMask { get; set; }          // Filter mask (hex string)
    ushort BitCount { get; set; }         // Number of bits to match
}
```

### GpiSettings Class
Configure General Purpose Inputs.

```csharp
class GpiSettings
{
    GpiConfig GetGpi(int gpiNumber)       // Get specific GPI config
}

class GpiConfig
{
    bool IsEnabled { get; set; }          // Enable/disable GPI
    ushort DebounceInMs { get; set; }     // Debounce time in milliseconds
}
```

### AutoStart/AutoStop Settings
Configure automatic start/stop triggers.

```csharp
class AutoStartSettings
{
    AutoStartMode Mode { get; set; }      // Trigger mode
    ushort GpiPortNumber { get; set; }    // GPI port for GpiTrigger mode
    bool GpiLevel { get; set; }           // GPI level for trigger
    uint PeriodInMs { get; set; }         // Period for Periodic mode
}

class AutoStopSettings
{
    AutoStopMode Mode { get; set; }       // Stop mode
    ushort GpiPortNumber { get; set; }    // GPI port for GpiTrigger mode
    bool GpiLevel { get; set; }           // GPI level for trigger
    uint DurationInMs { get; set; }       // Duration for Duration mode
}
```

### KeepaliveSettings Class
Configure connection keepalive.

```csharp
class KeepaliveSettings
{
    bool Enabled { get; set; }            // Enable keepalive
    uint PeriodInMs { get; set; }         // Keepalive period
}
```

## Tag Operations

### TagOpSequence Class
Container for tag operations.

```csharp
class TagOpSequence
{
    TargetTag TargetTag { get; set; }     // Target tag specification
    List<TagOp> Ops { get; }              // List of operations
    bool BlockWriteEnabled { get; set; }  // Enable block write
    int BlockWriteWordCount { get; set; } // Words per block
}
```

### TargetTag Class
Specify target tag for operations.

```csharp
class TargetTag
{
    MemoryBank MemoryBank { get; set; }   // Memory bank
    ushort BitPointer { get; set; }       // Starting bit
    string Data { get; set; }             // Match data (null = any tag)
}
```

### Tag Operation Classes

#### TagReadOp
```csharp
class TagReadOp : TagOp
{
    ushort Id { get; set; }               // Operation ID
    MemoryBank MemoryBank { get; set; }   // Memory bank to read
    ushort WordPointer { get; set; }      // Starting word
    ushort WordCount { get; set; }        // Number of words
}
```

#### TagWriteOp
```csharp
class TagWriteOp : TagOp
{
    ushort Id { get; set; }               // Operation ID
    MemoryBank MemoryBank { get; set; }   // Memory bank to write
    ushort WordPointer { get; set; }      // Starting word
    string Data { get; set; }             // Data to write (hex string)
    string AccessPassword { get; set; }   // Access password (null if none)
}
```

#### TagKillOp
```csharp
class TagKillOp : TagOp
{
    string KillPassword { get; set; }     // Kill password (hex string)
}
```

#### TagLockOp
```csharp
class TagLockOp : TagOp
{
    string AccessPassword { get; set; }           // Access password
    TagLockState AccessPasswordLockType { get; set; } // Lock state for access password
    TagLockState KillPasswordLockType { get; set; }   // Lock state for kill password
    TagLockState EpcLockType { get; set; }           // Lock state for EPC memory
    TagLockState TidLockType { get; set; }           // Lock state for TID memory
    TagLockState UserLockType { get; set; }          // Lock state for User memory
}
```

### Tag Operation Results

#### TagReadOpResult
```csharp
class TagReadOpResult : TagOpResult
{
    ushort OpId { get; }                  // Operation ID
    Tag Tag { get; }                      // Tag that was read
    ReadResultStatus Result { get; }      // Operation result
    string Data { get; }                  // Read data (hex string)
}
```

#### TagWriteOpResult
```csharp
class TagWriteOpResult : TagOpResult
{
    ushort OpId { get; }                  // Operation ID
    Tag Tag { get; }                      // Tag that was written
    WriteResultStatus Result { get; }     // Operation result
    ushort NumWordsWritten { get; }       // Words successfully written
}
```

#### TagKillOpResult
```csharp
class TagKillOpResult : TagOpResult
{
    Tag Tag { get; }                      // Tag that was killed
    KillResultStatus Result { get; }      // Operation result
}
```

#### TagLockOpResult
```csharp
class TagLockOpResult : TagOpResult
{
    Tag Tag { get; }                      // Tag that was locked
    LockResultStatus Result { get; }      // Operation result
}
```

#### TagOpReport
```csharp
class TagOpReport
{
    TagReadOpResult[] ReadResults { get; }
    TagWriteOpResult[] WriteResults { get; }
    TagKillOpResult[] KillResults { get; }
    TagLockOpResult[] LockResults { get; }
}

## Data Types

### Tag Class
Represents a single RFID tag.

```csharp
class Tag
{
    string Epc { get; }                   // EPC data (hex string)
    ushort AntennaPortNumber { get; }     // Antenna that read the tag
    ushort PcBits { get; }                // Protocol Control bits
    double PeakRssi { get; }              // Peak RSSI value (dBm)
    DateTime FirstTimeStamp { get; }      // First seen timestamp
    DateTime LastTimeStamp { get; }       // Last seen timestamp
    ushort TagSeenCount { get; }          // Number of times seen
    Direction Direction { get; }          // Direction (In/Out)
}
```

### TagReport Class
Container for multiple tags.

```csharp
class TagReport : IEnumerable<Tag>
{
    Tag[] Tags { get; }                   // Array of tags
    // Implements IEnumerable<Tag> for foreach loops
}
```

### ReaderCapability Class
Reader hardware capabilities.

```csharp
class ReaderCapability
{
    string ModelName { get; }              // Reader model
    string FirmwareVersion { get; }       // Firmware version
    ushort MaxAntennaNum { get; }         // Maximum antennas
    TxPowerTableEntry[] TxPowers { get; } // Available transmit power levels
    RxSensitivityTableEntry[] RxSensitivities { get; } // Available receive sensitivities
}

class TxPowerTableEntry
{
    double Dbm { get; }                   // Power in dBm
}

class RxSensitivityTableEntry
{
    double Dbm { get; }                   // Sensitivity in dBm
}
```

### Status Class
Current reader status.

```csharp
class Status
{
    bool IsConnected { get; }             // Connection status
    bool IsSingulating { get; }           // Inventory status
    AntennaStatus[] Antennas { get; }     // Antenna status array
    GpiStatus[] Gpis { get; }             // GPI status array
}

class AntennaStatus
{
    ushort PortNumber { get; }            // Antenna port number
    bool IsConnected { get; }             // Antenna connection status
}

class GpiStatus
{
    ushort PortNumber { get; }            // GPI port number
    bool State { get; }                   // Current GPI state
}
```

### Event Data Classes

#### GpiEvent
```csharp
class GpiEvent
{
    ushort PortNumber { get; }            // GPI port number
    bool State { get; }                   // Current state
}
```

#### AntennaEvent
```csharp
class AntennaEvent
{
    ushort PortNumber { get; }            // Antenna port number
    AntennaEventType State { get; }       // Event type
}

class ReaderStartedEvent
{
    // Event data when reader starts
}

class ReaderStoppedEvent
{
    // Event data when reader stops
}
```

## Enumerations

### ReaderMode
Performance modes for different environments.

```csharp
enum ReaderMode
{
    Mode1,    // MaxThroughput
    Mode2,    // Hybrid
    Mode3,    // DenseReaderM4
    Mode4,    // DenseReaderM8
    // Custom modes can be set using: (ReaderMode)1002
}
```

### SearchMode
Tag search modes.

```csharp
enum SearchMode
{
    SingleTarget,  // Single target inventory
    DualTarget     // Dual target inventory
}
```

### MemoryBank
Tag memory banks.

```csharp
enum MemoryBank
{
    Reserved = 0,  // Reserved memory (passwords)
    Epc = 1,       // EPC memory
    Tid = 2,       // TID memory
    User = 3       // User memory
}
```

### Direction
Direction detection values.

```csharp
enum Direction
{
    In,            // Moving towards reader
    Out            // Moving away from reader
}
```

### ReportMode
Tag report timing modes.

```csharp
enum ReportMode
{
    UponNtag       // Report after N tags
    // Additional modes available
}
```

### TagFilterMode
Filter application modes.

```csharp
enum TagFilterMode
{
    OnlyFilter1    // Use only filter 1
    // Additional modes available
}
```

### AutoStartMode
Automatic start triggers.

```csharp
enum AutoStartMode
{
    Immediate,     // Start immediately
    Periodic,      // Start periodically
    GpiTrigger     // Start on GPI trigger
}
```

### AutoStopMode
Automatic stop triggers.

```csharp
enum AutoStopMode
{
    None,          // No auto-stop
    Duration,      // Stop after duration
    GpiTrigger     // Stop on GPI trigger
}
```

### Result Status Enumerations

```csharp
enum ConnectAsyncResult
{
    Success        // Connection successful
    // Additional error codes
}

enum ReadResultStatus
{
    Success        // Read successful
    // Additional error codes
}

enum WriteResultStatus
{
    Success        // Write successful
    // Additional error codes
}

enum KillResultStatus
{
    Success        // Kill successful
    // Additional error codes
}

enum LockResultStatus
{
    Success        // Lock successful
    // Additional error codes
}

enum TagLockState
{
    Unlock,        // Unlock memory
    Lock,          // Lock memory
    PermaLock,     // Permanently lock (irreversible)
    PermaUnlock    // Permanently unlock (irreversible)
}

enum AntennaEventType
{
    Disconnected,  // Antenna disconnected
    Connected      // Antenna connected
```

## Helper Classes

### BitPointers Class
Common bit pointer constants.

```csharp
static class BitPointers
{
    const ushort Epc = 32;         // Start of EPC data
    // Additional constants
}
```

### WordPointers Class
Common word pointer constants.

```csharp
static class WordPointers
{
    const ushort PcBits = 1;       // PC bits location
    const ushort Epc = 2;          // EPC start location
    const ushort KillPassword = 0; // Kill password in Reserved
    const ushort AccessPassword = 2; // Access password in Reserved
    // Additional constants
}
```

### PcBits Class
PC bits manipulation utilities.

```csharp
static class PcBits
{
    static ushort AdjustPcBits(ushort currentPcBits, ushort newEpcLenWords)
    // Adjust PC bits for new EPC length
}
```

### TagData Class
Data conversion utilities.

```csharp
static class TagData
{
    static string FromHexString(string hexString)
    // Convert hex string to tag data format
}
```

## Usage Examples

### Basic Tag Inventory
```csharp
// Create and connect to reader
FixedReader reader = new FixedReader();
reader.Connect("192.168.1.100");

// Set up tag reporting
reader.TagReportCallback += (sender, report) =>
{
    foreach (Tag tag in report.Tags)
    {
        Console.WriteLine($"EPC: {tag.Epc}, RSSI: {tag.PeakRssi}");
    }
};

// Apply default settings and start
reader.SetDefaultSettings();
reader.Start();

// Wait for tags...
Thread.Sleep(5000);

// Stop and disconnect
reader.Stop();
reader.Disconnect();
```

### Advanced Configuration
```csharp
// Get default settings as baseline
Settings settings = reader.GetDefaultSettings();

// Configure reader mode and session
settings.ReaderMode = ReaderMode.Mode1;
settings.Session = 1;
settings.SearchMode = SearchMode.DualTarget;

// Configure antennas
settings.Antennas.DisableAll();
settings.Antennas.GetAntenna(1).IsEnabled = true;
settings.Antennas.GetAntenna(1).TxPower = 30.0;  // 30 dBm

// Configure reporting
settings.Report.Mode = ReportMode.UponNtag;
settings.Report.N = 10;  // Report every 10 tags
settings.Report.IncludeAntennaPortNumber = true;
settings.Report.IncludePeakRssi = true;
settings.Report.IncludeFirstSeenTime = true;

// Apply settings
reader.SetCurrentSettings(settings);
```

### Tag Filtering
```csharp
Settings settings = reader.GetDefaultSettings();

// Filter for specific EPC prefix
settings.Filters.Mode = TagFilterMode.OnlyFilter1;
settings.Filters.TagFilter.MemoryBank = MemoryBank.Epc;
settings.Filters.TagFilter.BitPointer = BitPointers.Epc;
settings.Filters.TagFilter.TagMask = "3005";  // Match tags starting with 3005
settings.Filters.TagFilter.BitCount = 16;  // Match 16 bits

reader.SetCurrentSettings(settings);
```

### Writing EPC
```csharp
// Create operation sequence
TagOpSequence sequence = new TagOpSequence();

// Target specific tag
sequence.TargetTag.MemoryBank = MemoryBank.Epc;
sequence.TargetTag.BitPointer = BitPointers.Epc;
sequence.TargetTag.Data = "300567890ABCDEF012345678";  // Current EPC

// Create write operation
TagWriteOp writeOp = new TagWriteOp();
writeOp.Id = 1;
writeOp.MemoryBank = MemoryBank.Epc;
writeOp.WordPointer = WordPointers.Epc;
writeOp.Data = "300512345678901234567890";  // New EPC
writeOp.AccessPassword = null;  // No password

sequence.Ops.Add(writeOp);

// Set up completion handler
reader.TagOpComplete += (reader, report) =>
{
    foreach (TagWriteOpResult result in report.WriteResults)
    {
        if (result.Result == WriteResultStatus.Success)
        {
            Console.WriteLine($"Successfully wrote {result.NumWordsWritten} words");
        }
    }
};

// Execute operation
reader.AddOpSequence(sequence);
reader.Start();
```

### Reading User Memory
```csharp
TagOpSequence sequence = new TagOpSequence();

// Target any tag (null = any)
sequence.TargetTag.Data = null;

// Read user memory
TagReadOp readOp = new TagReadOp();
readOp.Id = 1;
readOp.MemoryBank = MemoryBank.User;
readOp.WordPointer = 0;
readOp.WordCount = 16;  // Read 16 words

sequence.Ops.Add(readOp);

// Handle results
reader.TagOpComplete += (reader, report) =>
{
    foreach (TagReadOpResult result in report.ReadResults)
    {
        if (result.Result == ReadResultStatus.Success)
        {
            Console.WriteLine($"Tag: {result.Tag.Epc}");
            Console.WriteLine($"Data: {result.Data}");
        }
    }
};

reader.AddOpSequence(sequence);
```

### GPI Trigger
```csharp
Settings settings = reader.GetDefaultSettings();

// Configure GPI 1
settings.Gpis.GetGpi(1).IsEnabled = true;
settings.Gpis.GetGpi(1).DebounceInMs = 50;

// Start on GPI high
settings.AutoStart.Mode = AutoStartMode.GpiTrigger;
settings.AutoStart.GpiPortNumber = 1;
settings.AutoStart.GpiLevel = true;  // High level

// Stop on GPI low
settings.AutoStop.Mode = AutoStopMode.GpiTrigger;
settings.AutoStop.GpiPortNumber = 1;
settings.AutoStop.GpiLevel = false;  // Low level

// Monitor GPI changes
reader.GpiChanged += (sender, e) =>
{
    Console.WriteLine($"GPI {e.PortNumber} changed to {e.State}");
};

reader.SetCurrentSettings(settings);
```

### Multi-Reader Operation
```csharp
// Create multiple reader instances
FixedReader reader1 = new FixedReader("192.168.1.100", "Reader1");
FixedReader reader2 = new FixedReader("192.168.1.101", "Reader2");

// Common event handler
Action<FixedReader, TagReport> tagHandler = (reader, report) =>
{
    foreach (Tag tag in report.Tags)
    {
        Console.WriteLine($"{reader.Name}: {tag.Epc}");
    }
};

// Connect and configure both
reader1.Connect(reader1.Address);
reader1.TagReportCallback += (s, r) => tagHandler(s, r);

reader2.Connect(reader2.Address);
reader2.TagReportCallback += (s, r) => tagHandler(s, r);

// Start both readers
reader1.Start();
reader2.Start();
```

### Connection Monitoring
```csharp
// Enable keepalive
Settings settings = reader.GetDefaultSettings();
settings.Keepalives.Enabled = true;
settings.Keepalives.PeriodInMs = 5000;  // 5 seconds

// Monitor connection
reader.KeepaliveReceived += (reader) =>
{
    Console.WriteLine("Keepalive received");
};

reader.ConnectionLost += (reader) =>
{
    Console.WriteLine("Connection lost!");
    // Attempt reconnection
    reader.Connect(reader.Address);
};

reader.SetCurrentSettings(settings);
```

### Tag Memory Lock Operations
```csharp
// Create lock operation
TagOpSequence sequence = new TagOpSequence();

// Target specific tag
sequence.TargetTag.MemoryBank = MemoryBank.Epc;
sequence.TargetTag.Data = "300567890ABCDEF012345678";

// Create lock operation
TagLockOp lockOp = new TagLockOp();
lockOp.AccessPassword = "00000000";  // Access password
lockOp.UserLockType = TagLockState.Lock;  // Lock user memory
lockOp.EpcLockType = TagLockState.Lock;   // Lock EPC
lockOp.AccessPasswordLockType = TagLockState.PermaLock;  // Permanently lock access password

sequence.Ops.Add(lockOp);

// Handle results
reader.TagOpComplete += (reader, report) =>
{
    foreach (TagLockOpResult result in report.LockResults)
    {
        if (result.Result == LockResultStatus.Success)
        {
            Console.WriteLine($"Successfully locked tag {result.Tag.Epc}");
        }
    }
};

reader.AddOpSequence(sequence);
reader.Start();
```

### Block Write Operations
```csharp
// Enable block write for better performance with Monza chips
TagOpSequence sequence = new TagOpSequence();
sequence.BlockWriteEnabled = true;
sequence.BlockWriteWordCount = 2;  // Write 2 words at a time

// Target any tag
sequence.TargetTag.Data = null;

// Write to user memory
TagWriteOp writeOp = new TagWriteOp();
writeOp.MemoryBank = MemoryBank.User;
writeOp.WordPointer = 0;
writeOp.Data = "1234567890ABCDEF";  // 8 bytes = 4 words

sequence.Ops.Add(writeOp);
reader.AddOpSequence(sequence);
```

### Reader Status Monitoring
```csharp
// Get detailed reader status
Status status = reader.GetReaderStatus();

Console.WriteLine($"Connected: {status.IsConnected}");
Console.WriteLine($"Singulating: {status.IsSingulating}");

// Check antenna status
foreach (AntennaStatus antenna in status.Antennas)
{
    Console.WriteLine($"Antenna {antenna.PortNumber}: {(antenna.IsConnected ? "Connected" : "Disconnected")}");
}

// Check GPI status
foreach (GpiStatus gpi in status.Gpis)
{
    Console.WriteLine($"GPI {gpi.PortNumber}: {(gpi.State ? "High" : "Low")}");
}
```

### Direction Detection
```csharp
// Enable direction detection
Settings settings = reader.GetDefaultSettings();
settings.IsDirectionFunc = true;

// Configure antennas for direction detection
settings.Antennas.GetAntenna(1).Direction = Direction.In;
settings.Antennas.GetAntenna(2).Direction = Direction.Out;

reader.SetCurrentSettings(settings);

// Process tags with direction
reader.TagReportCallback += (sender, report) =>
{
    foreach (Tag tag in report.Tags)
    {
        Console.WriteLine($"EPC: {tag.Epc}, Direction: {tag.Direction}");
    }
};
```

## Error Handling

### Exception Handling
```csharp
try
{
    reader.Connect(hostname);
}
catch (FixedReaderSdkException ex)
{
    Console.WriteLine($"SDK Error: {ex.Message}");
}
catch (Exception ex)
{
    Console.WriteLine($"General Error: {ex.Message}");
}
```

## Notes

1. **Thread Safety**: Event callbacks are called from background threads. Use proper synchronization when updating UI or shared data.

2. **Resource Management**: Always call `Disconnect()` when done to properly release resources.

3. **Custom Modes**: The reader supports custom modes beyond the standard enumeration values by casting uint values to ReaderMode.

4. **Password Operations**: When using access-protected tags, provide passwords as hex strings without spaces or prefixes.

5. **Vendor Extensions**: This library includes Bluebird-specific extensions for the FR900 reader that may not be available on other LLRP-compliant readers.

## Version Information
- **DLL Version**: Based on analysis of Bluebird.FixedReader.dll (52KB)
- **LLRP Version**: LLRP 1.0.1 compliant with vendor extensions
- **Target Framework**: .NET Framework 4.8

## See Also
- [LLRP Specification](https://www.gs1.org/standards/epc-rfid/llrp)
- [Bluebird FR900 Hardware Manual](https://www.bluebirdcorp.com)
- [EPC Tag Data Standard](https://www.gs1.org/standards/rfid/epc-tds)