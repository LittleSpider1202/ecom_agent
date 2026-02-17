# -*- coding: utf-8 -*-
"""NocoDB REST API v2 客户端 (影刀环境)

Python 3.7 兼容，仅依赖 stdlib (urllib)。
影刀脚本通过此模块将采集数据写入 NocoDB。

用法:
    from nocodb_client import NocoDBClient

    client = NocoDBClient("http://192.168.3.100:8080", "your-api-token")
    # 确保表存在
    table = client.ensure_table(base_id, "达人作品", [
        {"column_name": "视频链接", "uidt": "URL"},
        {"column_name": "点赞数", "uidt": "Number"},
    ])
    # 写入记录
    client.create_records(table["id"], [
        {"视频链接": "https://...", "点赞数": 1234},
    ])

NocoDB v2 API:
    认证: xc-token header
    Meta: /api/v2/meta/...
    Data: /api/v2/meta/tables/{tableId}/records
"""
import json
import urllib.request
import urllib.error

# NocoDB UI Data Types
UIDT_TEXT = "SingleLineText"
UIDT_LONG_TEXT = "LongText"
UIDT_NUMBER = "Number"
UIDT_DATETIME = "DateTime"
UIDT_URL = "URL"

# 采集字段 label → NocoDB uidt 映射
LABEL_UIDT_MAP = {
    "视频链接": UIDT_URL,
    "发布时间": UIDT_DATETIME,
    "封面标题": UIDT_TEXT,
    "点赞数": UIDT_NUMBER,
    "收藏数": UIDT_NUMBER,
    "转发数": UIDT_NUMBER,
    "评论数": UIDT_NUMBER,
    "视频封面图": UIDT_URL,
    "视频时长": UIDT_NUMBER,
    "合拍/贴纸标签": UIDT_TEXT,
}


class NocoDBClient(object):
    """NocoDB REST API v2 客户端"""

    def __init__(self, base_url, api_token, print_fn=None):
        # type: (str, str, ...) -> None
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.log = print_fn or print

    def _request(self, method, path, body=None):
        # type: (str, str, ...) -> ...
        """发送 HTTP 请求"""
        url = "{}{}".format(self.base_url, path)
        headers = {
            "xc-token": self.api_token,
            "Content-Type": "application/json",
        }

        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        try:
            resp = opener.open(req, timeout=30)
            raw = resp.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
        except urllib.error.HTTPError as e:
            error_body = ""
            if e.fp:
                try:
                    error_body = e.fp.read().decode("utf-8")
                except Exception:
                    pass
            self.log("[NocoDB] API error: {} {} - {}".format(e.code, e.reason, error_body))
            raise RuntimeError("NocoDB API {}: {}".format(e.code, error_body))
        except urllib.error.URLError as e:
            self.log("[NocoDB] Connection error: {}".format(e.reason))
            raise RuntimeError("NocoDB connection failed: {}".format(e.reason))

    # ==================== Base / Table ====================

    def list_bases(self):
        """列出所有 bases"""
        result = self._request("GET", "/api/v2/meta/bases")
        return result.get("list", [])

    def list_tables(self, base_id):
        """列出 base 下的所有表"""
        result = self._request("GET", "/api/v2/meta/bases/{}/tables".format(base_id))
        return result.get("list", [])

    def create_table(self, base_id, table_name, columns):
        """创建表

        Args:
            base_id: NocoDB base ID (如 "p_xxx")
            table_name: 表名
            columns: [{"column_name": "...", "uidt": "SingleLineText"}, ...]
        """
        body = {
            "table_name": table_name,
            "columns": columns,
        }
        result = self._request("POST", "/api/v2/meta/bases/{}/tables".format(base_id), body)
        self.log("[NocoDB] Table created: {} -> {}".format(table_name, result.get("id", "")))
        return result

    def find_table_by_name(self, base_id, table_name):
        """按名称查找表，返回 None 或 table dict"""
        tables = self.list_tables(base_id)
        for t in tables:
            if t.get("title") == table_name:
                return t
        return None

    def ensure_table(self, base_id, table_name, columns):
        """确保表存在（不存在则创建）

        Returns:
            table dict (含 id, title)
        """
        existing = self.find_table_by_name(base_id, table_name)
        if existing:
            self.log("[NocoDB] Table '{}' exists: {}".format(table_name, existing.get("id", "")))
            return existing
        return self.create_table(base_id, table_name, columns)

    # ==================== 记录操作 ====================

    def create_records(self, table_id, records):
        """批量创建记录

        Args:
            table_id: 表 ID (如 "m_xxx")
            records: [{列名: 值}, ...]

        Returns:
            创建结果
        """
        if not records:
            return []
        result = self._request(
            "POST",
            "/api/v2/meta/tables/{}/records".format(table_id),
            records,
        )
        self.log("[NocoDB] {} records inserted into {}".format(len(records), table_id))
        return result

    # ==================== 辅助 ====================

    def test_connection(self):
        """测试连接"""
        try:
            bases = self.list_bases()
            return {"success": True, "bases": len(bases)}
        except Exception as e:
            return {"success": False, "error": str(e)}


def build_columns(field_labels):
    """根据字段 label 列表构建 NocoDB 列定义

    Args:
        field_labels: ["视频链接", "点赞数", ...]

    Returns:
        [{"column_name": "视频链接", "uidt": "URL"}, ...]
    """
    columns = []
    for label in field_labels:
        uidt = LABEL_UIDT_MAP.get(label, UIDT_TEXT)
        columns.append({"column_name": label, "uidt": uidt})
    return columns
