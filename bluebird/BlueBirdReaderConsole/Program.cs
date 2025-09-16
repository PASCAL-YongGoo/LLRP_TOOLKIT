using System;
using System.Collections.Generic;
using System.Threading;
using System.IO;
using System.Web.Script.Serialization;
using System.Linq;
using Bluebird.FixedReader;

namespace BlueBirdReaderConsole
{
    public class RssiStatistics
    {
        private List<double> rssiValues = new List<double>();
        private const int MaxSamples = 50; // 최근 50개 값만 유지

        public void AddValue(double rssi)
        {
            rssiValues.Add(rssi);

            // 최대 샘플 수 초과시 오래된 값 제거
            if (rssiValues.Count > MaxSamples)
            {
                rssiValues.RemoveAt(0);
            }
        }

        // dBm을 mW로 변환
        private double DbmToMw(double dbm) => Math.Pow(10, dbm / 10.0);

        // mW를 dBm으로 변환
        private double MwToDbm(double mw) => 10.0 * Math.Log10(mw);

        // 올바른 dBm 평균 (선형 스케일에서 평균 후 dBm 변환)
        public double Mean
        {
            get
            {
                if (rssiValues.Count == 0) return 0;

                double mwSum = rssiValues.Sum(dbm => DbmToMw(dbm));
                double avgMw = mwSum / rssiValues.Count;
                return MwToDbm(avgMw);
            }
        }

        // 단순 산술평균 (비교용)
        public double ArithmeticMean => rssiValues.Count > 0 ? rssiValues.Average() : 0;

        public double StandardDeviation
        {
            get
            {
                if (rssiValues.Count <= 1) return 0;

                // dBm 값에 대한 표준편차 (로그 스케일이므로 산술적으로 계산)
                double arithmeticMean = ArithmeticMean;
                double variance = rssiValues.Sum(x => Math.Pow(x - arithmeticMean, 2)) / (rssiValues.Count - 1);
                return Math.Sqrt(variance);
            }
        }

        public double Median
        {
            get
            {
                if (rssiValues.Count == 0) return 0;

                var sorted = rssiValues.OrderBy(x => x).ToList();
                int middle = sorted.Count / 2;

                if (sorted.Count % 2 == 0)
                    return (sorted[middle - 1] + sorted[middle]) / 2.0;
                else
                    return sorted[middle];
            }
        }

        public double FilteredMean
        {
            get
            {
                if (rssiValues.Count <= 2) return Mean;

                double arithmeticMean = ArithmeticMean;
                double stdDev = StandardDeviation;

                // 평균 ± 2σ 범위 내의 값만 사용 (dBm 기준으로 필터링)
                var filteredValues = rssiValues
                    .Where(x => Math.Abs(x - arithmeticMean) <= 2 * stdDev)
                    .ToList();

                if (filteredValues.Count == 0) return Mean;

                // 필터링된 값들의 올바른 dBm 평균
                double mwSum = filteredValues.Sum(dbm => DbmToMw(dbm));
                double avgMw = mwSum / filteredValues.Count;
                return MwToDbm(avgMw);
            }
        }

        public double WeightedMean
        {
            get
            {
                if (rssiValues.Count == 0) return 0;

                double weightedMwSum = 0;
                double totalWeight = 0;

                // 최근 값일수록 높은 가중치 (지수적 감소)
                for (int i = 0; i < rssiValues.Count; i++)
                {
                    double weight = Math.Pow(0.9, rssiValues.Count - 1 - i);
                    double mw = DbmToMw(rssiValues[i]);
                    weightedMwSum += mw * weight;
                    totalWeight += weight;
                }

                if (totalWeight == 0) return 0;

                double avgMw = weightedMwSum / totalWeight;
                return MwToDbm(avgMw);
            }
        }

        public int SampleCount => rssiValues.Count;

        public double Min => rssiValues.Count > 0 ? rssiValues.Min() : 0;
        public double Max => rssiValues.Count > 0 ? rssiValues.Max() : 0;

