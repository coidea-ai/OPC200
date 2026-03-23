# OPC200 - 模式分析模块
# 分析用户行为模式、工作节奏、决策风格

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class PatternProfile:
    """用户模式画像"""
    user_id: str
    pattern_type: str
    confidence: float
    features: Dict[str, Any]
    detected_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': self.user_id,
            'pattern_type': self.pattern_type,
            'confidence': self.confidence,
            'features': self.features,
            'detected_at': self.detected_at.isoformat()
        }


class PatternAnalyzer:
    """
    模式分析器
    
    分析维度：
    - 时间模式：工作时段、效率高峰期
    - 行为模式：任务偏好、交互风格
    - 认知模式：决策速度、反思频率
    - 情绪模式：压力周期、满意度变化
    """
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: 分析数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_db()
    
    def _ensure_db(self):
        """确保数据库结构"""
        with sqlite3.connect(self.db_path) as conn:
            # 模式表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    features TEXT,
                    detected_at TEXT NOT NULL
                )
            """)
            
            # 统计表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pattern_stats (
                    user_id TEXT PRIMARY KEY,
                    total_patterns INTEGER DEFAULT 0,
                    last_analysis TEXT,
                    profile_summary TEXT
                )
            """)
            
            conn.commit()
    
    def analyze_time_patterns(self, journal_entries: List[Dict]) -> Dict[str, Any]:
        """
        分析时间模式
        
        识别：
        - 活跃时段分布
        - 工作效率高峰期
        - 连续工作时长
        - 休息模式
        """
        if not journal_entries:
            return {}
        
        # 提取时间信息
        hours = defaultdict(int)
        weekdays = defaultdict(int)
        
        for entry in journal_entries:
            ts = datetime.fromisoformat(entry['timestamp'])
            hours[ts.hour] += 1
            weekdays[ts.weekday()] += 1
        
        # 找出高峰期
        peak_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # 计算时间分布特征
        all_hours = list(range(24))
        hour_counts = [hours.get(h, 0) for h in all_hours]
        
        # 计算变异系数（衡量规律性）
        cv = np.std(hour_counts) / (np.mean(hour_counts) + 0.001)
        
        return {
            'peak_hours': [h for h, _ in peak_hours],
            'peak_hours_activity': [c for _, c in peak_hours],
            'weekday_distribution': dict(weekdays),
            'regularity_score': 1.0 / (1.0 + cv),  # 越规律分数越高
            'early_bird': 7 in [h for h, _ in peak_hours[:2]],
            'night_owl': 22 in [h for h, _ in peak_hours[:2]],
            'weekend_worker': weekdays.get(5, 0) + weekdays.get(6, 0) > 
                             (sum(weekdays.values()) / 7 * 2)
        }
    
    def analyze_behavior_patterns(self, journal_entries: List[Dict]) -> Dict[str, Any]:
        """
        分析行为模式
        
        识别：
        - 任务类型偏好
        - 完成率趋势
        - 交互深度
        - 主动/被动比例
        """
        if not journal_entries:
            return {}
        
        type_counts = defaultdict(int)
        tag_counts = defaultdict(int)
        
        for entry in journal_entries:
            entry_type = entry.get('entry_type', 'unknown')
            type_counts[entry_type] += 1
            
            for tag in entry.get('tags', []):
                tag_counts[tag] += 1
        
        total = len(journal_entries)
        
        # 计算类型分布
        type_distribution = {
            k: round(v / total, 3) 
            for k, v in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        }
        
        # 识别主导模式
        dominant_type = max(type_counts.items(), key=lambda x: x[1])[0] if type_counts else None
        
        return {
            'type_distribution': type_distribution,
            'dominant_type': dominant_type,
            'top_tags': sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'variety_score': len(type_counts) / max(len(type_counts), 3),  # 多样性分数
            'action_ratio': type_counts.get('action', 0) / total if total > 0 else 0,
            'reflection_ratio': type_counts.get('thought', 0) / total if total > 0 else 0
        }
    
    def analyze_cognitive_patterns(self, journal_entries: List[Dict]) -> Dict[str, Any]:
        """
        分析认知模式
        
        识别：
        - 决策速度
        - 反思深度
        - 问题解决模式
        - 学习效率
        """
        if len(journal_entries) < 2:
            return {}
        
        # 按时间排序
        sorted_entries = sorted(
            journal_entries, 
            key=lambda x: x['timestamp']
        )
        
        # 计算条目间隔
        intervals = []
        for i in range(1, len(sorted_entries)):
            t1 = datetime.fromisoformat(sorted_entries[i-1]['timestamp'])
            t2 = datetime.fromisoformat(sorted_entries[i]['timestamp'])
            interval = (t2 - t1).total_seconds() / 60  # 分钟
            intervals.append(interval)
        
        if not intervals:
            return {}
        
        # 分析间隔分布
        short_intervals = [x for x in intervals if x < 10]  # < 10分钟
        long_intervals = [x for x in intervals if x > 60]    # > 1小时
        
        # 内容长度分析（作为反思深度的代理指标）
        content_lengths = [
            len(entry.get('content', '')) 
            for entry in journal_entries
        ]
        
        return {
            'avg_interval_minutes': round(np.mean(intervals), 2),
            'burst_ratio': len(short_intervals) / len(intervals),  # 爆发式工作比例
            'deep_work_ratio': len(long_intervals) / len(intervals),  # 深度工作比例
            'avg_content_length': round(np.mean(content_lengths), 2),
            'reflection_depth_score': min(1.0, np.mean(content_lengths) / 500),
            'consistency_score': 1.0 - (np.std(intervals) / (np.mean(intervals) + 1))
        }
    
    def analyze_sentiment_patterns(self, journal_entries: List[Dict]) -> Dict[str, Any]:
        """
        分析情绪模式
        
        识别：
        - 情绪波动周期
        - 压力信号
        - 满意度趋势
        """
        sentiments = []
        timestamps = []
        
        for entry in journal_entries:
            sentiment = entry.get('sentiment')
            if sentiment is not None:
                sentiments.append(sentiment)
                timestamps.append(datetime.fromisoformat(entry['timestamp']))
        
        if not sentiments:
            return {}
        
        # 计算趋势
        if len(sentiments) >= 7:
            first_week = np.mean(sentiments[:7])
            last_week = np.mean(sentiments[-7:])
            trend = last_week - first_week
        else:
            trend = 0
        
        # 计算波动
        volatility = np.std(sentiments)
        
        return {
            'avg_sentiment': round(np.mean(sentiments), 3),
            'sentiment_volatility': round(volatility, 3),
            'trend': 'improving' if trend > 0.1 else 'declining' if trend < -0.1 else 'stable',
            'positive_ratio': sum(1 for s in sentiments if s > 0) / len(sentiments),
            'stress_signals': sum(1 for s in sentiments if s < -0.5),
            'high_satisfaction_days': sum(1 for s in sentiments if s > 0.7)
        }
    
    def detect_milestones(self, journal_entries: List[Dict], 
                         user_id: str) -> List[Dict[str, Any]]:
        """
        检测里程碑
        
        识别：
        - 连续记录天数
        - 重大突破
        - 习惯养成
        """
        milestones = []
        
        # 检测连续记录
        dates = set()
        for entry in journal_entries:
            ts = datetime.fromisoformat(entry['timestamp'])
            dates.add(ts.date())
        
        sorted_dates = sorted(dates)
        if len(sorted_dates) >= 7:
            milestones.append({
                'type': 'consistency',
                'title': '7天连续记录',
                'description': '连续7天保持记录习惯',
                'value': len(sorted_dates)
            })
        
        if len(sorted_dates) >= 30:
            milestones.append({
                'type': 'consistency',
                'title': '30天连续记录',
                'description': '连续30天保持记录习惯',
                'value': len(sorted_dates)
            })
        
        if len(sorted_dates) >= 100:
            milestones.append({
                'type': 'consistency',
                'title': '百日成就',
                'description': '连续100天保持记录习惯',
                'value': len(sorted_dates)
            })
        
        # 检测类型里程碑
        type_counts = defaultdict(int)
        for entry in journal_entries:
            type_counts[entry.get('entry_type', 'unknown')] += 1
        
        for entry_type, count in type_counts.items():
            if count >= 50:
                milestones.append({
                    'type': 'volume',
                    'title': f'{entry_type} 大师',
                    'description': f'累计记录 {count} 条 {entry_type} 类型条目',
                    'value': count
                })
        
        return milestones
    
    def generate_full_profile(self, user_id: str, 
                             journal_entries: List[Dict]) -> Dict[str, Any]:
        """
        生成完整的用户画像
        """
        profile = {
            'user_id': user_id,
            'generated_at': datetime.now().isoformat(),
            'analysis_period': {
                'entry_count': len(journal_entries),
                'start_date': min(
                    (e['timestamp'] for e in journal_entries), 
                    default=None
                ),
                'end_date': max(
                    (e['timestamp'] for e in journal_entries),
                    default=None
                )
            },
            'patterns': {
                'time': self.analyze_time_patterns(journal_entries),
                'behavior': self.analyze_behavior_patterns(journal_entries),
                'cognitive': self.analyze_cognitive_patterns(journal_entries),
                'sentiment': self.analyze_sentiment_patterns(journal_entries)
            },
            'milestones': self.detect_milestones(journal_entries, user_id)
        }
        
        # 计算总体模式分数
        confidence = self._calculate_confidence(profile['patterns'])
        profile['confidence'] = confidence
        
        return profile
    
    def _calculate_confidence(self, patterns: Dict) -> float:
        """计算模式可信度"""
        scores = []
        
        if patterns.get('time'):
            scores.append(patterns['time'].get('regularity_score', 0))
        
        if patterns.get('behavior'):
            scores.append(patterns['behavior'].get('variety_score', 0))
        
        if patterns.get('cognitive'):
            scores.append(patterns['cognitive'].get('consistency_score', 0))
        
        return round(np.mean(scores), 3) if scores else 0.5
    
    def save_profile(self, profile: Dict[str, Any]):
        """保存用户画像"""
        with sqlite3.connect(self.db_path) as conn:
            # 保存统计
            conn.execute("""
                INSERT OR REPLACE INTO pattern_stats 
                (user_id, total_patterns, last_analysis, profile_summary)
                VALUES (?, ?, ?, ?)
            """, (
                profile['user_id'],
                len(profile.get('milestones', [])),
                datetime.now().isoformat(),
                json.dumps(profile['patterns'], ensure_ascii=False)
            ))
            
            conn.commit()
    
    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户画像统计"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM pattern_stats WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if row:
                return {
                    'user_id': row[0],
                    'total_patterns': row[1],
                    'last_analysis': row[2],
                    'profile_summary': json.loads(row[3]) if row[3] else {}
                }
            
            return None
    
    def compare_profiles(self, profile1: Dict, profile2: Dict) -> Dict[str, Any]:
        """
        比较两个用户画像（用于团队分析）
        """
        similarities = {}
        differences = {}
        
        # 比较时间模式
        time1 = profile1.get('patterns', {}).get('time', {})
        time2 = profile2.get('patterns', {}).get('time', {})
        
        if time1.get('peak_hours') and time2.get('peak_hours'):
            common_hours = set(time1['peak_hours']) & set(time2['peak_hours'])
            if common_hours:
                similarities['common_peak_hours'] = list(common_hours)
            else:
                differences['peak_hours'] = {
                    'user1': time1['peak_hours'],
                    'user2': time2['peak_hours']
                }
        
        # 比较行为模式
        behavior1 = profile1.get('patterns', {}).get('behavior', {})
        behavior2 = profile2.get('patterns', {}).get('behavior', {})
        
        if behavior1.get('dominant_type') == behavior2.get('dominant_type'):
            similarities['dominant_type'] = behavior1['dominant_type']
        else:
            differences['dominant_type'] = {
                'user1': behavior1.get('dominant_type'),
                'user2': behavior2.get('dominant_type')
            }
        
        return {
            'similarities': similarities,
            'differences': differences,
            'compatibility_score': len(similarities) / (len(similarities) + len(differences) + 0.001)
        }
