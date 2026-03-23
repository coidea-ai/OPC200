"""
Performance tests for OPC200.
Optimized benchmarks with baseline comparisons.
"""

import time
import pytest
import statistics
from functools import wraps

pytestmark = [pytest.mark.performance, pytest.mark.slow]


def benchmark(iterations=5, warmup=1):
    """Decorator for running benchmark multiple times and reporting stats."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Warmup runs
            for _ in range(warmup):
                func(*args, **kwargs)
            
            # Timed runs
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                end = time.perf_counter()
                times.append(end - start)
            
            # Store stats on the result
            if hasattr(result, '__benchmark_stats__'):
                result = result.__class__()  # Get fresh result
            
            wrapper._benchmark_stats = {
                'min': min(times),
                'max': max(times),
                'mean': statistics.mean(times),
                'median': statistics.median(times),
                'stdev': statistics.stdev(times) if len(times) > 1 else 0
            }
            
            return result
        return wrapper
    return decorator


class TestJournalPerformance:
    """Performance tests for journal operations."""
    
    BASELINE_INSERT_MS = 10  # Target: 10ms per insert
    BASELINE_SEARCH_MS = 100  # Target: 100ms for search

    @benchmark(iterations=3)
    def test_bulk_entry_insertion(self, in_memory_db):
        """Test performance of bulk entry insertion."""
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        # Create 1000 entries
        entries = [JournalEntry(content=f"Test content {i}", tags=["test", f"tag{i%10}"]) for i in range(1000)]

        start_time = time.perf_counter()
        for entry in entries:
            manager.create_entry(entry)
        duration = time.perf_counter() - start_time

        # Should complete within 10 seconds (10ms per entry)
        avg_ms = (duration / 1000) * 1000
        assert duration < 10.0, f"Insertion too slow: {duration:.2f}s (avg {avg_ms:.2f}ms/entry)"
        assert avg_ms < self.BASELINE_INSERT_MS * 2, f"Avg insertion time {avg_ms:.2f}ms exceeds baseline"
        assert len(manager.list_entries(limit=1000)) == 1000

    @benchmark(iterations=3)
    def test_search_performance(self, in_memory_db):
        """Test search performance with large dataset."""
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        # Create entries with unique searchable content
        for i in range(500):
            entry = JournalEntry(content=f"UniqueSearchTerm test content number {i}", tags=["test"])
            manager.create_entry(entry)

        # Measure search time
        start_time = time.perf_counter()
        results = manager.search_entries("UniqueSearchTerm")
        duration = time.perf_counter() - start_time

        # Should complete within 100ms
        duration_ms = duration * 1000
        assert duration_ms < self.BASELINE_SEARCH_MS * 3, f"Search too slow: {duration_ms:.2f}ms"
        # Results may include entries from previous benchmark iterations
        assert len(results) >= 500

    def test_concurrent_reads(self, in_memory_db):
        """Test concurrent read performance."""
        from src.journal.core import JournalEntry, JournalManager
        import threading

        manager = JournalManager(in_memory_db)
        manager.create_table()

        # Populate data
        for i in range(100):
            manager.create_entry(JournalEntry(content=f"Content {i}"))

        results = []
        
        def read_entries():
            start = time.perf_counter()
            entries = manager.list_entries(limit=100)
            duration = time.perf_counter() - start
            results.append((len(entries), duration))

        # Run 10 concurrent reads
        threads = [threading.Thread(target=read_entries) for _ in range(10)]
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        total_duration = time.perf_counter() - start

        # All reads should complete within 1 second total
        assert total_duration < 1.0, f"Concurrent reads too slow: {total_duration:.2f}s"
        assert all(count == 100 for count, _ in results)


class TestEncryptionPerformance:
    """Performance tests for encryption operations."""
    
    BASELINE_ENCRYPT_MBPS = 100  # Target: 100 MB/s

    @benchmark(iterations=3)
    def test_encryption_speed(self):
        """Test encryption throughput."""
        from src.security.encryption import EncryptionService

        service = EncryptionService(key=EncryptionService.generate_key())
        data_size = 10 * 1024 * 1024  # 10MB
        data = b"X" * data_size

        # Measure encryption time
        start_time = time.perf_counter()
        encrypted = service.encrypt(data)
        duration = time.perf_counter() - start_time

        # Should encrypt 10MB within 0.1 seconds (100MB/s)
        throughput_mbps = (data_size / 1024 / 1024) / duration
        assert throughput_mbps > self.BASELINE_ENCRYPT_MBPS / 2, f"Encryption too slow: {throughput_mbps:.1f} MB/s"

    @benchmark(iterations=3)
    def test_streaming_encryption_large_file(self, temp_dir):
        """Test streaming encryption for large files."""
        from src.security.encryption import FileEncryption, EncryptionService

        key = EncryptionService.generate_key()
        file_encryption = FileEncryption(key)

        # Create a 50MB test file
        input_path = temp_dir / "large_input.bin"
        output_path = temp_dir / "large_output.enc"
        file_size = 50 * 1024 * 1024
        input_path.write_bytes(b"X" * file_size)

        # Measure encryption time
        start_time = time.perf_counter()
        file_encryption.encrypt_file_streaming(input_path, output_path, chunk_size=1024 * 1024)
        duration = time.perf_counter() - start_time

        # Should complete within 2 seconds (25MB/s)
        throughput_mbps = (file_size / 1024 / 1024) / duration
        assert throughput_mbps > 20, f"Streaming encryption too slow: {throughput_mbps:.1f} MB/s"
        assert output_path.exists()


class TestSchedulerPerformance:
    """Performance tests for scheduler operations."""

    def test_cron_parsing_performance(self):
        """Test cron expression parsing speed."""
        from src.tasks.scheduler import CronParser

        parser = CronParser()
        expressions = [
            "0 9 * * 1",      # Weekly Monday
            "*/15 * * * *",   # Every 15 minutes
            "0 0 1 * *",      # Monthly
            "0 */6 * * *",    # Every 6 hours
        ]

        start = time.perf_counter()
        for _ in range(1000):
            for expr in expressions:
                parser.parse(expr)
        duration = time.perf_counter() - start

        # Should parse 4000 expressions within 0.5 seconds
        assert duration < 0.5, f"Cron parsing too slow: {duration:.2f}s for 4000 parses"

    def test_next_run_calculation(self):
        """Test next run calculation performance."""
        from src.tasks.scheduler import CronParser
        from datetime import datetime

        parser = CronParser()
        base_time = datetime(2024, 3, 1, 12, 0, 0)

        start = time.perf_counter()
        for _ in range(1000):
            parser.get_next_run("0 9 * * 1", base_time)
        duration = time.perf_counter() - start

        # Should calculate 1000 next runs within 0.5 seconds
        assert duration < 0.5, f"Next run calculation too slow: {duration:.2f}s"


class TestPatternRecognitionPerformance:
    """Performance tests for pattern recognition."""

    def test_pattern_detection_large_dataset(self):
        """Test pattern detection with large activity dataset."""
        from src.patterns.analyzer import BehaviorAnalyzer
        from datetime import datetime, timedelta

        analyzer = BehaviorAnalyzer()
        
        # Generate 10000 activities
        base_time = datetime(2024, 1, 1, 9, 0, 0)
        activities = []
        for i in range(10000):
            activities.append({
                "timestamp": base_time + timedelta(hours=i % 24),
                "action": "work",
                "output": i % 100
            })

        start = time.perf_counter()
        pattern = analyzer.detect_temporal_pattern(activities, "work")
        duration = time.perf_counter() - start

        # Should analyze 10000 activities within 1 second
        assert duration < 1.0, f"Pattern detection too slow: {duration:.2f}s"
        assert pattern["detected"] is True