        public double RecentVariability
        {
            get
            {
                if (rssiValues.Count < 10) return 0;

                // 최근 10개 값의 표준편차
                var recent = rssiValues.Skip(Math.Max(0, rssiValues.Count - 10)).ToList();
                if (recent.Count <= 1) return 0;

                double mean = recent.Average();
                double variance = recent.Sum(x => Math.Pow(x - mean, 2)) / (recent.Count - 1);
                return Math.Sqrt(variance);
            }
        }

        public double TrendSlope
        {
            get
            {
                if (rssiValues.Count < 5) return 0;

                // 최근 값들의 선형 추세 계산 (기울기)
                var recent = rssiValues.Skip(Math.Max(0, rssiValues.Count - 10)).ToList();
                int n = recent.Count;

                double sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;
                for (int i = 0; i < n; i++)
                {
                    sumX += i;
                    sumY += recent[i];
                    sumXY += i * recent[i];
                    sumXX += i * i;
                }

                double slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
                return slope;
            }
        }

        public string MovementStatus
        {
            get
            {
                if (rssiValues.Count < 5) return "측정중";

                double stdDev = StandardDeviation;
                double recentVar = RecentVariability;
                double slope = TrendSlope;

                // 움직임 판단 로직
                if (stdDev < 1.0 && recentVar < 0.8)
                {
                    return "정지";
                }
                else if (stdDev > 3.0 || recentVar > 2.5)
                {
                    if (Math.Abs(slope) > 0.3)
                    {
                        return slope > 0 ? "접근중" : "멀어짐";
                    }
                    return "이동중";
                }
                else if (Math.Abs(slope) > 0.5)
                {
                    return slope > 0 ? "접근중" : "멀어짐";
                }
                else
                {
                    return "미약한움직임";
                }
            }
        }

        public string GetStatsSummary()
        {
            if (rssiValues.Count == 0) return "No data";

            return $"Mean:{Mean:F1}(vs{ArithmeticMean:F1}) Median:{Median:F1} Filtered:{FilteredMean:F1} Weighted:{WeightedMean:F1} StdDev:{StandardDeviation:F2} Range:[{Min:F1}~{Max:F1}] n={SampleCount}";
        }

        public string GetMovementSummary()
        {
            if (rssiValues.Count < 5) return "측정중...";

            return $"상태:{MovementStatus} (편차:{StandardDeviation:F1} 추세:{TrendSlope:F2} 최근변동:{RecentVariability:F1})";
        }
    }

    public class ReaderConfig
    {
        public string hostname { get; set; }
        public int inventoryDurationMs { get; set; }
    }

    public class AntennaConfig
    {
        public int portNumber { get; set; }
        public bool isEnabled { get; set; }
        public bool maxTxPower { get; set; }
        public double txPower { get; set; }
    }

    public class ReportConfig
    {
        public bool includeAntennaPortNumber { get; set; }
        public bool includePeakRssi { get; set; }
        public bool includePcBits { get; set; }
    }

    public class SettingsConfig
    {
        public int tagPopulationEstimate { get; set; }
        public int session { get; set; }
        public bool maxRxSensitivity { get; set; }
    }

    public class KeepaliveConfig
    {
        public bool enabled { get; set; }
        public int periodInMs { get; set; }
    }

    public class StatisticsConfig
    {
        public int updateIntervalMs { get; set; }
    }

    public class ConnectionConfig
    {
        public string hostname { get; set; }
        public int connectionTimeoutMs { get; set; }
        public KeepaliveConfig keepalive { get; set; }
    }

    public class InventoryConfig
    {
        public string mode { get; set; }
        public int fixedDurationMs { get; set; }
    }

    public class LoggingConfig
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

