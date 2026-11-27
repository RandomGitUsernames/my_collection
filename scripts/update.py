#!/usr/bin/env python3
"""Create an AltStore Classic feed without executing or republishing upstream IPAs."""
import datetime as dt
import hashlib
import json
import os
import pathlib
import plistlib
import re
import subprocess
import tempfile
import urllib.request
import urllib.parse
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAX_IPA = 600 * 1024 * 1024
MAX_PLIST = 2 * 1024 * 1024
MAX_EXEC = 350 * 1024 * 1024


def load(name, default=None):
    path = ROOT / name
    return json.loads(path.read_text()) if path.exists() else default


def save(name, value):
    path = ROOT / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(path)


def get_release(repo):
    assert re.fullmatch(r'[\w.-]+/[\w.-]+', repo)
    headers = {'User-Agent': 'personal-altstore-source', 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28'}
    if os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}/releases/latest', headers=headers)
    with urllib.request.urlopen(req, timeout=40) as r:
        result = json.load(r)
    if result.get('draft') or result.get('prerelease'):
        raise ValueError('Not a stable public release')
    return result


def choose_asset(project, release):
    assets = [a for a in release.get('assets', []) if a.get('state') == 'uploaded'
              and re.fullmatch(project['asset_regex'], a['name'])]
    if len(assets) != 1:
        raise ValueError(f'Expected one approved IPA variant, got {len(assets)}')
    asset = assets[0]
    u = urllib.parse.urlsplit(asset['browser_download_url'])
    if u.scheme != 'https' or u.netloc != 'github.com' or not u.path.startswith('/' + project['repo'] + '/releases/download/'):
        raise ValueError('Asset is not hosted under the approved project')
    if not 0 < asset['size'] <= MAX_IPA:
        raise ValueError('Invalid IPA size')
    return asset


def download(asset, target):
    sha = hashlib.sha256()
    count = 0
    request = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent':'personal-altstore-source'})
    # Never forward GitHub credentials to the asset CDN.
    with urllib.request.urlopen(request, timeout=120) as response, target.open('wb') as out:
        if urllib.parse.urlsplit(response.geturl()).scheme != 'https':
            raise ValueError('Non-HTTPS redirect')
        while chunk := response.read(1024 * 1024):
            count += len(chunk)
            if count > (MAX_IPA if asset.get('approximate_size') else min(MAX_IPA, asset['size'])):
                raise ValueError('Download exceeds expected size')
            sha.update(chunk)
            out.write(chunk)
    if not count or (not asset.get('approximate_size') and count != asset['size']):
        raise ValueError('Incomplete download')
    digest = 'sha256:' + sha.hexdigest()
    if asset.get('digest') and asset['digest'] != digest:
        raise ValueError('GitHub asset digest mismatch')
    return digest


def plist_from_zip(z, name):
    if z.getinfo(name).file_size > MAX_PLIST:
        raise ValueError('Oversized plist')
    value = plistlib.loads(z.read(name))
    if not isinstance(value, dict):
        raise ValueError('Invalid plist')
    return value


def codesign_entitlements(executable):
    # Inspection only. The untrusted executable is never launched.
    result = subprocess.run(['/usr/bin/codesign', '-d', '--entitlements', ':-', str(executable)],
                            capture_output=True, timeout=45)
    if result.returncode != 0:
        raise ValueError('Cannot inspect code signature; refusing to publish')
    if not result.stdout.strip():
        return {}
    return plistlib.loads(result.stdout)


def inspect_ipa(path, entitlement_reader=codesign_entitlements):
    with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory() as tmp:
        names = z.namelist()
        mains = [n for n in names if re.fullmatch(r'Payload/[^/]+\.app/Info\.plist', n)]
        if len(mains) != 1:
            raise ValueError('Expected exactly one main app')
        main = mains[0]
        root = main.rsplit('/', 1)[0] + '/'
        info = plist_from_zip(z, main)
        entitlements, privacy = set(), {}
        bundles = [main] + [n for n in names if n.startswith(root) and re.search(r'\.(?:app|appex)/Info\.plist$', n) and n != main]
        for i, name in enumerate(bundles):
            meta = plist_from_zip(z, name)
            for k, v in meta.items():
                if 'UsageDescription' in k and isinstance(v, str):
                    privacy[k] = v
            exe = meta.get('CFBundleExecutable', '')
            if not exe or '/' in exe or '\\' in exe or exe in ('.', '..'):
                raise ValueError('Invalid executable name')
            binary = name.rsplit('/', 1)[0] + '/' + exe
            if z.getinfo(binary).file_size > MAX_EXEC:
                raise ValueError('Oversized executable')
            target = pathlib.Path(tmp) / str(i)
            target.write_bytes(z.read(binary))
            entitlements.update(entitlement_reader(target).keys())
        return info, {'entitlements': sorted(entitlements), 'privacy': privacy}


