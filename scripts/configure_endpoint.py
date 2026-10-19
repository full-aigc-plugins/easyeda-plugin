"""显式统一三个宿主配置中的原生 MCP 地址；不修改全局宿主配置。"""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure(endpoint, root=ROOT):
    spec = importlib.util.spec_from_file_location('native_endpoint', root / 'skills/easyeda-mcp-setup/scripts/native_mcp.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_endpoint(endpoint)
    changes = []
    for name in ['mcp.json', '.mcp.json', '.codex-plugin/mcp.json']:
        path = root / name
        data = json.loads(path.read_text())
        if data['mcpServers']['easyeda-native']['url'] != endpoint:
            data['mcpServers']['easyeda-native']['url'] = endpoint
            changes.append((path, json.dumps(data, ensure_ascii=False, indent=2) + '\n'))
    for path, content in changes:
        path.write_text(content)
    return {'ok': True, 'endpoint': endpoint, 'changed': len(changes)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('endpoint')
    print(json.dumps(configure(parser.parse_args().endpoint), ensure_ascii=False))
