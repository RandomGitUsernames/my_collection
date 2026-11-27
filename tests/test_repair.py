import unittest
from unittest.mock import patch
from scripts import update as u
P={p['id']:p for p in u.load('projects.json')}
class RepairTests(unittest.TestCase):
    def test_spotify_unpatched(self):
        p={**P['eeveespotify'],**P['eeveespotify']['fallbacks'][0]}
        name='EeveeSpotify-9.2.2-ESR-7.5.0.ipa'
        a={'name':name,'state':'uploaded','size':100,'browser_download_url':'https://github.com/estrogencat/EeveeIPA/releases/download/v/'+name}
        self.assertEqual(u.choose_asset(p,{'assets':[a,{**a,'name':name.replace('.ipa','-patched.ipa')}]}),a)
    def test_facebook_mirror_filters(self):
        p={**P['facebook-plus'],**P['facebook-plus']['fallbacks'][0]}
        a={'name':'Facebook (Plus 1.0.9)','bundleIdentifier':p['bundle_id'],'localizedDescription':'Build by @ipavault','version':'588.1.0','versionDate':'2026-11-22','size':100,'downloadURL':'https://'+p['asset_host']+'/Facebook%20Plus%20new.ipa'}
        self.assertEqual(len(u.facebook_entries(p,{'apps':[a,{**a,'downloadURL':'https://unknown.example/FacebookPlus.ipa'},{**a,'name':'Facebook (iQFace)'},{**a,'localizedDescription':'unknown'}]})),1)
        with self.assertRaises(ValueError): u.facebook_entries(p,{'apps':[{**a,'localizedDescription':'unknown'}]})
    def test_fallback_after_primary_failure(self):
        p=P['eeveespotify']; release={'id':1,'tag_name':'test','published_at':'2026-11-27T00:00:00Z'}; asset={'id':2,'size':1,'browser_download_url':'https://github.com/estrogencat/EeveeIPA/releases/download/a/b.ipa'}
        info={'CFBundleIdentifier':p['bundle_id'],'CFBundleShortVersionString':'9.2.2','CFBundleVersion':'1'}
        def fake_download(asset,target): target.write_bytes(b'x'); return 'sha256:fixture'
        with patch.object(u,'provider_candidates',side_effect=[ValueError('primary failed'),[(release,asset)]]), patch.object(u,'download',side_effect=fake_download),patch.object(u,'inspect_ipa',return_value=(info,{})):
            provider,_,app,_,errors=u.resolve_project(p,None,None,True)
            self.assertEqual(provider['asset_repo'],'estrogencat/EeveeIPA'); self.assertIn('community',app['localizedDescription'].lower()); self.assertTrue(errors)
    def test_no_community_without_opt_in(self):
        p=P['eeveespotify']
        with patch.object(u,'provider_candidates',side_effect=ValueError('primary failed')) as f:
            with self.assertRaises(ValueError): u.resolve_project(p,None,None,False)
            self.assertEqual(f.call_count,1)
    def test_download_retry(self):
        with patch.object(u,'download_once',side_effect=[ValueError('Incomplete download'),'sha256:ok']),patch.object(u.time,'sleep'):
            self.assertEqual(u.download({},None),'sha256:ok')
