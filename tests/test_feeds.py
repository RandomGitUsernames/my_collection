import unittest
from scripts.update import feed_asset, load, choose_asset
P = {p['id']:p for p in load('projects.json')}
def entry(p, url):
    return {'name':p['feed_name'],'bundleIdentifier':p['bundle_id'],'version':'1.2.3','versionDate':'2026-11-08','downloadURL':url,'size':1000}
class FeedTests(unittest.TestCase):
    def test_facebook_exact_variant(self):
        p=P['facebook-plus']; a=entry(p,'https://'+p['asset_host']+'/Facebook%20Plus%201.0.5%20%28FB%20586.0.0%29%20%5B%40ipavault%5D.ipa')
        r,asset=feed_asset(p,{'apps':[dict(a,name='Facebook (iQFace)'),a]})
        self.assertEqual(asset['browser_download_url'],a['downloadURL']); self.assertEqual(r['published_at'],'2026-11-08T00:00:00Z')
    def test_spotify_free_only(self):
        p=P['eeveespotify']; a=entry(p,'https://files.catbox.moe/79bhql.ipa')
        r,asset=feed_asset(p,{'apps':[dict(a,name=a['name']+'(PATCHED)',bundleIdentifier='com.spotify.client.patched'),a]})
        self.assertEqual(asset['browser_download_url'],a['downloadURL'])
    def test_youtube_music_version(self):
        p=P['ytmusicultimate']; a=entry(p,'https://github.com/mrdrvt99/YTMusicUltimate/releases/download/ytmu-ipa46/YTMusicUltimate_9.47.2_2.4.1.ipa')
        a['versions']=[{'version':'9.47.2','date':'2026-11-23T02:41:12Z','downloadURL':a['downloadURL'],'size':1000}]
        self.assertEqual(feed_asset(p,{'apps':[a]})[0]['tag_name'],'9.47.2')
    def test_duplicate_rejected(self):
        p=P['eeveespotify']; a=entry(p,'https://files.catbox.moe/79bhql.ipa')
        with self.assertRaises(ValueError): feed_asset(p,{'apps':[a,a]})
    def test_wrong_host_or_path(self):
        p=P['ytmusicultimate']
        for url in ('https://evil.example/x.ipa','https://github.com/other/repo/releases/download/a/x.ipa','http://github.com/mrdrvt99/YTMusicUltimate/releases/download/a/YTMusicUltimate_x.ipa'):
            with self.assertRaises(ValueError): feed_asset(p,{'apps':[entry(p,url)]})
    def test_livecontainer_standalone_only(self):
        p=P['livecontainer']; a={'name':'LiveContainer.ipa','state':'uploaded','size':1000,'browser_download_url':'https://github.com/LiveContainer/LiveContainer/releases/download/3.8.0/LiveContainer.ipa'}
        self.assertEqual(choose_asset(p,{'assets':[a,dict(a,name='LiveContainer+SideStore.ipa')]}),a)
    def test_default_opt_out(self):
        self.assertIsInstance(load('settings.json')['include_community'],bool)
        self.assertEqual(len({p['bundle_id'] for p in P.values()}),5)
