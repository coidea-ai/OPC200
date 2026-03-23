# OPC200 - 洞察生成模块
# 基于用户数据生成个性化洞察和建议

import os
import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Insight:
    """洞察数据结构"""
    id: str
    user_id: str
    category: str  # productivity, wellbeing, learning, collaboration
    title: str
    description: str
    evidence: List[Dict[str, Any]]
    recommendations: List[str]
    confidence: float
    priority: str  # high, medium, low
    generated_at: datetime
    expires_at: Optional[datetime] = None
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'user_id': self.user_id,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'evidence': self.evidence,
            'recommendations': self.recommendations,
            'confidence': self.confidence,
            'priority': self.priority,
            'generated_at': self.generated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'acknowledged': self.acknowledged
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Insight':
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            category=data['category'],
            title=data['title'],
            description=data['description'],
            evidence=data.get('evidence', []),
            recommendations=data.get('recommendations', []),
            confidence=data['confidence'],
            priority=data['priority'],
            generated_at=datetime.fromisoformat(data['generated_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            acknowledged=data.get('acknowledged', False)
        )


class InsightEngine:
    """
    洞察引擎
    
    基于用户日志和行为模式，生成个性化洞察和建议。
    
    洞察类别：
    - productivity: 效率优化建议
    - wellbeing: 工作生活平衡
    - learning: 学习成长建议
    - collaboration: 协作优化
    """
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: 洞察数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_db()
    
    def _ensure_db(self):
        """确保数据库结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    evidence TEXT,
                    recommendations TEXT,
                    confidence REAL NOT NULL,
                    priority TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    expires_at TEXT,
                    acknowledged INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_category 
                ON insights(user_id, category)
            """)
            
            conn.commit()
    
    def generate_insights(self, 
                         user_id: str,
                         journal_entries: List[Dict],
                         pattern_profile: Dict) -> List[Insight]:
        """
        生成用户洞察
        
        Args:
            user_id: 用户ID
            journal_entries: 日志条目
            pattern_profile: 模式画像
            
        Returns:
            洞察列表
        """
        insights = []
        
        # 生产效率洞察
        productivity_insights = self._analyze_productivity(
            user_id, journal_entries, pattern_profile
        )
        insights.extend(productivity_insights)
        
        # 健康平衡洞察
        wellbeing_insights = self._analyze_wellbeing(
            user_id, journal_entries, pattern_profile
        )
        insights.extend(wellbeing_insights)
        
        # 学习成长洞察
        learning_insights = self._analyze_learning(
            user_id, journal_entries, pattern_profile
        )
        insights.extend(learning_insights)
        
        # 保存洞察
        for insight in insights:
            self._save_insight(insight)
        
        return insights
    
    def _analyze_productivity(self, user_id: str,
                             entries: List[Dict],
                             profile: Dict) -> List[Insight]:
        """分析生产效率"""
        insights = []
        
        time_patterns = profile.get('patterns', {}).get('time', {})
        cognitive_patterns = profile.get('patterns', {}).get('cognitive', {})
        
        # 洞察1: 高效时段发现
        if time_patterns.get('peak_hours'):
            insights.append(Insight(
                id=f"{user_id}_prod_peak_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                category='productivity',
                title='发现你的高效时段',
                description=f"数据显示你在 {time_patterns['peak_hours']} 时段最为活跃和高效。",
                evidence=[{
                    'type': 'time_distribution',
                    'data': time_patterns.get('peak_hours', [])
                }],
                recommendations=[
                    f"将重要任务安排在 {time_patterns['peak_hours'][0]}:00 前后",
                    '避免在低效时段安排深度工作',
                    '使用番茄工作法强化高效时段'
                ],
                confidence=time_patterns.get('regularity_score', 0.7),
                priority='high' if time_patterns.get('regularity_score', 0) > 0.7 else 'medium',
                generated_at=datetime.now()
            ))
        
        # 洞察2: 深度工作比例
        deep_work_ratio = cognitive_patterns.get('deep_work_ratio', 0)
        if deep_work_ratio < 0.2:
            insights.append(Insight(
                id=f"{user_id}_prod_deep_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                category='productivity',
                title='增加深度工作时间',
                description='你的工作中断频率较高，建议增加深度工作时段。',
                evidence=[{
                    'type': 'deep_work_ratio',
                    'value': deep_work_ratio
                }],
                recommendations=[
                    '每天安排至少2小时的深度工作时段',
                    '关闭通知，减少干扰',
                    '使用"勿扰模式"保护专注时间'
                ],
                confidence=0.75,
                priority='medium',
                generated_at=datetime.now()
            ))
        
        return insights
    
    def _analyze_wellbeing(self, user_id: str,
                          entries: List[Dict],
                          profile: Dict) -> List[Insight]:
        """分析健康平衡"""
        insights = []
        
        sentiment_patterns = profile.get('patterns', {}).get('sentiment', {})
        time_patterns = profile.get('patterns', {}).get('time', {})
        
        # 洞察1: 情绪波动
        volatility = sentiment_patterns.get('sentiment_volatility', 0)
        if volatility > 0.5:
            insights.append(Insight(
                id=f"{user_id}_wellbeing_mood_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                category='wellbeing',
                title='情绪波动较大',
                description='近期你的情绪波动较为明显，建议关注压力管理。',
                evidence=[{
                    'type': 'volatility',
                    'value': volatility
                }],
                recommendations=[
                    '建立固定的休息和放松时间',
                    '记录情绪触发因素，寻找规律',
                    '考虑进行正念冥想练习'
                ],
                confidence=min(volatility, 0.9),
                priority='high',
                generated_at=datetime.now()
            ))
        
        # 洞察2: 工作生活平衡
        if time_patterns.get('weekend_worker'):
            insights.append(Insight(
                id=f"{user_id}_wellbeing_balance_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                category='wellbeing',
                title='注意工作边界',
                description='你在周末的工作活跃度较高，可能需要注意休息。',
                evidence=[{
                    'type': 'weekend_activity',
                    'weekend_worker': True
                }],
                recommendations=[
                    '设定明确的"离线"时间',
                    '周末安排一些与工作无关的活动',
                    '考虑使用"数字安息日"'
                ],
                confidence=0.7,
                priority='medium',
                generated_at=datetime.now()
            ))
        
        # 洞察3: 睡眠模式（如果检测到夜间工作）
        peak_hours = time_patterns.get('peak_hours', [])
        if peak_hours and peak_hours[0] < 6:
            insights.append(Insight(
                id=f"{user_id}_wellbeing_sleep_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                category='wellbeing',
                title='关注睡眠质量',
                description='凌晨时段仍有工作记录，建议关注作息规律。',
                evidence=[{
                    'type': 'late_night_activity',
                    'peak_hours': peak_hours
                }],
                recommendations=[
                    '设定最晚工作时间',
                    '睡前1小时避免屏幕',
                    '建立固定的睡前仪式'
                ],
                confidence=0.65,
                priority='medium',
                generated_at=datetime.now()
            ))
        
        return insights
    
    def _analyze_learning(self, user_id: str,
                         entries: List[Dict],
                         profile: Dict) -> List[Insight]:
        """分析学习成长"""
        insights = []
        
        behavior_patterns = profile.get('patterns', {}).get('behavior', {})
        
        # 洞察1: 学习模式
        reflection_ratio = behavior_patterns.get('reflection_ratio', 0)
        if reflection_ratio < 0.1:
            insights.append(Insight(
                id=f"{user_id}_learning_reflect_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                category='learning',
                title='增加反思记录',
                description='你的行动记录很多，但反思记录较少。增加反思有助于更快成长。',
                evidence=[{
                    'type': 'reflection_ratio',
                    'value': reflection_ratio
                }],
                recommendations=[
                    '每天结束前花5分钟回顾当日收获',
                    '记录失败经验和教训',
                    '定期回顾和整理过去的记录'
                ],
                confidence=0.8,
                priority='medium',
                generated_at=datetime.now()
            ))
        
        # 洞察2: 习惯养成
        milestones = profile.get('milestones', [])
        consistency_milestones = [m for m in milestones if m.get('type') == 'consistency']
        
        if consistency_milestones:
            latest = consistency_milestones[-1]
            insights.append(Insight(
                id=f"{user_id}_learning_habit_{datetime.now().strftime('%Y%m%d')}",
                user_id=user_id,
                category='learning',
                title=f'🎉 {latest["title"]}',
                description=f'{latest["description"]}。持续记录是进步的基础。',
                evidence=[{
                    'type': 'milestone',
                    'data': latest
                }],
                recommendations=[
                    '继续保持这个好习惯',
                    '考虑增加新的微习惯',
                    '回顾过去的记录，发现进步'
                ],
                confidence=0.95,
                priority='low',
                generated_at=datetime.now()
            ))
        
        return insights
    
    def _save_insight(self, insight: Insight):
        """保存洞察"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO insights 
                (id, user_id, category, title, description, evidence,
                 recommendations, confidence, priority, generated_at, expires_at, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                insight.id,
                insight.user_id,
                insight.category,
                insight.title,
                insight.description,
                json.dumps(insight.evidence),
                json.dumps(insight.recommendations),
                insight.confidence,
                insight.priority,
                insight.generated_at.isoformat(),
                insight.expires_at.isoformat() if insight.expires_at else None,
                int(insight.acknowledged)
            ))
            conn.commit()
    
    def get_insights(self, 
                    user_id: str,
                    category: Optional[str] = None,
                    acknowledged: Optional[bool] = None,
                    limit: int = 20) -> List[Insight]:
        """
        获取用户洞察
        
        Args:
            user_id: 用户ID
            category: 类别过滤
            acknowledged: 是否已确认
            limit: 数量限制
        """
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM insights WHERE user_id = ?"
            params = [user_id]
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            if acknowledged is not None:
                query += " AND acknowledged = ?"
                params.append(int(acknowledged))
            
            query += " ORDER BY generated_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            
            return [self._row_to_insight(row) for row in rows]
    
    def _row_to_insight(self, row) -> Insight:
        """数据库行转 Insight"""
        return Insight(
            id=row[0],
            user_id=row[1],
            category=row[2],
            title=row[3],
            description=row[4],
            evidence=json.loads(row[5]) if row[5] else [],
            recommendations=json.loads(row[6]) if row[6] else [],
            confidence=row[7],
            priority=row[8],
            generated_at=datetime.fromisoformat(row[9]),
            expires_at=datetime.fromisoformat(row[10]) if row[10] else None,
            acknowledged=bool(row[11])
        )
    
    def acknowledge_insight(self, insight_id: str) -> bool:
        """标记洞察为已确认"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE insights SET acknowledged = 1 WHERE id = ?",
                (insight_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def generate_daily_digest(self, user_id: str) -> Dict[str, Any]:
        """
        生成每日洞察摘要
        
        这是每天早上推送给用户的核心内容
        """
        # 获取最近的高优先级洞察
        recent_insights = self.get_insights(
            user_id=user_id,
            acknowledged=False,
            limit=5
        )
        
        # 按类别分组
        by_category = {}
        for insight in recent_insights:
            if insight.category not in by_category:
                by_category[insight.category] = []
            by_category[insight.category].append(insight)
        
        # 生成摘要
        digest = {
            'generated_at': datetime.now().isoformat(),
            'total_insights': len(recent_insights),
            'high_priority': [i.to_dict() for i in recent_insights if i.priority == 'high'],
            'summary': self._generate_digest_summary(recent_insights),
            'action_items': self._extract_action_items(recent_insights),
            'categories': {
                cat: [i.to_dict() for i in items]
                for cat, items in by_category.items()
            }
        }
        
        return digest
    
    def _generate_digest_summary(self, insights: List[Insight]) -> str:
        """生成摘要文本"""
        if not insights:
            return "今天没有新的洞察。继续保持良好的记录习惯！"
        
        categories = set(i.category for i in insights)
        high_priority = [i for i in insights if i.priority == 'high']
        
        summary_parts = []
        
        if high_priority:
            summary_parts.append(f"有 {len(high_priority)} 个高优先级洞察需要你关注")
        
        if 'wellbeing' in categories:
            summary_parts.append("健康方面有一些发现")
        
        if 'productivity' in categories:
            summary_parts.append("效率方面有优化建议")
        
        return "。".join(summary_parts) if summary_parts else "有一些有趣的发现"
    
    def _extract_action_items(self, insights: List[Insight]) -> List[str]:
        """提取行动项"""
        actions = []
        
        for insight in insights:
            if insight.recommendations:
                # 取最高优先级的建议
                actions.append(insight.recommendations[0])
        
        return actions[:3]  # 最多3个行动项
    
    def cleanup_old_insights(self, days: int = 30):
        """清理过期洞察"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM insights WHERE generated_at < ? AND acknowledged = 1",
                (cutoff,)
            )
            conn.commit()


class RecommendationEngine:
    """
    推荐引擎
    
    基于用户画像和当前上下文，生成实时建议
    """
    
    def __init__(self, insight_engine: InsightEngine):
        self.insight_engine = insight_engine
    
    def get_recommendations(self, 
                           user_id: str,
                           context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取上下文相关建议
        
        Args:
            user_id: 用户ID
            context: 当前上下文（时间、状态、最近活动等）
        """
        recommendations = []
        
        hour = datetime.now().hour
        
        # 基于时间的建议
        if 6 <= hour < 9:
            recommendations.append({
                'type': 'time_based',
                'title': '温和启动',
                'content': '早上好！建议先回顾今日优先事项，再开始工作。',
                'priority': 'low'
            })
        
        elif 12 <= hour < 14:
            recommendations.append({
                'type': 'time_based',
                'title': '午间休息',
                'content': '午休时间到了，建议放松一下大脑。',
                'priority': 'medium'
            })
        
        elif 18 <= hour < 20:
            recommendations.append({
                'type': 'time_based',
                'title': '日终总结',
                'content': '工作即将结束，建议记录今天的收获和明天的计划。',
                'priority': 'medium'
            })
        
        # 基于上下文状态的额外建议
        if context.get('streak_days', 0) > 7:
            recommendations.append({
                'type': 'achievement',
                'title': f'🔥 {context["streak_days"]} 天连胜',
                'content': '你的记录习惯保持得很好，继续保持！',
                'priority': 'low'
            })
        
        return recommendations
