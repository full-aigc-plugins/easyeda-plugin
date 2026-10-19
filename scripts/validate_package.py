"""离线验证宿主配置、原生 MCP 地址和自包含技能快照。"""
import hashlib
import importlib.util
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT):
    def read(name):
        return json.loads((root / name).read_text())

    manifest = read('plugin.json')
    schema = read('schemas/plugin.schema.json')
    if set(manifest) - set(schema['properties']) or not set(schema['required']) <= set(manifest):
        raise ValueError('portable manifest 字段不符合固定 schema')
    if manifest['$schema'] != schema['properties']['$schema']['const']:
        raise ValueError('portable manifest schema 不一致')
    version = manifest['version']
    ui = manifest['extensions']['com.openai']['interface']
    if manifest['name'] != 'easyeda' or ui['displayName'] != 'EasyEDA':
        raise ValueError('插件标识或显示名称错误')
    for name in ['.codex-plugin/plugin.json', '.claude-plugin/plugin.json', '.zcode-plugin/plugin.json']:
        native = read(name)
        if native['name'] != 'easyeda' or native['version'] != version or native['skills'] != './skills/':
            raise ValueError('宿主 manifest 不一致：' + name)
    if read('.codex-plugin/plugin.json')['interface'] != ui:
        raise ValueError('Codex UI 与 portable 扩展不一致')
    if read('.zcode-plugin/plugin.json')['displayName'] != 'EasyEDA':
        raise ValueError('ZCode 显示名称错误')
    endpoints = []
    for name, expected in [('mcp.json', 'streamable-http'), ('.mcp.json', 'http'),
                           ('.codex-plugin/mcp.json', None)]:
        servers = read(name)['mcpServers']
        if set(servers) != {'easyeda-native'}:
            raise ValueError('默认必须只连接客户端内置 MCP')
        config = servers['easyeda-native']
        if config.get('type') != expected:
            raise ValueError('宿主 MCP 类型不匹配：' + name)
        endpoints.append(config['url'])
    if len(set(endpoints)) != 1:
        raise ValueError('三个宿主 MCP 地址不一致')
    helper = root / 'skills/easyeda-mcp-setup/scripts/native_mcp.py'
    spec = importlib.util.spec_from_file_location('easyeda_native_check', helper)
    native_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native_module)
    native_module.validate_endpoint(endpoints[0])
    for key in ['logo', 'logoDark', 'composerIcon', 'composerIconDark']:
        image = (root / ui[key]).resolve()
        if not image.is_relative_to(root.resolve()) or not image.is_file():
            raise ValueError('品牌图片不可用')
    image = root / 'assets/official-logo.png'
    if image.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('品牌图片不是 PNG')
    if hashlib.sha256(image.read_bytes()).hexdigest() != read('docs/brand-source.json')['sha256']:
        raise ValueError('品牌图片与来源摘要不一致')
    market = read('.agents/plugins/marketplace.json')['plugins'][0]
    if market['name'] != 'easyeda' or market['source'] != {'source': 'local', 'path': './'}:
        raise ValueError('本地 Codex marketplace 应定位到插件根目录')
    companion = read('docs/eda-extension.json')
    extension = (root / companion['path']).resolve()
    if not extension.is_relative_to(root.resolve()) or extension.is_symlink() or not extension.is_file():
        raise ValueError('EDA 扩展安装包路径错误')
    if hashlib.sha256(extension.read_bytes()).hexdigest() != companion['sha256']:
        raise ValueError('EDA 扩展安装包摘要不一致')
    with zipfile.ZipFile(extension) as archive:
        if archive.testzip() is not None:
            raise ValueError('EDA 扩展 ZIP CRC 错误')
        config = json.loads(archive.read('extension.json'))
        if config['uuid'] != companion['uuid'] or config['version'] != companion['version']:
            raise ValueError('EDA 扩展版本或 UUID 不一致')
    snapshot = read('skill-snapshot.json')
    for record in snapshot['files']:
        path = root / record['path']
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('快照路径越界')
        if hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('快照内容不一致：' + record['path'])
    spec = importlib.util.spec_from_file_location('easyeda_skills_check', root / 'scripts/validate_skills.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {**module.validate(root), 'displayName': ui['displayName'],
            'nativeEndpoint': endpoints[0], 'snapshotFiles': len(snapshot['files'])}


if __name__ == '__main__':
    print(json.dumps(validate(), ensure_ascii=False))