    public class AppConfig
    {
        public ConnectionConfig connection { get; set; }
        public InventoryConfig inventory { get; set; }
        public ReaderConfig reader { get; set; }
        public AntennaConfig antenna { get; set; }
        public ReportConfig report { get; set; }
        public SettingsConfig settings { get; set; }
        public KeepaliveConfig keepalive { get; set; }
        public StatisticsConfig statistics { get; set; }
        public LoggingConfig logging { get; set; }
    }

    class Program
    {
        static FixedReader reader = new FixedReader();
        static int totalTagCount = 0;
        static HashSet<string> uniqueTags = new HashSet<string>();
        static Dictionary<string, int> tagCounts = new Dictionary<string, int>();
        static Dictionary<string, RssiStatistics> rssiStats = new Dictionary<string, RssiStatistics>();
        static Dictionary<string, int> tagDisplayLines = new Dictionary<string, int>();
        static List<string> tagOrder = new List<string>();
        static int nextDisplayLine = 0;
        static readonly object displayLock = new object();
        static DateTime startTime;
        static int tagsPerSecond = 0;
        static int lastSecondCount = 0;
        static Timer statisticsTimer;
        static AppConfig config;

        static AppConfig LoadConfig()
        {
            try
            {
                string configPath = "config.json";
                if (!File.Exists(configPath))
                {
                    Console.WriteLine($"Config file not found: {configPath}");
                    Console.WriteLine("Creating default config file...");
                    CreateDefaultConfig(configPath);
                    return GetDefaultConfig();
                }

                string jsonContent = File.ReadAllText(configPath);
                JavaScriptSerializer serializer = new JavaScriptSerializer();
                var loadedConfig = serializer.Deserialize<AppConfig>(jsonContent);

                // Null 체크 및 기본값 설정
                if (loadedConfig == null)
                {
                    Console.WriteLine("Config loaded as null, using defaults...");
                    return GetDefaultConfig();
                }

                // 각 섹션별 null 체크
                if (loadedConfig.connection == null)
                    loadedConfig.connection = GetDefaultConfig().connection;
                if (loadedConfig.inventory == null)
                    loadedConfig.inventory = GetDefaultConfig().inventory;
                if (loadedConfig.antenna == null)
                    loadedConfig.antenna = GetDefaultConfig().antenna;
                if (loadedConfig.report == null)
                    loadedConfig.report = GetDefaultConfig().report;
                if (loadedConfig.settings == null)
                    loadedConfig.settings = GetDefaultConfig().settings;
                if (loadedConfig.statistics == null)
                    loadedConfig.statistics = GetDefaultConfig().statistics;
                if (loadedConfig.logging == null)
                    loadedConfig.logging = GetDefaultConfig().logging;

                return loadedConfig;
            }
            catch (Exception e)
            {
                Console.WriteLine($"Error loading config: {e.Message}");
                Console.WriteLine($"Stack trace: {e.StackTrace}");
                Console.WriteLine("Using default settings...");
                return GetDefaultConfig();
            }
        }

        static void CreateDefaultConfig(string path)
        {
            var defaultConfig = GetDefaultConfig();
            JavaScriptSerializer serializer = new JavaScriptSerializer();
            string jsonContent = serializer.Serialize(defaultConfig);
            File.WriteAllText(path, jsonContent);
        }

