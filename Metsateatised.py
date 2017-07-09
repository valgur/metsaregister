
# coding: utf-8

# In[1]:

import requests
import xmltodict
import pandas as pd
import geopandas as gpd
import shapely.wkt
from urllib.parse import unquote, urljoin
from retrying import retry
import re
import numpy as np
from tqdm import tqdm_notebook


@retry(wait_exponential_multiplier=1000, wait_exponential_max=60000)
def query_metsaregister(aoi, layer_id=10):
    headers = {
        'Pragma': 'no-cache',
        'Origin': 'http://register.metsad.ee',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.8,et;q=0.6',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': '*/*',
        'Cache-Control': 'no-cache',
        'X-Requested-With': 'ShockwaveFlash/26.0.0.131',
        'Connection': 'keep-alive',
        'Referer': 'http://register.metsad.ee/avalik/flash/map.swf',
    }

    params = {'in': 'objects', 
              'layer_id': str(layer_id), 
              'operation': 'fw'}

    data = {'requestArea': aoi,
            'srs': 'EPSG:3301'}

    r = requests.post('http://register.metsad.ee/avalik/flashconf.php', headers=headers, params=params, data=data)
    crs = {'init': 'epsg:3301'}
    if ">0 objects<" in r.text:
        return gpd.GeoDataFrame(crs=crs)
    features = xmltodict.parse(r.text)['objects']['obj']
    if not isinstance(features, list):
        features = [features]
    df = pd.DataFrame(features).set_index('@id')
    if '@label' in list(df):
        df = df.drop('@label', axis=1)
    if 'url' in list(df):
        df['url'] = df['url'].map(unquote)
    geometry = df['wkt'].map(shapely.wkt.loads)
    df = df.drop('wkt', axis=1)
    gdf = gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    return gdf


@retry(wait_exponential_multiplier=1000, wait_exponential_max=60000)
def get_info(path):
    url = urljoin('http://register.metsad.ee/avalik/', path)
    txt = requests.get(url).text
    txt = txt.replace('\r\n', '\n').strip()
    txt = re.sub('\s*<script[^>]*>.+</script>\s*', '', txt, flags=re.DOTALL)
    txt = txt.replace("""
	<tr>
		<th colspan="2" id="grpHeader"><a class="button1" href="#"
			onclick="window.print();"><span>Prindi</span></a></th>
	</tr>""", "")
    txt = txt.replace(' onload="resizeWinTo(\'content\');"', '')
    return txt


def gather_info(aoi, home):
    res = []
    names = []
    for name, id in tqdm_notebook(layers.items()):
        df = query_metsaregister(aoi, id)
        res.append(df)
    all_df = pd.concat(res, keys=list(layers), verify_integrity=True)
    all_df['geometry'] = all_df.intersection(shapely.wkt.loads(aoi))
    
    all_df['pindala (ha)'] = np.round(all_df.area / 1e4, 2)
    all_df['kaugus (m)'] = np.round(all_df.distance(home)).astype(int)
    
    all_df['info'] = np.nan
    for idx, url in tqdm_notebook(list(all_df['url'].dropna().iteritems())):
        all_df.loc[idx, 'info'] = get_info(url)
    
    return all_df


# In[63]:

aoi = "POLYGON((674370.90226963919121772 6414554.51803057454526424, 674312.40983566886279732 6415538.7168108569458127, 675029.57793913071509451 6416072.77816449943929911, 675545.83724765118677169 6415813.37693558726459742, 675871.36035844241268933 6415650.61538019124418497, 676110.41639292961917818 6415592.12294622138142586, 676595.90691463730763644 6415704.78854201175272465, 676849.11234750458970666 6415424.4292376758530736, 676540.20862514618784189 6415213.19370006676763296, 676138.39103526331018656 6415096.20883212517946959, 675700.96935513766948134 6414798.66036366764456034, 675080.44092519185505807 6414389.21332587581127882, 675093.1566717071691528 6414213.73602396529167891, 674790.52190464350860566 6414236.62436769250780344, 674498.05973479198291898 6414211.19287466164678335, 674370.90226963919121772 6414554.51803057454526424))"


# In[64]:

