import copy
import pathlib
import plistlib
import tempfile
import unittest
import zipfile
from scripts.update import choose_asset, inspect_ipa, app_from_ipa, news_item, validate, load

P = load('projects.json')[0]
R = {'id':37,'tag_name':'test','published_at':'2026-01-01T00:00:00Z','assets':[]}
A = {'id':1,'name':'YouMod_test.ipa','state':'uploaded','size':123,'browser_download_url':'https://github.com/jaydenjcpy/YouMod/releases/download/test/YouMod_test.ipa'}
INFO = {'CFBundleIdentifier':P['bundle_id'],'CFBundleShortVersionString':'21.1.0','CFBundleVersion':'123','CFBundleExecutable':'App','NSCameraUsageDescription':'Camera','MinimumOSVersion':'17.0'}

class Tests(unittest.TestCase):
    def test_asset(self):
        self.assertEqual(choose_asset(P,{**R,'assets':[A]}),A)
    def test_ambiguous(self):
        with self.assertRaises(ValueError): choose_asset(P,{**R,'assets':[A,A]})
    def test_wrong_origin(self):
        with self.assertRaises(ValueError): choose_asset(P,{**R,'assets':[{**A,'browser_download_url':'https://github.com/other/repo/releases/download/test/x.ipa'}]})
    def test_ipa_and_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp)/'test.ipa'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('Payload/App.app/Info.plist',plistlib.dumps(INFO))
                z.writestr('Payload/App.app/App',b'fixture only')
                z.writestr('Payload/App.app/PlugIns/E.appex/Info.plist',plistlib.dumps({'CFBundleExecutable':'E','NSMicrophoneUsageDescription':'Mic'}))
                z.writestr('Payload/App.app/PlugIns/E.appex/E',b'fixture only')
            info, perms = inspect_ipa(path,lambda p:{'test.entitlement':True})
            self.assertEqual(info,INFO)
            self.assertEqual(perms,{'entitlements':['test.entitlement'],'privacy':{'NSCameraUsageDescription':'Camera','NSMicrophoneUsageDescription':'Mic'}})
            app = app_from_ipa(P,R,A,info,perms,'sha256:fake')
            self.assertEqual(app['versions'][0]['version'],'21.1.0')
            self.assertEqual(app['versions'][0]['buildVersion'],'123')
            validate({'name':'test','apps':[app],'news':[news_item(P,R)]})
            with self.assertRaises(ValueError): validate({'name':'test','apps':[app,copy.deepcopy(app)],'news':[]})
    def test_wrong_bundle(self):
        with self.assertRaises(ValueError): app_from_ipa(P,R,A,{**INFO,'CFBundleIdentifier':'wrong'},{},'sha256:fake')
    def test_watch_news(self):
        item=news_item({**load('projects.json')[1],'mode':'watch'},R)
        self.assertIn('build your own IPA', item['caption'])
        validate({'name':'test','apps':[],'news':[item]})
        with self.assertRaises(ValueError): validate({'name':'test','apps':[],'news':[item,item]})
    def test_seed(self):
        validate(load('source.json', {'name':'test','apps':[],'news':[]}))

if __name__=='__main__': unittest.main()