        static AppConfig GetDefaultConfig()
        {
            return new AppConfig
            {
                connection = new ConnectionConfig
                {
                    hostname = "192.168.10.106",
                    connectionTimeoutMs = 30000,
                    keepalive = new KeepaliveConfig { enabled = true, periodInMs = 10000 }
                },
                inventory = new InventoryConfig { mode = "FixedDuration", fixedDurationMs = 60000 },
                antenna = new AntennaConfig { portNumber = 1, isEnabled = true, maxTxPower = false, txPower = 14.0 },
                report = new ReportConfig { includeAntennaPortNumber = true, includePeakRssi = true, includePcBits = true },
                settings = new SettingsConfig { tagPopulationEstimate = 30, session = 0, maxRxSensitivity = true },
                statistics = new StatisticsConfig { updateIntervalMs = 1000 },
                logging = new LoggingConfig
                {
                    enableConsoleLogging = false,
                    enableFileLogging = true,
                    logLevel = "Info",
                    logFilePath = "logs/rfid_reader.log",
                    maxLogFileSize = 10485760,
                    keepLogDays = 7,
                    includeTimestamp = true,
                    includeLogLevel = true,
                    includeThreadId = false,
                    dateFormat = "yyyy-MM-dd HH:mm:ss.fff",
                    rotateLogFiles = true,
                    maxLogFiles = 10,
                    logTagData = true,
                    logStatistics = true,
                    logConnectionEvents = true,
                    logErrors = true,
                    logDebugInfo = false
                }
            };
        }

        static void Main(string[] args)
        {
            try
            {
                // 설정 로드
                config = LoadConfig();

                // 로거 초기화
                var logConfig = new LogConfig
                {
                    enableConsoleLogging = config.logging.enableConsoleLogging,
                    enableFileLogging = config.logging.enableFileLogging,
                    logLevel = config.logging.logLevel,
                    logFilePath = config.logging.logFilePath,
                    maxLogFileSize = config.logging.maxLogFileSize,
                    keepLogDays = config.logging.keepLogDays,
                    includeTimestamp = config.logging.includeTimestamp,
                    includeLogLevel = config.logging.includeLogLevel,
                    includeThreadId = config.logging.includeThreadId,
                    dateFormat = config.logging.dateFormat,
                    rotateLogFiles = config.logging.rotateLogFiles,
                    maxLogFiles = config.logging.maxLogFiles,
                    logTagData = config.logging.logTagData,
                    logStatistics = config.logging.logStatistics,
                    logConnectionEvents = config.logging.logConnectionEvents,
                    logErrors = config.logging.logErrors,
                    logDebugInfo = config.logging.logDebugInfo
                };
                Logger.Initialize(logConfig);

                Logger.Info("=== FR900 RFID Reader Inventory ===");
                Logger.Info($"Connecting to {config.connection.hostname}...");
                Logger.Info($"Inventory Mode: {config.inventory.mode}");

                Console.WriteLine("=== FR900 RFID Reader Inventory ===");
                Console.WriteLine($"Connecting to {config.connection.hostname}...");

                reader.Connect(config.connection.hostname);
                Logger.LogConnection("CONNECT", config.connection.hostname, true);
                Console.WriteLine("Connected successfully!");

                // 이벤트 핸들러 등록
                reader.TagReportCallback += OnTagsReported;

                // 설정 파일 기반 리더 설정
                Settings settings = reader.GetDefaultSettings();

                // 리포트 설정
                settings.Report.IncludeAntennaPortNumber = config.report.includeAntennaPortNumber;
                settings.Report.IncludePeakRssi = config.report.includePeakRssi;
                settings.Report.IncludePcBits = config.report.includePcBits;

                // 안테나 설정
                settings.Antennas.DisableAll();
                settings.Antennas.GetAntenna((ushort)config.antenna.portNumber).IsEnabled = config.antenna.isEnabled;
                settings.Antennas.GetAntenna((ushort)config.antenna.portNumber).MaxTxPower = config.antenna.maxTxPower;
                settings.Antennas.GetAntenna((ushort)config.antenna.portNumber).TxPower = config.antenna.txPower;

                // 기타 설정
                settings.TagPopulationEstimate = (ushort)config.settings.tagPopulationEstimate;
                settings.Session = (ushort)config.settings.session;
                settings.Antennas.MaxRxSensitivity = config.settings.maxRxSensitivity;

                // Keep-alive 설정
                if (config.keepalive.enabled)
                {
                    settings.Keepalives.Enabled = config.keepalive.enabled;
                    settings.Keepalives.PeriodInMs = (ushort)config.keepalive.periodInMs;
                }

                reader.SetCurrentSettings(settings);
                Logger.Info("Reader settings configured");
                Logger.Info($"Antenna {config.antenna.portNumber}: {config.antenna.txPower} dBm");
                Console.WriteLine("Reader settings configured!");
                Console.WriteLine($"Antenna {config.antenna.portNumber}: {config.antenna.txPower} dBm");

                int durationSeconds = config.inventory.fixedDurationMs / 1000;
                Logger.Info($"Starting {durationSeconds}-second inventory...");
                Console.WriteLine($"\nStarting {durationSeconds}-second inventory...");
                Console.WriteLine("EPC Tags Found:");
                Console.WriteLine("================");

                startTime = DateTime.Now;
                statisticsTimer = new Timer(ShowStatistics, null, config.statistics.updateIntervalMs, config.statistics.updateIntervalMs);

                reader.Start();
                Logger.Info("Inventory started");

                Thread.Sleep(config.inventory.fixedDurationMs);

                reader.Stop();
                Logger.Info("Inventory stopped");

                reader.Disconnect();
                Logger.LogConnection("DISCONNECT", config.connection.hostname, true);

                ShowFinalReport();

                // 로거 닫기
                Logger.Close();
            }
            catch (Exception e)
            {
                Logger.Error($"ERROR: {e.Message}");
                Logger.Error($"Stack Trace: {e.StackTrace}");
                Console.WriteLine($"ERROR: {e.Message}");
                Logger.Close();
            }

            Console.WriteLine("\nPress any key to exit...");
            Console.ReadKey();
        }

