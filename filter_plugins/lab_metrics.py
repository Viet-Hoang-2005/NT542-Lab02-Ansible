"""Script dùng để phân tích các chỉ số đo được từ router và phát hiện các xung đột."""

import ipaddress
import re


# Chuyển đổi giá trị thời gian sang mili giây
def _milliseconds(value):
    if not value:
        return None
    value = value.strip().lower().replace("µ", "u")
    if value.startswith("<"):
        return None
    units = {"ns": 0.000001, "us": 0.001, "ms": 1.0, "s": 1000.0}
    parts = re.findall(r"(\d+(?:\.\d+)?)(ns|us|ms|s)", value)
    if not parts or "".join(number + unit for number, unit in parts) != value:
        return None
    return round(sum(float(number) * units[unit] for number, unit in parts), 6)


# Phân tích kết quả ping và phát hiện lỗi
def parse_ping(text, platform):
    text = str(text or "")
    result = {
        "sent": None,
        "received": None,
        "loss_percent": None,
        "min_ms": None,
        "avg_ms": None,
        "max_ms": None,
        "warnings": [],
    }
    if platform == "linux":
        counts = re.search(
            r"(\d+) packets transmitted,\s*(\d+) (?:packets )?received,\s*([\d.]+)% packet loss",
            text,
        )
        rtt = re.search(
            r"(?:rtt|round-trip) min/avg/max/(?:mdev|stddev)\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/[\d.]+\s*ms",
            text,
        )
        if counts:
            result.update(
                sent=int(counts[1]),
                received=int(counts[2]),
                loss_percent=float(counts[3]),
            )
        if rtt:
            result.update(
                min_ms=float(rtt[1]), avg_ms=float(rtt[2]), max_ms=float(rtt[3])
            )
    elif platform == "routeros":
        counts = re.search(
            r"\bsent=(\d+)\s+received=(\d+)\s+packet-loss=([\d.]+)%", text
        )
        if counts:
            result.update(
                sent=int(counts[1]),
                received=int(counts[2]),
                loss_percent=float(counts[3]),
            )
        for key, output in [
            ("min-rtt", "min_ms"),
            ("avg-rtt", "avg_ms"),
            ("max-rtt", "max_ms"),
        ]:
            match = re.search(r"\b" + key + r"=([^\s]+)", text)
            if match:
                result[output] = _milliseconds(match[1])
    else:
        raise ValueError("Unsupported ping platform: " + str(platform))
    if result["sent"] is None:
        result["warnings"].append(
            "Ping summary was not available or could not be parsed."
        )
    elif result["received"] and any(
        result[key] is None for key in ("min_ms", "avg_ms", "max_ms")
    ):
        result["warnings"].append(
            "Round-trip times were not available or were not exact."
        )
    return result


# Tính phần trăm bộ nhớ đã sử dụng
def memory_used_percent(facts):
    try:
        total = float(facts["ansible_net_memtotal_mb"])
        free = float(facts["ansible_net_memfree_mb"])
        if total <= 0 or free < 0 or free > total:
            return None
        return round(100 * (total - free) / total, 2)
    except (KeyError, TypeError, ValueError):
        return None


# Lên kế hoạch trạng thái router
def plan_router_state(addresses, routes, interfaces, desired):
    """Reject ambiguous or conflicting entries and report required additions."""
    errors, actions = [], {}
    names = {str(item.get("name", "")) for item in interfaces}
    for name in ("ether1", desired["link_interface"], desired["loopback_interface"]):
        if name not in names:
            errors.append("Required interface is missing: " + name)
    for key, interface in [
        ("link_address", desired["link_interface"]),
        ("loopback_address", desired["loopback_interface"]),
    ]:
        target = ipaddress.ip_interface(desired[key])
        matched = []
        for item in addresses:
            try:
                existing = ipaddress.ip_interface(item.get("address", ""))
            except ValueError:
                errors.append("An existing address could not be parsed.")
                continue
            if existing.version != target.version or not existing.network.overlaps(
                target.network
            ):
                continue
            if existing == target and item.get("interface") == interface:
                matched.append(item)
            else:
                errors.append(
                    "Address conflict for "
                    + str(target)
                    + ": "
                    + str(item.get("address"))
                )
        if len(matched) > 1:
            errors.append("Duplicate address: " + str(target))
        actions[key] = not matched
    destination = desired["peer_loopback"] + "/32"
    matching_routes = [
        item for item in routes if item.get("dst-address") == destination
    ]
    if len(matching_routes) > 1:
        errors.append("Multiple routes already exist for " + destination)
    for route in matching_routes:
        if route.get("gateway") != desired["peer_gateway"]:
            errors.append(
                "Route conflict for " + destination + ": " + str(route.get("gateway"))
            )
    actions["route"] = not matching_routes
    return {"errors": errors, "actions": actions}


# Khai báo module được sử dụng để lọc dữ liệu từ router
class FilterModule:
    def filters(self):
        return {
            "lab_parse_ping": parse_ping,
            "lab_plan_router_state": plan_router_state,
            "lab_memory_used_percent": memory_used_percent,
        }