from collections import OrderedDict
layers_xml = requests.get("http://register.metsad.ee/avalik/flashconf.php?in=layers").text
layers = OrderedDict()
for g in xmltodict.parse(layers_xml)['groups']['group']:
    ll = g['layer']
    if not isinstance(ll, list):
        ll = [ll]
    layers.update(OrderedDict([(l['@name'], l['@Lid']) for l in ll]))
layers


# In[67]:

katastrid = query_metsaregister(aoi, 13)


# In[231]:

katastrid


# In[68]:

kodu = katastrid.loc['91804:001:0351'].geometry


# In[69]:

df = gather_info(aoi, kodu)


# In[70]:

df


# In[40]:

df.sort_values('pindala (ha)', ascending=False)


# In[41]:

def count_points(geom):
    d = extract_poly_coords(geom)
    return len(d['exterior_coords']) + len(d['interior_coords'])

def extract_poly_coords(geom):
        if geom.type == 'Polygon':
            exterior_coords = geom.exterior.coords[:]
            interior_coords = []
            for int in geom.interiors:
                interior_coords += int.coords[:]
        elif geom.type == 'MultiPolygon':
            exterior_coords = []
            interior_coords = []
            for part in geom:
                epc = extract_poly_coords(part)  # Recursive call
                exterior_coords += epc['exterior_coords']
                interior_coords += epc['interior_coords']
        else:
            raise ValueError('Unhandled geometry type: ' + repr(geom.type))
        return {'exterior_coords': exterior_coords,
                'interior_coords': interior_coords}

df.geometry.map(count_points).sort_values(ascending=False)


# In[42]:

get_ipython().magic('matplotlib inline')
df.plot()


# In[55]:

df2 = df.copy()
df2.loc[("Teatis", "3423101801"), "url"] = "sjdkjksdfg"
df2.drop(("Teatis", "3271001801"), inplace=True)
df2.loc[("Teatis", "3271001822"), :] = df.loc[("Teatis", "3271001801")]


# In[58]:

df.loc[("Teatis", "3423101801")] != df2.loc[("Teatis", "3423101801")]


# In[75]:

pd.DataFrame(all_df).equals(pd.DataFrame(df2))


# In[77]:

df2.index.difference(all_df.index)


# In[121]:

from htmldiff import htmldiff


# In[122]:

from ipywidgets import HTML
HTML(htmldiff(all_df.ix[0]['info'], all_df.ix[3]['info'], True))


# In[72]:

def compare_tables(df_new, df_old):
    added = df_new.index.difference(df_old.index)
    removed = df_old.index.difference(df_new.index)
    print(list(added), list(removed))
compare_tables(df2, df)


# In[84]:

from ipywidgets import HTML

"{1:.0f} : {0:.0f}".format(*list(df.loc['Teatis'].geometry.centroid[0].coords)[0])


# In[152]:

res = get_info('info.php?id=195969103711')


# In[153]:

from ipywidgets import HTML
HTML(res)


# In[154]:

from bs4 import BeautifulSoup

soup = BeautifulSoup(res, "lxml")
for th in soup.find_all('th'):
    if th.get('colspan') == '2':
        th.extract()
t2 = soup.find_all('table')[1].extract()


# In[148]:

df.loc[df.url.str.startswith('info_ky') == True]


# In[161]:

from io import StringIO

s = pd.read_html(StringIO(str(soup.find_all('table')[0])), thousands=' ', decimal=',')[0].set_index(0).iloc[:, 0]
s.name = None
s.index.name = None
s


# In[230]:

for idx, txt in df['info'].dropna().iteritems():
    soup = BeautifulSoup(txt, "lxml")
    success = False
    try:
        parse_takseer(txt)
        success = True
    except:
        pass
    if not success:
        print(idx, len(soup.find_all('table')), success)


# In[222]:

from collections import OrderedDict
import re
from babel.numbers import parse_decimal