def app_from_ipa(project, release, asset, info, permissions, digest):
    bundle = info['CFBundleIdentifier']
    if bundle != project['bundle_id']:
        raise ValueError(f'Unexpected bundle ID: {bundle}; review projects.json')
    version = {'version': str(info['CFBundleShortVersionString']), 'buildVersion': str(info['CFBundleVersion']),
               'date': release['published_at'], 'downloadURL': asset['browser_download_url'], 'size': asset['size'],
               'localizedDescription': f"Upstream release {release['tag_name']}. SHA-256: {digest.removeprefix('sha256:')}"}
    if info.get('MinimumOSVersion'):
        version['minOSVersion'] = str(info['MinimumOSVersion'])
    return {'name': project['name'], 'bundleIdentifier': bundle, 'developerName': project.get('publisher', project['repo'].split('/')[0]),
            'localizedDescription': f"Original project: https://github.com/{project['repo']}. Binary provider: {project.get('publisher', project['repo'])}. " + ("Community-packaged IPA, not an original developer build. " if project.get("community") else "") + "Not independently security audited.",
            'iconURL': 'https://github.com/' + project['repo'].split('/')[0] + '.png', 'category': project['category'],
            'versions': [version], 'appPermissions': permissions}


def news_item(project, release):
    tag = release['tag_name']
    caption = ('New upstream release. Open GitHub to review the changes.' if project['mode'] in ('ipa','feed')
               else 'New tweak release. Open GitHub to build your own IPA; no public IPA is supplied here.')
    return {'title': f"{project['name']}: {tag}"[:150],
            'identifier': project['id'] + '-' + str(release['id']), 'caption': caption,
            'date': release['published_at'], 'notify': True,
            'url': f"https://github.com/{project['repo']}/releases/tag/{urllib.parse.quote(tag, safe='')}"}


def validate(source):
    assert isinstance(source['name'], str) and source['name']
    assert isinstance(source['apps'], list) and isinstance(source['news'], list)
    for items, key in [(source['apps'], 'bundleIdentifier'), (source['news'], 'identifier')]:
        ids = [i[key] for i in items]
        if len(ids) != len(set(ids)):
            raise ValueError(f'Duplicate {key}')
    for app in source['apps']:
        assert all(isinstance(app[k], str) and app[k] for k in ('name','bundleIdentifier','developerName','localizedDescription','iconURL'))
        assert app['versions'] and isinstance(app['appPermissions'], dict)
        for v in app['versions']:
            assert all(isinstance(v[k], str) and v[k] for k in ('version','buildVersion','date','downloadURL'))
            assert v['size'] > 0 and urllib.parse.urlsplit(v['downloadURL']).scheme == 'https'
            dt.datetime.fromisoformat(v['date'].replace('Z', '+00:00'))
    for n in source['news']:
        assert all(isinstance(n[k], str) and n[k] for k in ('title','identifier','caption','date','url'))
        dt.datetime.fromisoformat(n['date'].replace('Z', '+00:00'))


def feed_asset(project, data):
    # Match both exact name and exact bundle identifier, never just one of them.
    matches = [a for a in data['apps'] if a.get('name') == project['feed_name'] and a.get('bundleIdentifier') == project['bundle_id']]
    if len(matches) != 1:
        raise ValueError(f'Expected one exact feed entry, got {len(matches)}')
    a = matches[0]
    v = a['versions'][0] if a.get('versions') else a
    url = v['downloadURL']
    u = urllib.parse.urlsplit(url)
    if u.scheme != 'https' or u.netloc != project['asset_host'] or not re.fullmatch(project['asset_path_regex'], u.path) or u.query or u.fragment:
        raise ValueError('Download URL is outside approved provider/path')
    date = v.get('date') or a['versionDate']
    if len(date) == 10: date += 'T00:00:00Z'
    dt.datetime.fromisoformat(date.replace('Z','+00:00'))
    size = v.get('size', a.get('size'))
    if not isinstance(size, int) or not 0 < size <= MAX_IPA:
        raise ValueError('Invalid reported IPA size')
    tag = str(v.get('version',a.get('version','unknown')))
    identity = hashlib.sha256(json.dumps([url,date,tag,size,v.get('localizedDescription'),a.get('localizedDescription')],sort_keys=True).encode()).hexdigest()
    return ({'id':identity,'tag_name':tag,'published_at':date},
            {'id':identity,'browser_download_url':url,'size':size,'updated_at':date,'approximate_size':True})