        static void UpdateTagDisplay(string epc, string displayText)
        {
            lock (displayLock)
            {
                try
                {
                    if (!tagDisplayLines.ContainsKey(epc))
                    {
                        tagDisplayLines[epc] = nextDisplayLine++;
                        tagOrder.Add(epc);
                    }

                    int tagIndex = tagOrder.IndexOf(epc);
                    int currentCursorTop = Console.CursorTop;
                    int targetLine = Math.Max(0, currentCursorTop - (tagOrder.Count - 1 - tagIndex));

                    // 안전한 커서 위치 설정
                    if (targetLine >= 0 && targetLine < Console.WindowHeight - 1)
                    {
                        Console.SetCursorPosition(0, targetLine);
                        Console.Write(new string(' ', Math.Min(Console.WindowWidth - 1, 150)));
                        Console.SetCursorPosition(0, targetLine);
                        Console.Write(displayText.Length > Console.WindowWidth - 1 ?
                                    displayText.Substring(0, Console.WindowWidth - 1) : displayText);
                        Console.SetCursorPosition(0, currentCursorTop);
                    }
                }
                catch
                {
                    // 커서 조작 실패시 단순히 새 줄에 출력
                    Console.WriteLine(displayText);
                }
            }
        }

        static void AddNewTagLine(string epc, string displayText)
        {
            lock (displayLock)
            {
                if (!tagDisplayLines.ContainsKey(epc))
                {
                    tagDisplayLines[epc] = nextDisplayLine++;
                    tagOrder.Add(epc);
                    Console.WriteLine(displayText);
                }
            }
        }

