using System;
using System.Collections.Generic;
using System.IO;
using System.Text;
using System.Threading;
using System.Linq;

namespace BlueBirdReaderConsole
{
    public enum LogLevel
    {
        Debug = 0,
        Info = 1,
        Warning = 2,
        Error = 3,
        Critical = 4
    }

    public class LogConfig
    {
        public bool enableConsoleLogging { get; set; }
        public bool enableFileLogging { get; set; }
        public string logLevel { get; set; }
        public string logFilePath { get; set; }
        public long maxLogFileSize { get; set; }
        public int keepLogDays { get; set; }
        public bool includeTimestamp { get; set; }
        public bool includeLogLevel { get; set; }
        public bool includeThreadId { get; set; }
        public string dateFormat { get; set; }
        public bool rotateLogFiles { get; set; }
        public int maxLogFiles { get; set; }
        public bool logTagData { get; set; }
        public bool logStatistics { get; set; }
        public bool logConnectionEvents { get; set; }
        public bool logErrors { get; set; }
        public bool logDebugInfo { get; set; }
    }

    public static class Logger
    {
        private static LogConfig config;
        private static LogLevel currentLevel;
        private static StreamWriter fileWriter;
        private static readonly object lockObject = new object();
        private static Queue<string> logBuffer = new Queue<string>();
        private static Timer flushTimer;
        private static long currentFileSize = 0;
        private static string currentLogFile;
        private static int logFileCounter = 0;

        public static void Initialize(LogConfig logConfig)
        {
            config = logConfig;

            // Parse log level
            if (!Enum.TryParse<LogLevel>(config.logLevel, true, out currentLevel))
            {
                currentLevel = LogLevel.Info;
            }

            // Initialize file logging if enabled
            if (config.enableFileLogging)
            {
                InitializeFileLogging();
            }

            // Set up flush timer for buffered writing
            flushTimer = new Timer(FlushBuffer, null, 1000, 1000);

            // Clean up old log files
            if (config.keepLogDays > 0)
            {
                CleanupOldLogs();
            }
        }

