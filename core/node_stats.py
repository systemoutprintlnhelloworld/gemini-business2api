"""节点统计追踪器"""
import json
import os
from typing import Dict, Literal


class NodeStatsTracker:
    """追踪节点的成功/风控/其他失败统计"""

    def __init__(self, stats_file: str = "data/node_stats.json"):
        self.stats_file = stats_file
        os.makedirs(os.path.dirname(stats_file), exist_ok=True)

    def record(self, node_name: str, result: Literal["success", "risk_control", "other"]) -> None:
        """记录节点结果"""
        stats = self._load_stats()
        if node_name not in stats:
            stats[node_name] = {"success": 0, "risk_control": 0, "other": 0}
        stats[node_name][result] = stats[node_name].get(result, 0) + 1
        self._save_stats(stats)

        # 同步更新节点数据库
        from core import node_manager
        nodes = node_manager.load_all_nodes()
        for node in nodes:
            if node.get("name") == node_name:
                if result == "success":
                    node["success"] = node.get("success", 0) + 1
                else:
                    node["fail"] = node.get("fail", 0) + 1
                node_manager.save_all_nodes(nodes)
                break

    def get_stats(self) -> Dict[str, Dict[str, int]]:
        """获取统计数据"""
        return self._load_stats()

    def get_chart_data(self) -> Dict:
        """返回 ECharts 格式数据（只显示有数据的节点）"""
        stats = self._load_stats()
        # 过滤出有数据的节点
        active_nodes = [
            name for name in stats.keys()
            if stats[name].get("success", 0) + stats[name].get("risk_control", 0) + stats[name].get("other", 0) > 0
        ]
        labels = [self._simplify_node_name(n) for n in active_nodes]
        return {
            "labels": labels,
            "datasets": [
                {"label": "成功", "data": [stats[n].get("success", 0) for n in active_nodes]},
                {"label": "风控", "data": [stats[n].get("risk_control", 0) for n in active_nodes]},
                {"label": "其他", "data": [stats[n].get("other", 0) for n in active_nodes]},
            ],
        }

    def _simplify_node_name(self, name: str) -> str:
        """简化节点名称: '🇭🇰 香港｜Hong Kong 03' -> '香港 03'"""
        import re
        # 提取中文地区名和数字
        match = re.search(r'[\u4e00-\u9fff]+.*?(\d+)', name)
        if match:
            # 提取emoji后的中文部分和数字
            parts = re.split(r'[｜|]', name)
            if parts:
                cn_part = re.sub(r'^[^\u4e00-\u9fff]*', '', parts[0]).strip()
                num = match.group(1)
                return f"{cn_part} {num}"
        return name

    def _load_stats(self) -> Dict:
        """加载统计数据"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_stats(self, stats: Dict) -> None:
        """保存统计数据"""
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