        static void OnTagsReported(FixedReader sender, TagReport report)
        {
            foreach (Tag tag in report)
            {
                if (!string.IsNullOrEmpty(tag.Epc))
                {
                    totalTagCount++;
                    bool isNewTag = uniqueTags.Add(tag.Epc);

                    if (tagCounts.ContainsKey(tag.Epc))
                        tagCounts[tag.Epc]++;
                    else
                        tagCounts[tag.Epc] = 1;

                    // RSSI 통계 업데이트
                    if (!rssiStats.ContainsKey(tag.Epc))
                        rssiStats[tag.Epc] = new RssiStatistics();

                    rssiStats[tag.Epc].AddValue(tag.PeakRssi);

                    // 로그에 태그 정보 기록 (가중평균 RSSI 사용)
                    double avgRssi = rssiStats[tag.Epc].WeightedMean;
                    Logger.LogTag(tag.Epc, tag.AntennaPortNumber, avgRssi, tagCounts[tag.Epc]);

                    // 디스플레이 텍스트 생성
                    string displayText;

                    if (isNewTag)
                    {
                        displayText = $"EPC: {tag.Epc} | Ant: {tag.AntennaPortNumber} | RSSI: {tag.PeakRssi:F1} (Avg: {avgRssi:F1}) | Count: {tagCounts[tag.Epc]} | 상태: 측정중";
                        AddNewTagLine(tag.Epc, displayText);
                    }
                    else
                    {
                        // RSSI 통계가 충분히 쌓였을 때만 상세 정보 표시
                        var stats = rssiStats[tag.Epc];
                        string displayInfo;

                        if (stats.SampleCount >= 5)
                        {
                            string rssiInfo = $"{tag.PeakRssi:F1} (F:{stats.FilteredMean:F1} ±{stats.StandardDeviation:F1})";
                            string movementInfo = stats.MovementStatus;
                            displayInfo = $"RSSI: {rssiInfo} | Count: {tagCounts[tag.Epc]} | 상태: {movementInfo}";
                        }
                        else
                        {
                            displayInfo = $"RSSI: {tag.PeakRssi:F1} (Avg: {avgRssi:F1}) | Count: {tagCounts[tag.Epc]} | 상태: 측정중";
                        }

                        displayText = $"EPC: {tag.Epc} | Ant: {tag.AntennaPortNumber} | {displayInfo}";
                        UpdateTagDisplay(tag.Epc, displayText);
                    }
                }
            }
        }

        static void ShowStatistics(object state)
        {
            int currentCount = totalTagCount;
            tagsPerSecond = currentCount - lastSecondCount;
            lastSecondCount = currentCount;

            TimeSpan elapsed = DateTime.Now - startTime;

            // 통계 로깅
            Logger.LogStatistics(totalTagCount, uniqueTags.Count, tagsPerSecond);

            Console.WriteLine($"[{elapsed.Seconds}s] Rate: {tagsPerSecond} tags/s | Total: {totalTagCount} | Unique: {uniqueTags.Count}");
        }

        static void ShowFinalReport()
        {
            TimeSpan totalTime = DateTime.Now - startTime;
            double avgRate = totalTagCount / totalTime.TotalSeconds;

            Console.WriteLine("\n" + new string('=', 50));
            Console.WriteLine("INVENTORY COMPLETE - FINAL REPORT");
            Console.WriteLine(new string('=', 50));
            Console.WriteLine($"Duration: {totalTime.TotalSeconds:F1} seconds");
            Console.WriteLine($"Total tags read: {totalTagCount}");
            Console.WriteLine($"Unique tags found: {uniqueTags.Count}");
            Console.WriteLine($"Average rate: {avgRate:F1} tags/second");

            if (uniqueTags.Count > 0)
            {
                Console.WriteLine("\nUnique EPC List with RSSI Statistics and Movement Analysis:");
                Console.WriteLine(new string('-', 90));
                foreach (var epc in uniqueTags)
                {
                    var stats = rssiStats[epc];
                    Console.WriteLine($"EPC: {epc}");
                    Console.WriteLine($"  Count: {tagCounts[epc]} reads");
                    Console.WriteLine($"  RSSI Stats: {stats.GetStatsSummary()}");
                    Console.WriteLine($"  Movement: {stats.GetMovementSummary()}");
                    Console.WriteLine();
                }
            }
            else
            {
                Console.WriteLine("\nNo tags detected during inventory.");
                Console.WriteLine("Possible causes:");
                Console.WriteLine("- No RFID tags in antenna range");
                Console.WriteLine("- Tags not EPC Gen2 compatible");
                Console.WriteLine("- Antenna connection issues");
                Console.WriteLine("- RF interference");
            }
        }
    }
}