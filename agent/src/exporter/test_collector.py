"""单元测试 - collector.py

测试指标采集器的各项功能。

Usage:
    cd /root/.openclaw/workspace/opc200
    python3 -m pytest agent/src/exporter/test_collector.py -v

Author: @zhang-chenyang-claw
"""

import unittest
import sys
import os

# 添加模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collector import MetricsCollector, SystemMetrics


class TestSystemMetrics(unittest.TestCase):
    """测试 SystemMetrics 数据类"""
    
    def test_default_values(self):
        """测试默认值"""
        m = SystemMetrics()
        self.assertEqual(m.cpu_usage, 0.0)
        self.assertEqual(m.memory_usage, 0.0)
        self.assertEqual(m.disk_usage, 0.0)
        self.assertEqual(m.agent_health, 1)
        self.assertIsNone(m.error)
    
    def test_to_prometheus_format(self):
        """测试 Prometheus 格式转换"""
        m = SystemMetrics(
            cpu_usage=45.5,
            memory_usage=78.2,
            disk_usage=65.0,
            agent_health=1,
            agent_version="1.0.0",
            os="linux"
        )
        output = m.to_prometheus(tenant_id="opc-001")
        
        # 验证包含必要指标
        self.assertIn('agent_health{tenant_id="opc-001"', output)
        self.assertIn('cpu_usage{tenant_id="opc-001"', output)
        self.assertIn('memory_usage{tenant_id="opc-001"', output)
        self.assertIn('disk_usage{tenant_id="opc-001"', output)
        
        # 验证数值
        self.assertIn('cpu_usage', output)
        self.assertIn('45.5', output)
        
        # 验证格式正确（Prometheus 格式）
        lines = output.strip().split('\n')
        self.assertEqual(len(lines), 4)
        
        for line in lines:
            # 格式: metric_name{labels} value
            self.assertIn('{', line)
            self.assertIn('}', line)
            parts = line.split('}')
            self.assertEqual(len(parts), 2)
    
    def test_to_dict(self):
        """测试字典转换"""
        m = SystemMetrics(cpu_usage=50.0, memory_usage=60.0)
        d = m.to_dict()
        self.assertEqual(d['cpu_usage'], 50.0)
        self.assertEqual(d['memory_usage'], 60.0)
        self.assertEqual(d['agent_health'], 1)


class TestMetricsCollector(unittest.TestCase):
    """测试 MetricsCollector 采集器"""
    
    def test_initialization(self):
        """测试初始化"""
        collector = MetricsCollector(agent_version="1.0.0")
        self.assertEqual(collector.agent_version, "1.0.0")
        self.assertIn(collector.os, ["linux", "darwin", "windows"])
        self.assertIsNotNone(collector.arch)
        self.assertIsNotNone(collector.hostname)
    
    def test_collect_all(self):
        """测试采集所有指标"""
        collector = MetricsCollector(agent_version="1.0.0")
        metrics = collector.collect_all()
        
        # 验证返回类型
        self.assertIsInstance(metrics, SystemMetrics)
        
        # 验证字段存在且为数值
        self.assertIsInstance(metrics.cpu_usage, float)
        self.assertIsInstance(metrics.memory_usage, float)
        self.assertIsInstance(metrics.disk_usage, float)
        self.assertIn(metrics.agent_health, [0, 1])
        
        # 验证范围合理
        self.assertGreaterEqual(metrics.cpu_usage, 0.0)
        self.assertLessEqual(metrics.cpu_usage, 100.0)
        self.assertGreaterEqual(metrics.memory_usage, 0.0)
        self.assertLessEqual(metrics.memory_usage, 100.0)
        self.assertGreaterEqual(metrics.disk_usage, 0.0)
        self.assertLessEqual(metrics.disk_usage, 100.0)
    
    def test_cpu_collection(self):
        """测试 CPU 采集"""
        collector = MetricsCollector()
        cpu = collector._collect_cpu()
        self.assertIsInstance(cpu, float)
        self.assertGreaterEqual(cpu, 0.0)
        self.assertLessEqual(cpu, 100.0)
    
    def test_memory_collection(self):
        """测试内存采集"""
        collector = MetricsCollector()
        mem = collector._collect_memory()
        self.assertIsInstance(mem, float)
        self.assertGreaterEqual(mem, 0.0)
        self.assertLessEqual(mem, 100.0)
    
    def test_disk_collection(self):
        """测试磁盘采集"""
        collector = MetricsCollector()
        disk = collector._collect_disk()
        self.assertIsInstance(disk, float)
        self.assertGreaterEqual(disk, 0.0)
        self.assertLessEqual(disk, 100.0)
    
    def test_health_check(self):
        """测试健康检查"""
        collector = MetricsCollector()
        health = collector._check_health()
        self.assertIn(health, [0, 1])
    
    def test_error_handling(self):
        """测试错误处理"""
        # 正常情况不应有错误
        collector = MetricsCollector()
        metrics = collector.collect_all()
        self.assertIsNone(metrics.error)
    
    def test_prometheus_output_integrity(self):
        """测试 Prometheus 输出完整性"""
        collector = MetricsCollector(agent_version="1.0.0")
        metrics = collector.collect_all()
        output = metrics.to_prometheus(tenant_id="test-tenant")
        
        # 验证包含所有必需的标签
        self.assertIn('tenant_id="test-tenant"', output)
        self.assertIn('agent_version="1.0.0"', output)
        self.assertIn(f'os="{collector.os}"', output)


class TestLinuxSpecific(unittest.TestCase):
    """Linux 特定测试"""
    
    def setUp(self):
        import platform
        if platform.system().lower() != 'linux':
            self.skipTest("非 Linux 系统，跳过 Linux 特定测试")
    
    def test_proc_meminfo_parsing(self):
        """测试 /proc/meminfo 解析"""
        collector = MetricsCollector()
        mem = collector._collect_memory_linux()
        self.assertGreater(mem, 0.0)  # 应该有值
        self.assertLessEqual(mem, 100.0)
    
    def test_proc_stat_parsing(self):
        """测试 /proc/stat 解析"""
        collector = MetricsCollector()
        cpu = collector._collect_cpu_linux()
        # CPU 可能为 0（空闲时），但应该能正常执行
        self.assertIsInstance(cpu, float)


class TestCrossPlatform(unittest.TestCase):
    """跨平台兼容性测试"""
    
    def test_all_platforms_detected(self):
        """测试平台检测"""
        collector = MetricsCollector()
        self.assertIn(collector.os, ['linux', 'darwin', 'windows'])
    
    def test_arch_detection(self):
        """测试架构检测"""
        collector = MetricsCollector()
        self.assertIsNotNone(collector.arch)
        self.assertIn(collector.arch.lower(), [
            'x86_64', 'amd64', 'i386', 'i686',
            'arm64', 'aarch64', 'armv7l'
        ])


if __name__ == '__main__':
    unittest.main(verbosity=2)
