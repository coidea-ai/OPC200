"""
Performance tests for OPC200.
"""
import time
import pytest

pytestmark = [pytest.mark.performance, pytest.mark.slow]


class TestJournalPerformance:
    """Performance tests for journal operations."""
    
    def test_bulk_entry_insertion(self, in_memory_db):
        """Test performance of bulk entry insertion."""
        from src.journal.core import JournalEntry, JournalManager
        
        manager = JournalManager(in_memory_db)
        manager.create_table()
        
        # Create 1000 entries
        entries = [
            JournalEntry(content=f"Test content {i}", tags=["test", f"tag{i%10}"])
            for i in range(1000)
        ]
        
        start_time = time.time()
        for entry in entries:
            manager.create_entry(entry)
        duration = time.time() - start_time
        
        # Should complete within 10 seconds
        assert duration < 10.0
        assert len(manager.list_entries(limit=1000)) == 1000
    
    def test_search_performance(self, in_memory_db):
        """Test search performance with large dataset."""
        from src.journal.core import JournalEntry, JournalManager
        
        manager = JournalManager(in_memory_db)
        manager.create_table()
        
        # Create entries
        for i in range(500):
            entry = JournalEntry(
                content=f"This is a searchable test content number {i}",
                tags=["test"]
            )
            manager.create_entry(entry)
        
        # Measure search time
        start_time = time.time()
        results = manager.search_entries("searchable")
        duration = time.time() - start_time
        
        # Should complete within 1 second
        assert duration < 1.0
        assert len(results) == 500


class TestEncryptionPerformance:
    """Performance tests for encryption operations."""
    
    def test_encryption_speed(self):
        """Test encryption throughput."""
        from src.security.encryption import EncryptionService
        
        service = EncryptionService(key=EncryptionService.generate_key())
        data = b"X" * (1024 * 1024)  # 1MB of data
        
        # Measure encryption time
        start_time = time.time()
        encrypted = service.encrypt(data)
        duration = time.time() - start_time
        
        # Should encrypt 1MB within 0.1 seconds
        assert duration < 0.1
    
    def test_streaming_encryption_large_file(self, temp_dir):
        """Test streaming encryption for large files."""
        from src.security.encryption import FileEncryption, EncryptionService
        
        key = EncryptionService.generate_key()
        file_encryption = FileEncryption(key)
        
        # Create a 10MB test file
        input_path = temp_dir / "large_input.bin"
        output_path = temp_dir / "large_output.enc"
        input_path.write_bytes(b"X" * (10 * 1024 * 1024))
        
        # Measure encryption time
        start_time = time.time()
        file_encryption.encrypt_file_streaming(input_path, output_path, chunk_size=1024*1024)
        duration = time.time() - start_time
        
        # Should complete within 5 seconds
        assert duration < 5.0
        assert output_path.exists()