def parse_full_takseer(info):
    soup = BeautifulSoup(info, "lxml")
    tables = soup.find_all('table')
    for tbl in tables[::-1]:
        # Make nested tables independent
        tbl.extract()
    txt = tables[0].text
    d = OrderedDict()
    d['Katastritunnus'] = re.search(r'katastritunnus ([^,\s]+)', txt).group(1)
    d['Eraldise nr.'] = int(re.search(r'eraldis ([^,\s]+)', txt).group(1))
    for l in txt.splitlines():
        l = l.strip()
        l = re.sub(r'\s+', ' ', l)
        parts = l.split(': ', 1)
        if len(parts) != 2:
            continue
        key = parts[0]
        value = parts[1].replace(' ha', '')
        try:
            value = float(parse_decimal(value, 'et_ee'))
        except:
            pass
        if 'pindala' in key.lower():
            key += ' (ha)'
        d[key] = value
    s = pd.Series(d)
    s['Täiskirjeldusega'] = True
    
    kooslus = pd.read_html(StringIO(str(tables[2])), header=0, thousands=' ', decimal=',')[0]
    kooslus = kooslus.loc[kooslus['Rinne'].str.endswith('Esimene')]
    s['Pealiik'] = kooslus.loc[kooslus['%'].idxmax(), 'Puuliik'].lower()
    s['Kõrgus'] = (kooslus['H'] * kooslus['%']).sum() / 100
    s['Vanus'] = (kooslus['Vanus'] * kooslus['%']).sum() / 100
    for idx, row in kooslus.iterrows():
        liik = row['Puuliik'].lower()
        s[liik + ' %'] = row['%']
        s[liik + ' H'] = row['H']
        s[liik + ' A'] = row['Vanus']
    
    return s

parse_full_takseer(df.loc[('Eraldised Eramets: täiskirjeldus', '768863248111'), 'info'])


# In[188]:

HTML(df.loc[('Eraldised Eramets: osaline kirjeldus', '21756000286'), 'info'])


# In[ ]:




# In[229]:

from collections import OrderedDict
from io import StringIO

def parse_short_takseer(info):
    soup = BeautifulSoup(info, "lxml")
    tables = soup.find_all('table')
    for th in soup.find_all('th'):
        if th.get('colspan') == '2':
            th.extract()
    for tbl in tables[::-1]:
        # Make nested tables independent
        tbl.extract()
    s = pd.read_html(StringIO(str(tables[0])), thousands=' ', decimal=',')[0].set_index(0).iloc[:, 0]
    s.name = None
    s.index.name = None
    s['Täiskirjeldusega'] = False
    
    if len(tables) == 1:
        return s
    kooslus = pd.read_html(StringIO(str(tables[1])), header=0, thousands=' ', decimal=',')[0]
    if len(kooslus) == 0:
        return s
    s['Pealiik'] = liigikoodid[kooslus.loc[kooslus['%'].idxmax(), 'Liik']]
    s['Kõrgus'] = (kooslus['H'] * kooslus['%']).sum() / 100
    s['Vanus'] = (kooslus['A'] * kooslus['%']).sum() / 100
    for idx, row in kooslus.iterrows():
        liik = liigikoodid[row['Liik']]
        s[liik + ' %'] = row['%']
        s[liik + ' H'] = row['H']
        s[liik + ' A'] = row['A']
    
    return s

parse_takseer(df.loc[('Eraldised Eramets: osaline kirjeldus', '548210648311'), 'info'])


# In[189]:

def parse_takseer(info):
    if 'Üldised takseerandmed' in info:
        return parse_short_takseer(info)
    else:
        return parse_full_takseer(info)


# In[193]:

liigikoodid = {
'MA': 'mänd',
'KU': 'kuusk',
'NU': 'nulg',
'LH': 'lehis',
'SD': 'seedermänd',
'TS': 'ebatsuuga',
'TA': 'tamm',
'SA': 'saar',
'VA': 'vaher',
'JA': 'jalakas',
'KP': 'künnapuu',
'KS': 'kask',
'HB': 'haab',
'LM': 'sanglepp',
'LV': 'hall lepp',
'PN': 'pärn',
'PP': 'pappel',
'RE': 'remmelgas',
'TM': 'toomingas',
'PI': 'pihlakas',
'TO': 'teised okaspuuliigid',
'TL': 'teised lehtpuuliigid',

'PA': 'paju',
'SP': 'sarapuu',
'TM': 'toomingas',
'PI': 'pihlakas',
'PK': 'paakspuu',
'TY': 'türnpuu',
'KL': 'kuslapuu',
'KD': 'kadakas',
'TP': 'teised põõsaliigid'
}

