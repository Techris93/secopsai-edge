from __future__ import annotations

import xml.etree.ElementTree as ET

from secopsai_agent.models import AssetObservation, ServiceObservation


def parse_nmap_xml(xml_text: str) -> list[AssetObservation]:
    root = ET.fromstring(xml_text)
    assets: list[AssetObservation] = []

    for host in root.findall("host"):
        status = host.find("status")
        if status is not None and status.attrib.get("state") not in {None, "up"}:
            continue

        ip = None
        mac = None
        vendor = None
        for address in host.findall("address"):
            addr_type = address.attrib.get("addrtype")
            if addr_type == "ipv4":
                ip = address.attrib.get("addr")
            elif addr_type == "mac":
                mac = address.attrib.get("addr")
                vendor = address.attrib.get("vendor")

        if not ip:
            continue

        hostname = None
        hostnames = host.find("hostnames")
        if hostnames is not None:
            first_hostname = hostnames.find("hostname")
            if first_hostname is not None:
                hostname = first_hostname.attrib.get("name")

        services: list[ServiceObservation] = []
        ports = host.find("ports")
        if ports is not None:
            for port_node in ports.findall("port"):
                state_node = port_node.find("state")
                state = state_node.attrib.get("state") if state_node is not None else None
                if state != "open":
                    continue
                service_node = port_node.find("service")
                services.append(
                    ServiceObservation(
                        port=int(port_node.attrib["portid"]),
                        protocol=port_node.attrib.get("protocol", "tcp"),
                        state=state,
                        name=service_node.attrib.get("name") if service_node is not None else None,
                        product=service_node.attrib.get("product")
                        if service_node is not None
                        else None,
                        version=service_node.attrib.get("version")
                        if service_node is not None
                        else None,
                    )
                )

        assets.append(
            AssetObservation(
                ip=ip,
                mac=mac,
                vendor=vendor,
                hostname=hostname,
                services=services,
                raw={"source": "nmap"},
            )
        )

    return assets