        private static void InitializeFileLogging()
        {
            try
            {
                // Create log directory if it doesn't exist
                string logDir = Path.GetDirectoryName(config.logFilePath);
                if (!string.IsNullOrEmpty(logDir) && !Directory.Exists(logDir))
                {
                    Directory.CreateDirectory(logDir);
                }

                // Generate log file name with timestamp
                string baseFileName = Path.GetFileNameWithoutExtension(config.logFilePath);
                string extension = Path.GetExtension(config.logFilePath);
                string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                currentLogFile = Path.Combine(
                    Path.GetDirectoryName(config.logFilePath) ?? "",
                    $"{baseFileName}_{timestamp}{extension}"
                );

                // Open file for writing
                fileWriter = new StreamWriter(currentLogFile, true, Encoding.UTF8);
                fileWriter.AutoFlush = false;

                // Write header
                fileWriter.WriteLine("====================================================");
                fileWriter.WriteLine($"Log Started: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                fileWriter.WriteLine($"Application: BlueBird RFID Reader Console");
                fileWriter.WriteLine("====================================================");
                fileWriter.Flush();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to initialize file logging: {ex.Message}");
            }
        }

        public static void Debug(string message, params object[] args)
        {
            Log(LogLevel.Debug, message, args);
        }

        public static void Info(string message, params object[] args)
        {
            Log(LogLevel.Info, message, args);
        }

        public static void Warning(string message, params object[] args)
        {
            Log(LogLevel.Warning, message, args);
        }

        public static void Error(string message, params object[] args)
        {
            Log(LogLevel.Error, message, args);
        }

        public static void Critical(string message, params object[] args)
        {
            Log(LogLevel.Critical, message, args);
        }

        public static void LogTag(string epc, int antenna, double rssi, int count)
        {
            if (config != null && config.logTagData)
            {
                string message = $"TAG: EPC={epc}, Antenna={antenna}, RSSI={rssi:F1}, Count={count}";
                Log(LogLevel.Info, message);
            }
        }

        public static void LogStatistics(int total, int unique, double rate)
        {
            if (config != null && config.logStatistics)
            {
                string message = $"STATS: Total={total}, Unique={unique}, Rate={rate:F1} tags/s";
                Log(LogLevel.Info, message);
            }
        }

        public static void LogConnection(string action, string hostname, bool success)
        {
            if (config != null && config.logConnectionEvents)
            {
                string status = success ? "SUCCESS" : "FAILED";
                string message = $"CONNECTION: {action} {hostname} - {status}";
                Log(success ? LogLevel.Info : LogLevel.Error, message);
            }
        }

        private static void Log(LogLevel level, string message, params object[] args)
        {
            if (config == null || level < currentLevel)
                return;

            // Format message
            if (args != null && args.Length > 0)
            {
                try
                {
                    message = string.Format(message, args);
                }
                catch
                {
                    // If formatting fails, just use the original message
                }
            }

            // Build log entry
            StringBuilder logEntry = new StringBuilder();

            if (config.includeTimestamp)
            {
                logEntry.Append($"[{DateTime.Now.ToString(config.dateFormat ?? "yyyy-MM-dd HH:mm:ss.fff")}] ");
            }

            if (config.includeLogLevel)
            {
                logEntry.Append($"[{level,-8}] ");
            }

            if (config.includeThreadId)
            {
                logEntry.Append($"[Thread-{Thread.CurrentThread.ManagedThreadId:D3}] ");
            }

            logEntry.Append(message);
            string fullMessage = logEntry.ToString();

            // Console output
            if (config.enableConsoleLogging)
            {
                lock (lockObject)
                {
                    ConsoleColor originalColor = Console.ForegroundColor;
                    Console.ForegroundColor = GetLogColor(level);
                    Console.WriteLine(fullMessage);
                    Console.ForegroundColor = originalColor;
                }
            }

            // File output
            if (config.enableFileLogging && fileWriter != null)
            {
                lock (lockObject)
                {
                    logBuffer.Enqueue(fullMessage);

                    // Check if we need to rotate the log file
                    currentFileSize += Encoding.UTF8.GetByteCount(fullMessage) + 2; // +2 for newline
                    if (config.maxLogFileSize > 0 && currentFileSize > config.maxLogFileSize)
                    {
                        RotateLogFile();
                    }
                }
            }
        }

        private static ConsoleColor GetLogColor(LogLevel level)
        {
            switch (level)
            {
                case LogLevel.Debug:
                    return ConsoleColor.Gray;
                case LogLevel.Info:
                    return ConsoleColor.White;
                case LogLevel.Warning:
                    return ConsoleColor.Yellow;
                case LogLevel.Error:
                    return ConsoleColor.Red;
                case LogLevel.Critical:
                    return ConsoleColor.Magenta;
                default:
                    return ConsoleColor.White;
            }
        }

        private static void FlushBuffer(object state)
        {
            if (fileWriter == null || logBuffer.Count == 0)
                return;

            lock (lockObject)
            {
                try
                {
                    while (logBuffer.Count > 0)
                    {
                        fileWriter.WriteLine(logBuffer.Dequeue());
                    }
                    fileWriter.Flush();
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error flushing log buffer: {ex.Message}");
                }
            }
        }

        private static void RotateLogFile()
        {
            try
            {
                // Close current file
                fileWriter?.Close();
                fileWriter?.Dispose();

                // Create new log file
                logFileCounter++;
                string baseFileName = Path.GetFileNameWithoutExtension(config.logFilePath);
                string extension = Path.GetExtension(config.logFilePath);
                string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                currentLogFile = Path.Combine(
                    Path.GetDirectoryName(config.logFilePath) ?? "",
                    $"{baseFileName}_{timestamp}_{logFileCounter:D3}{extension}"
                );

                fileWriter = new StreamWriter(currentLogFile, true, Encoding.UTF8);
                currentFileSize = 0;

                // Delete old files if max files exceeded
                if (config.maxLogFiles > 0)
                {
                    CleanupExcessLogFiles();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error rotating log file: {ex.Message}");
            }
        }

        private static void CleanupOldLogs()
        {
            try
            {
                string logDir = Path.GetDirectoryName(config.logFilePath);
                if (string.IsNullOrEmpty(logDir) || !Directory.Exists(logDir))
                    return;

                string baseFileName = Path.GetFileNameWithoutExtension(config.logFilePath);
                string extension = Path.GetExtension(config.logFilePath);
                string searchPattern = $"{baseFileName}_*{extension}";

                DateTime cutoffDate = DateTime.Now.AddDays(-config.keepLogDays);

                foreach (string file in Directory.GetFiles(logDir, searchPattern))
                {
                    FileInfo fileInfo = new FileInfo(file);
                    if (fileInfo.CreationTime < cutoffDate)
                    {
                        try
                        {
                            File.Delete(file);
                            Console.WriteLine($"Deleted old log file: {fileInfo.Name}");
                        }
                        catch
                        {
                            // Ignore deletion errors
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error cleaning up old logs: {ex.Message}");
            }
        }

        private static void CleanupExcessLogFiles()
        {
            try
            {
                string logDir = Path.GetDirectoryName(config.logFilePath);
                if (string.IsNullOrEmpty(logDir) || !Directory.Exists(logDir))
                    return;

                string baseFileName = Path.GetFileNameWithoutExtension(config.logFilePath);
                string extension = Path.GetExtension(config.logFilePath);
                string searchPattern = $"{baseFileName}_*{extension}";

                var files = new DirectoryInfo(logDir)
                    .GetFiles(searchPattern)
                    .OrderBy(f => f.CreationTime)
                    .ToList();

                while (files.Count > config.maxLogFiles)
                {
                    try
                    {
                        files[0].Delete();
                        files.RemoveAt(0);
                    }
                    catch
                    {
                        // Ignore deletion errors
                        break;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error cleaning up excess log files: {ex.Message}");
            }
        }

        public static void ExportCurrentSession(string exportPath)
        {
            try
            {
                // Flush current buffer
                FlushBuffer(null);

                // Copy current log file to export path
                if (File.Exists(currentLogFile))
                {
                    File.Copy(currentLogFile, exportPath, true);
                    Info($"Log exported to: {exportPath}");
                }
            }
            catch (Exception ex)
            {
                Error($"Failed to export log: {ex.Message}");
            }
        }

        public static void Close()
        {
            try
            {
                // Flush remaining buffer
                FlushBuffer(null);

                // Stop timer
                flushTimer?.Dispose();

                // Write footer
                if (fileWriter != null)
                {
                    fileWriter.WriteLine("====================================================");
                    fileWriter.WriteLine($"Log Ended: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                    fileWriter.WriteLine("====================================================");
                    fileWriter.Flush();
                    fileWriter.Close();
                    fileWriter.Dispose();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error closing logger: {ex.Message}");
            }
        }
    }
}