def get_feed(project):
    req=urllib.request.Request(project['feed'],headers={'User-Agent':'personal-altstore-source','Cache-Control':'no-cache'})
    with urllib.request.urlopen(req,timeout=45) as response:
        if urllib.parse.urlsplit(response.geturl()).netloc != 'raw.githubusercontent.com':
            raise ValueError('Unexpected feed redirect')
        data=response.read(12*1024*1024+1)
    if len(data)>12*1024*1024: raise ValueError('Feed too large')
    return feed_asset(project,json.loads(data))


def main():
    projects = load('projects.json')
    settings = load('settings.json', {'include_community':False})
    old = load('source.json', {'name':'Personal App Updates','identifier':'org.personalappupdates.source','apps':[],'news':[]})
    cache = load('asset-cache.json', {})
    old_apps = {a['bundleIdentifier']: a for a in old['apps']}
    news = {n['identifier']: n for n in old['news']}
    apps, status, next_cache = [], [], {}
    for p in projects:
        row = {'project': p['name'], 'repo': p['repo'], 'publisher':p.get('publisher',p['repo'])}
        release = None
        enabled = not p.get('community') or settings.get('include_community') is True
        try:
            if not enabled:
                release = get_release(p['repo'])
                row['status']='Community build disabled; personal IPA required'
                row['tag']=release['tag_name']
                item=news_item({**p,'mode':'watch'},release)
                news[item['identifier']]=item
                status.append(row); print(p['name'],row['status']); continue
            if p['mode']=='feed':
                release,asset = get_feed(p)
            else:
                release = get_release(p['repo'])
                asset = choose_asset(p,release)
            row.update(tag=release['tag_name'],mode=p['mode'])
            identity = [p['repo'], release['id'], asset['id'], asset.get('digest'), asset['size'], asset.get('updated_at'), p['bundle_id'],asset['browser_download_url']]
            previous = old_apps.get(p['bundle_id'])
            if previous and cache.get(p['id']) == identity:
                app=previous
            else:
                with tempfile.TemporaryDirectory() as tmp:
                    ipa = pathlib.Path(tmp) / 'app.ipa'
                    digest = download(asset, ipa)
                    info, permissions = inspect_ipa(ipa)
                    app = app_from_ipa(p, release, {**asset,'size':ipa.stat().st_size}, info, permissions, digest)
            apps.append(app); next_cache[p['id']]=identity
            row['status']='IPA listed; metadata inspected, not security audited'
            item=news_item(p,release)
            if p['mode']=='feed':
                item['url']=p['feed']; item['caption']='New build indexed from '+p['publisher']+'. Review source and permissions before installing.'
            news[item['identifier']]=item
            if previous and previous['versions'][0]['version'] == app['versions'][0]['version'] and previous['versions'][0]['buildVersion'] == app['versions'][0]['buildVersion'] and cache.get(p['id']) != identity:
                row['note']='Same version/build: AltStore may not offer Update. Check News.'
        except Exception as exc:
            row['status']='Check failed: '+str(exc)[:350]
            if enabled and p['bundle_id'] in old_apps and cache.get(p['id']):
                apps.append(old_apps[p['bundle_id']]); next_cache[p['id']]=cache[p['id']]
                row['note']='Previous validated listing retained; may be stale. New asset not published.'
        status.append(row); print(p['name'],row['status'])
    source={**old,'subtitle':'Selected developer and opt-in community builds','description':'Curated direct links; not a security audit. Community builds are labelled.','apps':apps,'news':sorted(news.values(),key=lambda n:n['date'],reverse=True)[:40]}
    validate(source)
    save('source.json',source); save('asset-cache.json',next_cache)
    save('status.json',{'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'projects':status,'installable_count':len(apps),'expected_count':sum(not p.get('community') or settings.get('include_community') is True for p in projects)})
    return int(any(r['status'].startswith('Check failed') for r in status))

if __name__=='__main__':
    raise SystemExit(main())
