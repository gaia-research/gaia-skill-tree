"""Add avatars and Hall plates to the fixtures; mirror blobs locally for the harness."""
import json, shutil, sys
S = sys.argv[1]
AV = {
    'addy-osmani': 'f7b9a68d1e272d936670ff5809195013', 'anthropics': '33bfaeefd69562e55593d97a1918dd92', 'ayghri': '0906f8af7cb92513d1b2db668b4c1268',
    'caioribeiroclw-pixel': '231f6f923cc2aefdfb2b76c421e8655e', 'cathrynlavery': 'fb114aed5189164ef816a87f2dd7d8ef', 'dietrichgebert': 'ccb97ddbe18aac374d02b09d12521173',
    'emilkowalski': 'dc6f21bca1b2ebabff225d654a5e697c', 'firecrawl': '39c2f9d2046268bf6df034c08b5043fa', 'garrytan': '5b854334452b123b1fb1513fe0c27eb1',
    'gsd-build': '4e35b9c1c10942fb2759c674885ad397', 'heygen-com': '7410b1d293e1215160a6548fdf591a27', 'latent-spaces': 'b58ab28157324cf3a8c8a9262749c1fc',
    'leonxlnx': 'ffbc9c053853f227d589f6e7b30ffeae', 'mattpocock': '7e56cd5c85f9c2f4c9ceeb48f3580e80', 'mbtiongson1': '663dc7d9c7471208821be71421aa1a8d',
    'mksglu': 'e4807bff8a96bcc4dee2540bda4640bc', 'mvanhorn': 'fa8b8e68172f78a3fea39f912c0fe3fc', 'nextlevelbuilder': 'c5caa67aa87d63462b13198c9bfd1e27',
    'nvidia': '67ff43e38f5d4587d9849dfd3597b1fd', 'obra': '3227f9575fdb2e75064112a25b696f07', 'panniantong': '2ffdfc21ed48c7e32fdaf4208c8ed2aa',
    'pbakaus': 'd4018f5ecfc98b812a9e4d2a88c0d3dc', 'ruvnet': '6f492f2ccf1d84439c0064d962d40c0f', 'safishamsi': '745d7120f4048829967270ed0745c143',
    't3dotgg': 'f8c4032ba8f32a9d3e9c644c71bf149c', 'trailhq': '9a020ac23b735362b8745561d8192c6a', 'vercel-labs': 'd729df87f7f30fbd1a56c5731b256895',
    'wheresryan22': 'fe8772a02c806d059180171bd19aac63',
}
fx = json.load(open(S + '/assets/atlas-fixtures.json'))
fx['avatars'] = {h: '/_blob/' + b for h, b in AV.items()}
fx['plates'] = json.load(open(S + '/assets/hall-plates.json'))
json.dump(fx, open(S + '/assets/atlas-fixtures-v2.json', 'w'), separators=(',', ':'))
for h, b in AV.items():
    shutil.copy(S + '/avatars/' + h + '.webp', S + '/canvas/_blob/' + b)
shutil.copy(S + '/assets/astrolabe-1920.webp', S + '/canvas/_blob/344138fe2966bd3daea583bc3b98afa2')
shutil.copy(S + '/assets/origin-wreath-gold.svg', S + '/canvas/_blob/0d2eb07f0432c1cefb75dd02485bfb39')
missing = sorted(set(p['c'] for p in fx['plates']) - set(AV))
print('ok', len(fx['avatars']), 'plates', len(fx['plates']), 'missing', missing)
