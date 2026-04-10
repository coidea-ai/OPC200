"""OPC200 Agent Exporter - 系统指标采集器

采集 CPU、内存、磁盘使用率及 Agent 健康状态。
支持 Linux、macOS、Windows 跨平台。

Usage:
    from collector import MetricsCollector
    
    collector = MetricsCollector(agent_version="1.0.0")
    metrics = collector.collect_all()
    print(metrics.to_prometheus())

Author: @zhang-chenyang-claw (zhangyao719)
"""

import platform
import subprocess
import shutil
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class SystemMetrics:
    """系统指标数据结构"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    agent_health: int = 1  # 1 = healthy, 0 = unhealthy
    agent_version: str = "1.0.0"
    os: str = "linux"
    hostname: str = "unknown"
    arch: str = "amd64"
    error: Optional[str] = None
    
    def to_prometheus(self, tenant_id: str) -> str:
        """转换为 Prometheus 文本格式"""
        labels = f'tenant_id="{tenant_id}",agent_version="{self.agent_version}",os="{self.os}"'
        lines = [
            f'agent_health{{{labels}}} {self.agent_health}',
            f'cpu_usage{{{labels}}} {self.cpu_usage:.1f}',
            f'memory_usage{{{labels}}} {self.memory_usage:.1f}',
            f'disk_usage{{{labels}}} {self.disk_usage:.1f}',
        ]
        return '\n'.join(lines) + '\n'
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'agent_health': self.agent_health,
        }


class MetricsCollector:
    """系统指标采集器"""
    
    def __init__(self, agent_version: str = "1.0.0"):
        self.agent_version = agent_version
        self.os = self._detect_os()
        self.arch = platform.machine().lower()
        self.hostname = platform.node()
        
    def _detect_os(self) -> str:
        """检测操作系统"""
        system = platform.system().lower()
        if system == "darwin":
            return "darwin"  # macOS
        elif system == "windows":
            return "windows"
        else:
            return "linux"
    
    def collect_all(self) -> SystemMetrics:
        """采集所有指标"""
        try:
            metrics = SystemMetrics(
                agent_version=self.agent_version,
                os=self.os,
                hostname=self.hostname,
                arch=self.arch,
            )
            
            # 采集各项指标
            metrics.cpu_usage = self._collect_cpu()
            metrics.memory_usage = self._collect_memory()
            metrics.disk_usage = self._collect_disk()
            metrics.agent_health = self._check_health()
            
            return metrics
            
        except Exception as e:
            return SystemMetrics(
                agent_version=self.agent_version,
                os=self.os,
                hostname=self.hostname,
                arch=self.arch,
                agent_health=0,
                error=str(e),
            )
    
    def _collect_cpu(self) -> float:
        """采集 CPU 使用率"""
        try:
            if self.os == "linux":
                return self._collect_cpu_linux()
            elif self.os == "darwin":
                return self._collect_cpu_darwin()
            elif self.os == "windows":
                return self._collect_cpu_windows()
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def _collect_cpu_linux(self) -> float:
        """Linux CPU 采集"""
        # 方法1: 使用 mpstat (if available)
        if shutil.which("mpstat"):
            try:
                result = subprocess.run(
                    ["mpstat", "1", "1"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'Average' in line or 'all' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            # mpstat 输出: %usr %nice %sys %iowait %irq %soft %steal %guest %idle
                            idle_idx = -1  # 最后一个通常是 idle
                            idle = float(parts[idle_idx])
                            return round(100.0 - idle, 1)
            except Exception:
                pass
        
        # 方法2: 使用 /proc/stat
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                fields = line.split()
                if len(fields) >= 5:
                    user = float(fields[1])
                    nice = float(fields[2])
                    system = float(fields[3])
                    idle = float(fields[4])
                    total = user + nice + system + idle
                    if total > 0:
                        return round(100.0 * (user + nice + system) / total, 1)
        except Exception:
            pass
        
        # 方法3: 使用 top
        if shutil.which("top"):
            try:
                result = subprocess.run(
                    ["top", "-bn1"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                for line in result.stdout.split('\n'):
                    if '%Cpu' in line or 'Cpu(s)' in line:
                        # 解析: %Cpu(s):  5.6 us,  3.4 sy,  0.0 ni, 90.8 id
                        if 'id' in line:
                            parts = line.split(',')
                            for part in parts:
                                if 'id' in part:
                                    idle_str = part.strip().split()[0]
                                    idle = float(idle_str)
                                    return round(100.0 - idle, 1)
            except Exception:
                pass
        
        return 0.0
    
    def _collect_cpu_darwin(self) -> float:
        """macOS CPU 采集"""
        # 使用 top 命令
        try:
            result = subprocess.run(
                ["top", "-l", "1", "-n", "0"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'CPU usage' in line:
                    # 解析: CPU usage: 7.12% user, 12.34% sys, 80.54% idle
                    if 'idle' in line:
                        parts = line.split(',')
                        for part in parts:
                            if 'idle' in part:
                                idle_str = part.split('%')[0].strip().split()[-1]
                                idle = float(idle_str)
                                return round(100.0 - idle, 1)
        except Exception:
            pass
        
        # 备选: vm_stat + sysctl
        try:
            result = subprocess.run(
                ["sysctl", "-n", "vm.loadavg"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # 简单估算，不够准确
            return 0.0
        except Exception:
            pass
        
        return 0.0
    
    def _collect_cpu_windows(self) -> float:
        """Windows CPU 采集 (需要 PowerShell)"""
        try:
            # 使用 wmic
            result = subprocess.run(
                ["wmic", "cpu", "get", "loadpercentage", "/value"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'LoadPercentage' in line:
                    value = line.split('=')[-1].strip()
                    if value and value.isdigit():
                        return float(value)
        except Exception:
            pass
        
        return 0.0
    
    def _collect_memory(self) -> float:
        """采集内存使用率"""
        try:
            if self.os == "linux":
                return self._collect_memory_linux()
            elif self.os == "darwin":
                return self._collect_memory_darwin()
            elif self.os == "windows":
                return self._collect_memory_windows()
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def _collect_memory_linux(self) -> float:
        """Linux 内存采集"""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    key, value = line.split(':')
                    meminfo[key.strip()] = int(value.split()[0])  # kB
                
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', 0)
                
                # 如果没有 MemAvailable，用 MemFree + Buffers + Cached 估算
                if available == 0:
                    free = meminfo.get('MemFree', 0)
                    buffers = meminfo.get('Buffers', 0)
                    cached = meminfo.get('Cached', 0)
                    available = free + buffers + cached
                
                if total > 0:
                    used = total - available
                    return round(100.0 * used / total, 1)
        except Exception:
            pass
        
        # 备选: free 命令
        if shutil.which("free"):
            try:
                result = subprocess.run(
                    ["free"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.startswith('Mem:'):
                        parts = line.split()
                        if len(parts) >= 3:
                            total = int(parts[1])
                            used = int(parts[2])
                            if total > 0:
                                return round(100.0 * used / total, 1)
            except Exception:
                pass
        
        return 0.0
    
    def _collect_memory_darwin(self) -> float:
        """macOS 内存采集"""
        try:
            # 获取总内存
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True,
                text=True,
                timeout=5
            )
            total_bytes = int(result.stdout.strip())
            
            # 获取内存统计
            result = subprocess.run(
                ["vm_stat"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            page_size = 4096  # 默认页大小
            vm_stats = {}
            
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':')
                    key = key.strip()
                    value = int(value.strip().replace('.', ''))
                    vm_stats[key] = value
            
            # 计算已用内存
            free_pages = vm_stats.get('Pages free', 0)
            inactive_pages = vm_stats.get('Pages inactive', 0)
            speculative_pages = vm_stats.get('Pages speculative', 0)
            
            free_bytes = (free_pages + inactive_pages + speculative_pages) * page_size
            used_bytes = total_bytes - free_bytes
            
            if total_bytes > 0:
                return round(100.0 * used_bytes / total_bytes, 1)
                
        except Exception:
            pass
        
        return 0.0
    
    def _collect_memory_windows(self) -> float:
        """Windows 内存采集"""
        try:
            # 使用 wmic
            result = subprocess.run(
                ["wmic", "OS", "get", "TotalVisibleMemorySize,FreePhysicalMemory", "/value"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            total = 0
            free = 0
            
            for line in result.stdout.split('\n'):
                if 'TotalVisibleMemorySize' in line:
                    total = int(line.split('=')[-1].strip())
                elif 'FreePhysicalMemory' in line:
                    free = int(line.split('=')[-1].strip())
            
            if total > 0:
                used = total - free
                return round(100.0 * used / total, 1)
                
        except Exception:
            pass
        
        return 0.0
    
    def _collect_disk(self) -> float:
        """采集磁盘使用率"""
        try:
            if self.os == "linux" or self.os == "darwin":
                return self._collect_disk_unix()
            elif self.os == "windows":
                return self._collect_disk_windows()
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def _collect_disk_unix(self) -> float:
        """Linux/macOS 磁盘采集"""
        # 使用 df 命令
        try:
            result = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                # 第二行是数据
                parts = lines[1].split()
                if len(parts) >= 5:
                    # 格式: Filesystem Size Used Avail Use% Mount
                    use_percent = parts[4].replace('%', '')
                    return float(use_percent)
        except Exception:
            pass
        
        # 备选: statvfs
        try:
            import os
            stat = os.statvfs('/')
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            if total > 0:
                used = total - free
                return round(100.0 * used / total, 1)
        except Exception:
            pass
        
        return 0.0
    
    def _collect_disk_windows(self) -> float:
        """Windows 磁盘采集"""
        try:
            # 使用 wmic
            result = subprocess.run(
                ["wmic", "logicaldisk", "where", "DeviceID='C:'", "get", "Size,FreeSpace", "/value"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            total = 0
            free = 0
            
            for line in result.stdout.split('\n'):
                if 'Size' in line and 'FreeSpace' not in line:
                    total = int(line.split('=')[-1].strip())
                elif 'FreeSpace' in line:
                    free = int(line.split('=')[-1].strip())
            
            if total > 0:
                used = total - free
                return round(100.0 * used / total, 1)
                
        except Exception:
            pass
        
        return 0.0
    
    def _check_health(self) -> int:
        """检查 Agent 健康状态"""
        # 基础检查: 能正常采集指标就是健康的
        try:
            cpu = self._collect_cpu()
            mem = self._collect_memory()
            disk = self._collect_disk()
            
            # 如果所有指标都是 0，可能有问题
            if cpu == 0 and mem == 0 and disk == 0:
                return 0  # unhealthy
            
            return 1  # healthy
        except Exception:
            return 0  # unhealthy


# 简单的 CLI 测试
if __name__ == "__main__":
    import json
    
    print("OPC200 Metrics Collector Test")
    print("=" * 40)
    
    collector = MetricsCollector(agent_version="1.0.0")
    print(f"OS: {collector.os}")
    print(f"Arch: {collector.arch}")
    print(f"Hostname: {collector.hostname}")
    print()
    
    print("Collecting metrics...")
    metrics = collector.collect_all()
    
    print()
    print("Results:")
    print(f"  CPU Usage: {metrics.cpu_usage}%")
    print(f"  Memory Usage: {metrics.memory_usage}%")
    print(f"  Disk Usage: {metrics.disk_usage}%")
    print(f"  Agent Health: {'✓ Healthy' if metrics.agent_health else '✗ Unhealthy'}")
    
    if metrics.error:
        print(f"  Error: {metrics.error}")
    
    print()
    print("Prometheus Format:")
    print(metrics.to_prometheus(tenant_id="test-opc-001"))
