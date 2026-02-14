"""流程定义 API"""
import re

from fastapi import APIRouter, HTTPException

from flows.registry import get_flow, get_all_flows, FlowRegistry

router = APIRouter(prefix="/flows", tags=["flows"])


def _extract_refs(obj) -> set[str]:
    """递归扫描对象中所有 {{ key }} 引用，返回 key 集合"""
    refs = set()
    if isinstance(obj, str):
        refs.update(re.findall(r'\{\{\s*(\w+)', obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            refs.update(_extract_refs(v))
    elif isinstance(obj, list):
        for item in obj:
            refs.update(_extract_refs(item))
    return refs


def _extract_node_params(node: dict, param_by_key: dict, param_order: list[str]) -> list:
    """根据节点 inputs 中引用的 {{ key }} 匹配对应的 parameter 定义，按 YAML 定义顺序返回"""
    node_inputs = node.get("inputs") or {}
    refs = _extract_refs(node_inputs)
    return [param_by_key[key] for key in param_order if key in refs and key in param_by_key]


def transform_flow_for_frontend(flow: dict) -> dict:
    """将 YAML 格式的流程定义转换为前端期望的格式

    YAML 格式:
    - id, name, version, parameters, variables, nodes, connections

    前端格式:
    - id, type, name, version, steps (with params), stepGroups

    注意：
    - parameters: 用户表单输入，展示给用户
    - node.inputs: 执行时的输入，不展示给用户
    """
    if not flow:
        return None

    # 收集用户参数（仅来自 parameters），按 key 索引，保留定义顺序
    param_by_key = {}
    param_order = []
    for param_def in flow.get("parameters", []):
        input_type = param_def.get("input", "input")
        default_val = param_def.get("default")
        if default_val is None:
            default_val = [] if input_type == "checkbox" else ""
        param = {
            "key": param_def.get("key"),
            "label": param_def.get("label", param_def.get("key")),
            "type": input_type,
            "options": param_def.get("options", []),
            "default": default_val,
            "required": param_def.get("required", False),
            "placeholder": param_def.get("placeholder", ""),
        }
        if param_def.get("row") is not None:
            param["row"] = param_def["row"]
            param["span"] = param_def.get("span", 12)
        if param_def.get("input") == "file":
            param["accept"] = param_def.get("accept", "")
        if param_def.get("showWhen"):
            param["showWhen"] = param_def["showWhen"]
        param_by_key[param["key"]] = param
        param_order.append(param["key"])

    # 转换 nodes 为 steps
    # 先收集每个节点引用的参数
    nodes = flow.get("nodes", [])
    node_param_lists = []
    for node in nodes:
        node_params = _extract_node_params(node, param_by_key, param_order)
        node_param_lists.append(node_params)

    # 参数去重：同一个参数被多个节点引用时，只在最后一个节点展示
    # 这样前端展示节点可以拆分参数分组，而执行节点保留完整 inputs
    seen_keys = set()
    for i in range(len(nodes) - 1, -1, -1):
        deduped = [p for p in node_param_lists[i] if p["key"] not in seen_keys]
        seen_keys.update(p["key"] for p in deduped)
        node_param_lists[i] = deduped

    steps = []
    for i, node in enumerate(nodes):
        step = {
            "id": node.get("id"),
            "name": node.get("name"),
            "type": node.get("type", "system"),
            "category": node.get("category", "execute"),
            "description": node.get("name"),
            "handler": node.get("config", {}).get("script"),
            "params": node_param_lists[i]
        }

        # 如果是 manual 类型，添加 prompt 信息
        if node.get("type") == "manual":
            inputs = node.get("inputs") or {}
            step["title"] = inputs.get("title", "人工确认")
            step["prompt"] = inputs.get("prompt", "请确认操作")
            step["actions"] = inputs.get("actions", [])
            # 传递 config.fields（运行时表单字段）
            config_fields = node.get("config", {}).get("fields")
            if config_fields:
                step["runtimeFields"] = config_fields

        steps.append(step)

    return {
        "id": flow.get("id"),
        "type": flow.get("id"),
        "name": flow.get("name"),
        "version": flow.get("version", 1),
        "description": flow.get("description", ""),
        "trigger": flow.get("trigger", {}).get("type", "manual"),
        "steps": steps,
        "stepGroups": [],
        "_raw": flow
    }


@router.get("")
async def list_flows():
    """获取所有流程定义"""
    flows = get_all_flows()
    # 转换为前端格式
    transformed = [transform_flow_for_frontend(f) for f in flows]
    return {"flows": transformed}


@router.get("/{flow_id}")
async def get_flow_by_id(flow_id: str, raw: bool = False):
    """获取单个流程定义

    Args:
        flow_id: 流程ID
        raw: 是否返回原始 YAML 格式（默认返回前端格式）
    """
    flow = get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")

    if raw:
        return flow
    return transform_flow_for_frontend(flow)


@router.post("/reload")
async def reload_flows():
    """热加载流程定义（无需重启服务）"""
    loaded = FlowRegistry.reload()
    return {
        "success": True,
        "loaded": loaded,
        "count": len(loaded) if loaded else 0
    }
